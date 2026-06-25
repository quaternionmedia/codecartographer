#!/usr/bin/env python3
"""
C Semantic Graph Parser
=======================
Parses C source files using libclang and emits a typed semantic graph (JSON)
suitable for consumption by the C Semantic Visualizer.

Usage:
    python3 parser.py file1.c file2.h [file3.c ...] > graph.json

    # With compile_commands.json (recommended for real kernel source):
    python3 parser.py --compile-commands compile_commands.json --subsystem net/core

    # Output to file:
    python3 parser.py sample/mm_types.h sample/mm_core.c -o graph.json

Requirements:
    pip install libclang networkx --break-system-packages

libclang path (Ubuntu 24):
    /usr/local/lib/python3.12/dist-packages/clang/native/libclang.so

    If this fails, find yours with:
    find / -name "libclang*.so" 2>/dev/null
"""

import json
import sys
import os
import hashlib
import pickle
import argparse
from pathlib import Path

# ── libclang setup ────────────────────────────────────────────────────────────
try:
    import clang.cindex
    # Try bundled native lib first (most reliable)
    LIBCLANG_CANDIDATES = [
        '/usr/local/lib/python3.12/dist-packages/clang/native/libclang.so',
        '/usr/lib/x86_64-linux-gnu/libclang-18.so.1',
        '/usr/lib/x86_64-linux-gnu/libclang-17.so.1',
        '/usr/lib/x86_64-linux-gnu/libclang-16.so.1',
        '/usr/lib/llvm-18/lib/libclang.so',
        '/usr/lib/llvm-17/lib/libclang.so',
    ]
    for candidate in LIBCLANG_CANDIDATES:
        if os.path.exists(candidate):
            clang.cindex.Config.set_library_file(candidate)
            break
    idx = clang.cindex.Index.create()
except Exception as e:
    print(f"ERROR: Could not initialise libclang: {e}", file=sys.stderr)
    print("Install with: pip install libclang --break-system-packages", file=sys.stderr)
    sys.exit(1)

# ── Cursor kind → semantic kind mapping ──────────────────────────────────────
CURSOR_MAP = {
    clang.cindex.CursorKind.STRUCT_DECL:        'struct',
    clang.cindex.CursorKind.UNION_DECL:         'union',
    clang.cindex.CursorKind.ENUM_DECL:          'enum',
    clang.cindex.CursorKind.TYPEDEF_DECL:       'typedef',
    clang.cindex.CursorKind.FUNCTION_DECL:      'function',
    clang.cindex.CursorKind.VAR_DECL:           'variable',
    clang.cindex.CursorKind.FIELD_DECL:         'field',
    clang.cindex.CursorKind.ENUM_CONSTANT_DECL: 'enum_constant',
    clang.cindex.CursorKind.MACRO_DEFINITION:   'macro',
}

# ── Node ID ───────────────────────────────────────────────────────────────────
def node_id(cursor):
    """Stable cross-file node identifier: file_stem::symbol_name"""
    stem = Path(cursor.location.file.name).stem if cursor.location.file else '__global'
    return f"{stem}::{cursor.spelling}"


# ── Qualifier extraction ──────────────────────────────────────────────────────
def get_qualifiers(cursor):
    quals = []
    try:
        sc = cursor.storage_class
        if sc == clang.cindex.StorageClass.STATIC:  quals.append('static')
        if sc == clang.cindex.StorageClass.EXTERN:  quals.append('extern')
        if sc == clang.cindex.StorageClass.REGISTER: quals.append('register')
    except Exception:
        pass
    try:
        if cursor.type.is_const_qualified():    quals.append('const')
        if cursor.type.is_volatile_qualified(): quals.append('volatile')
    except Exception:
        pass
    return quals


# ── File membership test ──────────────────────────────────────────────────────
def make_in_target(target_stems):
    """Returns a predicate: is this cursor in one of the target files?"""
    def in_target(cursor):
        if not cursor.location.file:
            return False
        return Path(cursor.location.file.name).stem in target_stems
    return in_target


