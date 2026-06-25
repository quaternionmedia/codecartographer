"""
C Semantic Graph Parser
=======================
Parses C source files using libclang and returns a typed semantic graph
(nodes + edges + meta) suitable for the C Semantic Renderer.

Requires the optional 'c-parsing' dependency group:
    uv pip install "codecarto[c-parsing]"

libclang native library candidates are probed automatically on Linux.
"""

import json
import os
import hashlib
import pickle
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── libclang lazy setup ───────────────────────────────────────────────────────
_clang = None
_clang_idx = None
_LIBCLANG_CANDIDATES = [
    '/usr/local/lib/python3.12/dist-packages/clang/native/libclang.so',
    '/usr/lib/x86_64-linux-gnu/libclang-18.so.1',
    '/usr/lib/x86_64-linux-gnu/libclang-17.so.1',
    '/usr/lib/x86_64-linux-gnu/libclang-16.so.1',
    '/usr/lib/llvm-18/lib/libclang.so',
    '/usr/lib/llvm-17/lib/libclang.so',
]


def _get_clang():
    """Lazy-initialise the clang module and index. Raises ImportError if unavailable."""
    global _clang, _clang_idx
    if _clang_idx is not None:
        return _clang, _clang_idx

    try:
        import clang.cindex as cindex
    except ImportError as exc:
        raise ImportError(
            "libclang Python bindings are not installed. "
            "Install with: uv pip install 'codecarto[c-parsing]'"
        ) from exc

    for candidate in _LIBCLANG_CANDIDATES:
        if os.path.exists(candidate):
            try:
                cindex.Config.set_library_file(candidate)
                break
            except Exception:
                pass

    try:
        idx = cindex.Index.create()
    except Exception as exc:
        raise ImportError(
            f"Could not initialise libclang index: {exc}. "
            "Make sure LLVM/libclang is installed on your system."
        ) from exc

    _clang = cindex
    _clang_idx = idx
    return _clang, _clang_idx


# ── Cursor kind → semantic kind mapping ──────────────────────────────────────
def _cursor_map(cindex):
    return {
        cindex.CursorKind.STRUCT_DECL:        'struct',
        cindex.CursorKind.UNION_DECL:         'union',
        cindex.CursorKind.ENUM_DECL:          'enum',
        cindex.CursorKind.TYPEDEF_DECL:       'typedef',
        cindex.CursorKind.FUNCTION_DECL:      'function',
        cindex.CursorKind.VAR_DECL:           'variable',
        cindex.CursorKind.FIELD_DECL:         'field',
        cindex.CursorKind.ENUM_CONSTANT_DECL: 'enum_constant',
        cindex.CursorKind.MACRO_DEFINITION:   'macro',
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def _node_id(cursor) -> str:
    stem = Path(cursor.location.file.name).stem if cursor.location.file else '__global'
    return f"{stem}::{cursor.spelling}"


def _get_qualifiers(cursor, cindex) -> list:
    quals = []
    try:
        sc = cursor.storage_class
        if sc == cindex.StorageClass.STATIC:   quals.append('static')
        if sc == cindex.StorageClass.EXTERN:   quals.append('extern')
        if sc == cindex.StorageClass.REGISTER: quals.append('register')
    except Exception:
        pass
    try:
        if cursor.type.is_const_qualified():    quals.append('const')
        if cursor.type.is_volatile_qualified(): quals.append('volatile')
    except Exception:
        pass
    return quals


def _make_in_target(target_stems):
    def in_target(cursor):
        if not cursor.location.file:
            return False
        return Path(cursor.location.file.name).stem in target_stems
    return in_target


def _add_edge(edges, edge_set, src, dst, kind, weight=1.0):
    if src == dst:
        return
    key = (src, dst, kind)
    if key not in edge_set:
        edge_set.add(key)
        edges.append({'src': src, 'dst': dst, 'kind': kind, 'weight': weight})


# ── Pass 1: Declaration walk ──────────────────────────────────────────────────
def _pass1_declarations(tu, in_target, nodes, edges, edge_set, cindex):
    CURSOR_MAP = _cursor_map(cindex)

    def visit(cursor, parent=None):
        if not in_target(cursor):
            for child in cursor.get_children():
                if in_target(child):
                    visit(child, cursor)
            return

        kind = CURSOR_MAP.get(cursor.kind)
        nid = None

        if kind and cursor.spelling:
            nid = _node_id(cursor)

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
                    'qualifiers': _get_qualifiers(cursor, cindex),
                    'type_str':   cursor.type.spelling if cursor.type else '',
                }

                if kind == 'struct':
                    n['field_count'] = sum(
                        1 for c in cursor.get_children()
                        if c.kind == cindex.CursorKind.FIELD_DECL
                    )
                elif kind == 'enum':
                    n['member_count'] = sum(
                        1 for c in cursor.get_children()
                        if c.kind == cindex.CursorKind.ENUM_CONSTANT_DECL
                    )
                elif kind == 'function':
                    n['param_count'] = sum(
                        1 for c in cursor.get_children()
                        if c.kind == cindex.CursorKind.PARM_DECL
                    )
                    n['is_definition'] = cursor.is_definition()

                nodes[nid] = n

            if kind == 'field' and parent is not None:
                pk = CURSOR_MAP.get(parent.kind)
                if pk and parent.spelling and 'unnamed' not in parent.spelling:
                    pid = _node_id(parent)
                    _add_edge(edges, edge_set, pid, nid, 'FIELD_OF')

            if kind == 'enum_constant' and parent is not None:
                if parent.kind == cindex.CursorKind.ENUM_DECL and parent.spelling:
                    pid = _node_id(parent)
                    _add_edge(edges, edge_set, pid, nid, 'FIELD_OF')

        for child in cursor.get_children():
            visit(child, cursor)

    visit(tu.cursor)


# ── Pass 2: Call edge walk ────────────────────────────────────────────────────
def _pass2_calls(tu, in_target, nodes, call_counts, cindex):
    def find_calls(cursor, enclosing_fn=None):
        if (cursor.kind == cindex.CursorKind.FUNCTION_DECL
                and cursor.is_definition()
                and in_target(cursor)
                and cursor.spelling):
            enclosing_fn = _node_id(cursor)

        if (cursor.kind == cindex.CursorKind.CALL_EXPR
                and enclosing_fn
                and cursor.referenced
                and cursor.referenced.spelling
                and cursor.referenced.location.file
                and in_target(cursor.referenced)):
            dst = _node_id(cursor.referenced)
            if enclosing_fn in nodes and dst in nodes:
                key = (enclosing_fn, dst)
                call_counts[key] = call_counts.get(key, 0) + 1

        for child in cursor.get_children():
            find_calls(child, enclosing_fn)

    find_calls(tu.cursor)


# ── Post-processing: derive type edges ────────────────────────────────────────
def _derive_type_edges(nodes, edges, edge_set):
    struct_names = {n['name']: nid for nid, n in nodes.items() if n['kind'] == 'struct'}

    for nid, node in list(nodes.items()):
        ts = node.get('type_str', '')

        if node['kind'] in ('field', 'variable'):
            for sname, sid in struct_names.items():
                if f'struct {sname} *' in ts or f'{sname} *' in ts:
                    _add_edge(edges, edge_set, nid, sid, 'POINTS_TO', 0.6)

        if node['kind'] == 'typedef':
            for other_id, other in nodes.items():
                if other['kind'] in ('struct', 'enum', 'union'):
                    if (f'struct {other["name"]}' in ts
                            or f'enum {other["name"]}' in ts
                            or f'union {other["name"]}' in ts):
                        _add_edge(edges, edge_set, nid, other_id, 'ALIASES', 0.8)


# ── Cache helpers ─────────────────────────────────────────────────────────────
def _cache_path_for(filepath, args, cache_dir) -> Path:
    key = f"{filepath}::{os.path.getmtime(filepath)}::{' '.join(args)}"
    digest = hashlib.md5(key.encode()).hexdigest()
    return Path(cache_dir) / f"{digest}.pkl"