# ── Pass 1: Declaration walk ──────────────────────────────────────────────────
def pass1_declarations(tu, in_target, nodes, edges, edge_set):
    """Walk AST, emit nodes and FIELD_OF edges."""

    def visit(cursor, parent=None):
        if not in_target(cursor):
            # Still recurse — a system header might forward-declare something
            # that's defined in our target files
            for child in cursor.get_children():
                if in_target(child):
                    visit(child, cursor)
            return

        kind = CURSOR_MAP.get(cursor.kind)
        nid = None

        if kind and cursor.spelling:
            nid = node_id(cursor)

            # Skip unnamed anonymous structs (they clutter the graph)
            if 'unnamed' in cursor.spelling or 'anonymous' in cursor.spelling:
                for child in cursor.get_children():
                    visit(child, cursor)
                return

            if nid not in nodes:
                n = {
                    'id':         nid,
                    'kind':       kind,
                    'name':       cursor.spelling,
                    'file':       Path(cursor.location.file.name).stem,
                    'line':       cursor.location.line,
                    'qualifiers': get_qualifiers(cursor),
                    'type_str':   cursor.type.spelling if cursor.type else '',
                }

                # Kind-specific metadata
                if kind == 'struct':
                    n['field_count'] = sum(
                        1 for c in cursor.get_children()
                        if c.kind == clang.cindex.CursorKind.FIELD_DECL
                    )
                elif kind == 'enum':
                    n['member_count'] = sum(
                        1 for c in cursor.get_children()
                        if c.kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL
                    )
                elif kind == 'function':
                    n['param_count'] = sum(
                        1 for c in cursor.get_children()
                        if c.kind == clang.cindex.CursorKind.PARM_DECL
                    )
                    n['is_definition'] = cursor.is_definition()

                nodes[nid] = n

            # FIELD_OF edge: field → parent struct/union
            if kind == 'field' and parent is not None:
                pk = CURSOR_MAP.get(parent.kind)
                if pk and parent.spelling and 'unnamed' not in parent.spelling:
                    pid = node_id(parent)
                    add_edge(edges, edge_set, pid, nid, 'FIELD_OF')

            # Enum member → enum
            if kind == 'enum_constant' and parent is not None:
                if parent.kind == clang.cindex.CursorKind.ENUM_DECL and parent.spelling:
                    pid = node_id(parent)
                    add_edge(edges, edge_set, pid, nid, 'FIELD_OF')

        for child in cursor.get_children():
            visit(child, cursor)

    visit(tu.cursor)


# ── Pass 2: Call edge walk ────────────────────────────────────────────────────
def pass2_calls(tu, in_target, nodes, call_counts):
    """Walk function bodies, collect CALLS edges with frequency counts."""

    def find_calls(cursor, enclosing_fn=None):
        # Track enclosing function definition
        if (cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL
                and cursor.is_definition()
                and in_target(cursor)
                and cursor.spelling):
            enclosing_fn = node_id(cursor)

        # Collect call expressions
        if (cursor.kind == clang.cindex.CursorKind.CALL_EXPR
                and enclosing_fn
                and cursor.referenced
                and cursor.referenced.spelling
                and cursor.referenced.location.file
                and in_target(cursor.referenced)):
            dst = node_id(cursor.referenced)
            if enclosing_fn in nodes and dst in nodes:
                key = (enclosing_fn, dst)
                call_counts[key] = call_counts.get(key, 0) + 1

        for child in cursor.get_children():
            find_calls(child, enclosing_fn)

    find_calls(tu.cursor)


# ── Edge helpers ──────────────────────────────────────────────────────────────
def add_edge(edges, edge_set, src, dst, kind, weight=1.0):
    if src == dst:
        return
    key = (src, dst, kind)
    if key not in edge_set:
        edge_set.add(key)
        edges.append({'src': src, 'dst': dst, 'kind': kind, 'weight': weight})


# ── Post-processing edges ─────────────────────────────────────────────────────
def derive_type_edges(nodes, edges, edge_set):
    """
    Derive POINTS_TO and ALIASES edges from type_str inspection.
    This catches pointer relationships not visible in the declaration tree.
    """
    struct_names = {n['name']: nid for nid, n in nodes.items() if n['kind'] == 'struct'}

    for nid, node in list(nodes.items()):
        ts = node.get('type_str', '')

        # POINTS_TO: field/variable whose type is 'struct X *'
        if node['kind'] in ('field', 'variable'):
            for sname, sid in struct_names.items():
                if (f'struct {sname} *' in ts or f'{sname} *' in ts):
                    add_edge(edges, edge_set, nid, sid, 'POINTS_TO', 0.6)

        # ALIASES: typedef → underlying struct/enum
        if node['kind'] == 'typedef':
            for other_id, other in nodes.items():
                if other['kind'] in ('struct', 'enum', 'union'):
                    if (f'struct {other["name"]}' in ts
                            or f'enum {other["name"]}' in ts
                            or f'union {other["name"]}' in ts):
                        add_edge(edges, edge_set, nid, other_id, 'ALIASES', 0.8)


# ── Per-file cache ────────────────────────────────────────────────────────────
def cache_path_for(filepath, args, cache_dir):
    key = f"{filepath}::{os.path.getmtime(filepath)}::{' '.join(args)}"
    digest = hashlib.md5(key.encode()).hexdigest()
    return Path(cache_dir) / f"{digest}.pkl"


# ── Main parse function ───────────────────────────────────────────────────────
def parse_files(filepaths, extra_args=None, cache_dir=None):
    """
    Parse a list of C source files and return the semantic graph.

    Args:
        filepaths:   list of Path or str — files to parse
        extra_args:  list of str — extra compiler args (e.g. ['-I/kernel/include'])
        cache_dir:   optional Path — directory to cache per-file parse results

    Returns:
        dict with keys 'nodes', 'edges', 'meta'
    """
    filepaths = [Path(f) for f in filepaths]
    target_stems = {f.stem for f in filepaths}
    in_target = make_in_target(target_stems)
    extra_args = extra_args or ['-std=c11']

    if cache_dir:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)

    nodes = {}      # id → node dict
    edges = []
    edge_set = set()
    call_counts = {}

    for fpath in filepaths:
        args = extra_args + [f'-I{fpath.parent}']
        print(f"  Parsing {fpath.name}...", file=sys.stderr)

        if cache_dir:
            cp = cache_path_for(str(fpath), args, cache_dir)
            if cp.exists():
                cached = pickle.loads(cp.read_bytes())
                nodes.update(cached['nodes'])
                print(f"    (cached, {len(cached['nodes'])} nodes)", file=sys.stderr)
                continue

        tu = idx.parse(str(fpath), args=args)

        # Report parse errors
        errors = [d for d in tu.diagnostics
                  if d.severity >= clang.cindex.Diagnostic.Error]
        if errors:
            for e in errors[:3]:
                print(f"    WARN: {e.spelling}", file=sys.stderr)

        pass1_declarations(tu, in_target, nodes, edges, edge_set)

        if cache_dir:
            cp = cache_path_for(str(fpath), args, cache_dir)
            cp.write_bytes(pickle.dumps({'nodes': {k: v for k, v in nodes.items()
                                                   if v['file'] == fpath.stem}}))

    # Pass 2: call edges (re-parse to walk function bodies)
    for fpath in filepaths:
        args = extra_args + [f'-I{fpath.parent}']
        tu = idx.parse(str(fpath), args=args)
        pass2_calls(tu, in_target, nodes, call_counts)

    # Emit CALLS edges with weights
    for (src, dst), count in call_counts.items():
        if src in nodes and dst in nodes:
            add_edge(edges, edge_set, src, dst, 'CALLS',
                     min(3.0, 0.5 + count * 0.4))

    # Derived type edges
    derive_type_edges(nodes, edges, edge_set)

    # Stats
    kind_counts = {}
    for n in nodes.values():
        kind_counts[n['kind']] = kind_counts.get(n['kind'], 0) + 1
    edge_kind_counts = {}
    for e in edges:
        edge_kind_counts[e['kind']] = edge_kind_counts.get(e['kind'], 0) + 1

    print(f"\nParse complete:", file=sys.stderr)
    print(f"  Nodes: {len(nodes)}  {kind_counts}", file=sys.stderr)
    print(f"  Edges: {len(edges)}  {edge_kind_counts}", file=sys.stderr)

    return {
        'nodes': list(nodes.values()),
        'edges': edges,
        'meta': {
            'files':       [f.name for f in filepaths],
            'node_count':  len(nodes),
            'edge_count':  len(edges),
            'kind_counts': kind_counts,
            'edge_kinds':  edge_kind_counts,
        }
    }