# ── CParser class ─────────────────────────────────────────────────────────────
class CParser:
    """
    Parses C source files into a semantic graph using libclang.

    The returned graph dict has the shape:
        {
            'nodes': [{'id', 'kind', 'name', 'file', 'line', 'qualifiers',
                       'type_str', ...metadata}, ...],
            'edges': [{'src', 'dst', 'kind', 'weight'}, ...],
            'meta':  {'files', 'node_count', 'edge_count',
                      'kind_counts', 'edge_kinds'}
        }
    """

    def parse_files(
        self,
        filepaths: list[str | Path],
        extra_args: Optional[list[str]] = None,
        cache_dir: Optional[str | Path] = None,
    ) -> dict:
        """
        Parse a list of C/H source files and return the semantic graph.

        Parameters
        ----------
        filepaths : list of str or Path
        extra_args : extra compiler args (e.g. ['-I/usr/include'])
        cache_dir : optional path for per-file result caching

        Returns
        -------
        dict with 'nodes', 'edges', 'meta'
        """
        cindex, idx = _get_clang()
        filepaths = [Path(f) for f in filepaths]
        target_stems = {f.stem for f in filepaths}
        in_target = _make_in_target(target_stems)
        extra_args = extra_args or ['-std=c11']

        if cache_dir:
            Path(cache_dir).mkdir(parents=True, exist_ok=True)

        nodes: dict = {}
        edges: list = []
        edge_set: set = set()
        call_counts: dict = {}

        for fpath in filepaths:
            args = extra_args + [f'-I{fpath.parent}']
            logger.info("Parsing %s", fpath.name)

            if cache_dir:
                cp = _cache_path_for(str(fpath), args, cache_dir)
                if cp.exists():
                    cached = pickle.loads(cp.read_bytes())
                    nodes.update(cached['nodes'])
                    logger.info("Loaded %d nodes from cache for %s", len(cached['nodes']), fpath.name)
                    continue

            tu = idx.parse(str(fpath), args=args)

            errors = [d for d in tu.diagnostics if d.severity >= cindex.Diagnostic.Error]
            for e in errors[:3]:
                logger.warning("libclang: %s", e.spelling)

            _pass1_declarations(tu, in_target, nodes, edges, edge_set, cindex)

            if cache_dir:
                cp = _cache_path_for(str(fpath), args, cache_dir)
                cp.write_bytes(pickle.dumps({
                    'nodes': {k: v for k, v in nodes.items() if v['file'] == fpath.stem}
                }))

        for fpath in filepaths:
            args = extra_args + [f'-I{fpath.parent}']
            tu = idx.parse(str(fpath), args=args)
            _pass2_calls(tu, in_target, nodes, call_counts, cindex)

        for (src, dst), count in call_counts.items():
            if src in nodes and dst in nodes:
                _add_edge(edges, edge_set, src, dst, 'CALLS', min(3.0, 0.5 + count * 0.4))

        _derive_type_edges(nodes, edges, edge_set)

        return self._build_result(list(nodes.values()), edges, [f.name for f in filepaths])

    def parse_compile_commands(
        self,
        compile_commands_path: str | Path,
        subsystem_filter: Optional[str] = None,
        max_files: Optional[int] = None,
    ) -> dict:
        """
        Parse using compile_commands.json for accurate include paths.

        Parameters
        ----------
        compile_commands_path : path to compile_commands.json
        subsystem_filter : optional path fragment to filter files (e.g. 'mm/')
        max_files : optional limit on number of files parsed

        Returns
        -------
        dict with 'nodes', 'edges', 'meta'
        """
        import shlex
        cindex, idx = _get_clang()

        with open(compile_commands_path) as f:
            cmds = json.load(f)

        if subsystem_filter:
            cmds = [c for c in cmds if subsystem_filter in c.get('file', '')]
            logger.info("Filtered to %d files matching '%s'", len(cmds), subsystem_filter)

        if max_files:
            cmds = cmds[:max_files]

        filepaths = [Path(c['file']) for c in cmds]
        target_stems = {f.stem for f in filepaths}
        in_target = _make_in_target(target_stems)

        nodes: dict = {}
        edges: list = []
        edge_set: set = set()
        call_counts: dict = {}

        for entry in cmds:
            fpath = Path(entry['file'])
            raw_args = entry.get('command', entry.get('arguments', ['cc'])[1:])
            if isinstance(raw_args, str):
                args = shlex.split(raw_args)[1:]
            else:
                args = list(raw_args)[1:]
            args = [a for a in args if not a.startswith('-o') and a != '-c']

            logger.info("Parsing %s", fpath.name)
            try:
                tu = idx.parse(str(fpath), args=args)
                _pass1_declarations(tu, in_target, nodes, edges, edge_set, cindex)
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", fpath.name, exc)

        for entry in cmds:
            fpath = Path(entry['file'])
            raw_args = entry.get('command', entry.get('arguments', ['cc'])[1:])
            if isinstance(raw_args, str):
                args = shlex.split(raw_args)[1:]
            else:
                args = list(raw_args)[1:]
            args = [a for a in args if not a.startswith('-o') and a != '-c']
            try:
                tu = idx.parse(str(fpath), args=args)
                _pass2_calls(tu, in_target, nodes, call_counts, cindex)
            except Exception:
                pass

        for (src, dst), count in call_counts.items():
            if src in nodes and dst in nodes:
                _add_edge(edges, edge_set, src, dst, 'CALLS', min(3.0, 0.5 + count * 0.4))

        _derive_type_edges(nodes, edges, edge_set)

        return self._build_result(
            list(nodes.values()),
            edges,
            [Path(c['file']).name for c in cmds],
        )

    @staticmethod
    def _build_result(nodes: list, edges: list, file_names: list) -> dict:
        kind_counts: dict = {}
        for n in nodes:
            kind_counts[n['kind']] = kind_counts.get(n['kind'], 0) + 1

        edge_kind_counts: dict = {}
        for e in edges:
            edge_kind_counts[e['kind']] = edge_kind_counts.get(e['kind'], 0) + 1

        logger.info(
            "Parse complete: %d nodes %s | %d edges %s",
            len(nodes), kind_counts, len(edges), edge_kind_counts,
        )

        return {
            'nodes': nodes,
            'edges': edges,
            'meta': {
                'files':       file_names,
                'node_count':  len(nodes),
                'edge_count':  len(edges),
                'kind_counts': kind_counts,
                'edge_kinds':  edge_kind_counts,
            },
        }