# ── compile_commands.json mode ───────────────────────────────────────────────
def parse_compile_commands(compile_commands_path, subsystem_filter=None, max_files=None):
    """
    Parse using compile_commands.json for accurate include paths.

    Args:
        compile_commands_path: path to compile_commands.json
        subsystem_filter: optional string — only parse files containing this path fragment
                          e.g. 'net/core' or 'mm/'
        max_files: optional int — limit number of files (for testing)

    Returns:
        graph dict
    """
    with open(compile_commands_path) as f:
        cmds = json.load(f)

    if subsystem_filter:
        cmds = [c for c in cmds if subsystem_filter in c.get('file', '')]
        print(f"Filtered to {len(cmds)} files matching '{subsystem_filter}'", file=sys.stderr)

    if max_files:
        cmds = cmds[:max_files]

    filepaths = [Path(c['file']) for c in cmds]
    target_stems = {f.stem for f in filepaths}
    in_target = make_in_target(target_stems)

    nodes = {}
    edges = []
    edge_set = set()
    call_counts = {}

    for entry in cmds:
        fpath = Path(entry['file'])
        # Parse compile command: strip compiler binary, keep flags
        raw_args = entry.get('command', entry.get('arguments', ['cc'])[1:])
        if isinstance(raw_args, str):
            import shlex
            args = shlex.split(raw_args)[1:]  # drop compiler binary
        else:
            args = list(raw_args)[1:]
        # Remove output flags that confuse libclang
        args = [a for a in args if not a.startswith('-o') and a != '-c']

        print(f"  Parsing {fpath.name}...", file=sys.stderr)
        try:
            tu = idx.parse(str(fpath), args=args)
            pass1_declarations(tu, in_target, nodes, edges, edge_set)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)

    for entry in cmds:
        fpath = Path(entry['file'])
        raw_args = entry.get('command', entry.get('arguments', ['cc'])[1:])
        if isinstance(raw_args, str):
            import shlex
            args = shlex.split(raw_args)[1:]
        else:
            args = list(raw_args)[1:]
        args = [a for a in args if not a.startswith('-o') and a != '-c']
        try:
            tu = idx.parse(str(fpath), args=args)
            pass2_calls(tu, in_target, nodes, call_counts)
        except Exception:
            pass

    for (src, dst), count in call_counts.items():
        if src in nodes and dst in nodes:
            add_edge(edges, edge_set, src, dst, 'CALLS', min(3.0, 0.5 + count * 0.4))

    derive_type_edges(nodes, edges, edge_set)

    return {
        'nodes': list(nodes.values()),
        'edges': edges,
        'meta': {
            'files':      [Path(c['file']).name for c in cmds],
            'node_count': len(nodes),
            'edge_count': len(edges),
        }
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Parse C source into a semantic graph JSON for the C Visualizer'
    )
    parser.add_argument('files', nargs='*', help='C source files to parse')
    parser.add_argument('--compile-commands', '-cc', metavar='PATH',
                        help='Path to compile_commands.json (alternative to listing files)')
    parser.add_argument('--subsystem', '-s', metavar='PATH_FRAGMENT',
                        help='Filter compile_commands.json to files containing this path fragment')
    parser.add_argument('--max-files', type=int, metavar='N',
                        help='Limit number of files (useful for testing large codebases)')
    parser.add_argument('--output', '-o', metavar='PATH', default='-',
                        help='Output file (default: stdout)')
    parser.add_argument('--cache-dir', metavar='PATH',
                        help='Cache directory for per-file parse results')
    parser.add_argument('--include', '-I', action='append', default=[], metavar='PATH',
                        help='Extra include directories')
    parser.add_argument('--define', '-D', action='append', default=[], metavar='MACRO',
                        help='Extra macro definitions')
    args = parser.parse_args()

    extra_args = ['-std=c11'] + [f'-I{p}' for p in args.include] + [f'-D{d}' for d in args.define]

    if args.compile_commands:
        graph = parse_compile_commands(
            args.compile_commands,
            subsystem_filter=args.subsystem,
            max_files=args.max_files,
        )
    elif args.files:
        graph = parse_files(args.files, extra_args=extra_args, cache_dir=args.cache_dir)
    else:
        parser.print_help()
        sys.exit(1)

    output_json = json.dumps(graph, indent=2)

    if args.output == '-':
        print(output_json)
    else:
        Path(args.output).write_text(output_json)
        print(f"Wrote {len(graph['nodes'])} nodes, {len(graph['edges'])} edges → {args.output}",
              file=sys.stderr)


if __name__ == '__main__':
    main()
