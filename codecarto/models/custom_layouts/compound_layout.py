import math
import networkx as nx

# Edge kinds that express structural parent-child containment for layout
# purposes. 'contains' is the general unified-schema kind every parser uses
# for dir->file->symbol nesting; 'field_of' is the C parser's more specific
# kind for struct/union/enum -> field/enum_constant membership (see
# c_language_parser.py's _EDGE_KIND_MAP) -- semantically a containment
# relationship even though it isn't literally named "contains". Reference
# edges like CALLS/POINTS_TO/ALIASES are deliberately excluded: they connect
# symbols to each other, not a parent to its child.
_CONTAINS_KINDS = frozenset({"contains", "field_of"})


def compound_layout(G: nx.DiGraph) -> dict:
    """Four-tier hierarchical layout: dirs → files → symbols → sub-symbols.

    Pass 1 — spring layout on directory nodes, scaled so clusters don't overlap.
    Pass 2 — file nodes placed in even orbits around their parent dir.
    Pass 3 — symbol nodes placed in a source-ordered arc around their parent file.
             Symbols are sorted by their ``line`` attribute so the arc is a
             readable minimap of the file: early lines at 12 o'clock, later
             lines clockwise around the file node.
    Pass 4 — sub-symbol nodes (depth ≥ 3) orbit their nearest depth-2 symbol
             ancestor with the same source-order arc convention. Bare
             module-level statements (a top-level call or constant with no
             enclosing function/class) have no depth-2 ancestor at all —
             those orbit their file directly, just outside its real
             symbol-orbit ring, with the same arc convention.

    Orphans (no parent detected via edges or node attributes) land on a
    fallback ring at each level rather than failing.

    Returns a flat {node_id: (x, y)} dict.  graph_serializer.py multiplies by
    spread=100, so 1.0 unit here ≈ 100 px in the browser.
    """
    # ── Categorise nodes by depth ──────────────────────────────────────────
    dirs:    list[str] = []
    files:   list[str] = []
    syms:    list[str] = []  # depth == 2
    subsyms: list[str] = []  # depth >= 3

    for node, data in G.nodes(data=True):
        depth = data.get("depth", 1)
        if depth == 0:
            dirs.append(node)
        elif depth == 1:
            files.append(node)
        elif depth == 2:
            syms.append(node)
        else:
            subsyms.append(node)

    # ── Build parent maps from 'contains' edges ────────────────────────────
    file_parent:   dict[str, str] = {}   # file_id   → dir_id
    sym_parent:    dict[str, str] = {}   # sym_id    → file_id
    # subsym_id → nearest depth-2 ancestor, or (bare module-level statements
    # with no enclosing function/class) the depth-1 file directly.
    subsym_parent: dict[str, str] = {}

    for u, v, edata in G.edges(data=True):
        if edata.get("kind") not in _CONTAINS_KINDS:
            continue
        u_depth = G.nodes[u].get("depth", 1)
        v_depth = G.nodes[v].get("depth", 1)

        if u_depth == 0 and v_depth == 1:
            file_parent[v] = u
        elif u_depth == 1 and v_depth == 2:
            sym_parent[v] = u
        elif u_depth == 1 and v_depth >= 3:
            subsym_parent[v] = u
        elif u_depth == 2 and v_depth >= 3:
            subsym_parent[v] = u
        elif u_depth >= 3 and v_depth >= 3:
            # Deep nesting: trace up to the nearest depth-2 ancestor,
            # falling back to the depth-1 file if the chain never passes
            # through one (a bare module-level statement's own descendants).
            ancestor = u
            visited: set[str] = set()
            while ancestor and ancestor not in visited:
                visited.add(ancestor)
                anc_depth = G.nodes[ancestor].get("depth", 3)
                if anc_depth in (1, 2):
                    subsym_parent[v] = ancestor
                    break
                found = None
                for pu, _pv, pdata in G.in_edges(ancestor, data=True):
                    if pdata.get("kind") in _CONTAINS_KINDS:
                        found = pu
                        break
                ancestor = found  # type: ignore[assignment]

    # Fallback: match symbol to file via the 'file' node attribute (stem name)
    file_label_to_id: dict[str, str] = {}
    for f in files:
        label = G.nodes[f].get("label", f)
        file_label_to_id[label] = f

    for sym in syms:
        if sym in sym_parent:
            continue
        file_attr = G.nodes[sym].get("file", "")
        if not file_attr:
            continue
        stem = file_attr.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if stem in file_label_to_id:
            sym_parent[sym] = file_label_to_id[stem]
        elif file_attr in file_label_to_id:
            sym_parent[sym] = file_label_to_id[file_attr]

    for sub in subsyms:
        if sub in subsym_parent:
            continue
        file_attr = G.nodes[sub].get("file", "")
        if not file_attr:
            continue
        stem = file_attr.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        # Try to find the nearest depth-2 sym in the same file
        candidates = [
            s for s in syms
            if sym_parent.get(s) and file_label_to_id.get(stem) == sym_parent.get(s)
        ]
        if candidates:
            subsym_parent[sub] = candidates[0]
        elif stem in file_label_to_id:
            # No symbol in this file to attach to (e.g. every top-level
            # statement in it is itself a bare module-level statement) —
            # fall back to the file directly.
            subsym_parent[sub] = file_label_to_id[stem]

    # ── Group children per parent ──────────────────────────────────────────
    dir_files: dict[str, list[str]]  = {d: [] for d in dirs}
    for f in files:
        p = file_parent.get(f)
        if p in dir_files:
            dir_files[p].append(f)

    file_syms: dict[str, list[str]] = {f: [] for f in files}
    for sym in syms:
        p = sym_parent.get(sym)
        if p in file_syms:
            file_syms[p].append(sym)

    sym_subsyms: dict[str, list[str]] = {s: [] for s in syms}
    # Bare module-level statements: subsym_parent points at a depth-1 file
    # rather than a depth-2 symbol (no enclosing function/class exists).
    file_direct_subsyms: dict[str, list[str]] = {f: [] for f in files}
    for sub in subsyms:
        p = subsym_parent.get(sub)
        if p in sym_subsyms:
            sym_subsyms[p].append(sub)
        elif p in file_direct_subsyms:
            file_direct_subsyms[p].append(sub)

    # ── Source-line sort helper ────────────────────────────────────────────
    def _line(node_id: str) -> int:
        return int(G.nodes[node_id].get("line", 0) or 0)

    # ── Orbit radius helpers ───────────────────────────────────────────────
    def sym_orbit_r(n: int) -> float:
        return max(0.45, math.sqrt(max(n, 1)) * 0.28)

    def subsym_orbit_r(n: int) -> float:
        return max(0.22, math.sqrt(max(n, 1)) * 0.14)

    def file_orbit_r(n_files: int, max_child_sym_r: float = 0.45) -> float:
        base = max(1.8, math.sqrt(max(n_files, 1)) * 0.9)
        return base + max_child_sym_r

    # ── Arc placement helper (source-order clockwise from 12 o'clock) ─────
    def _arc_angles(n: int) -> list[float]:
        """Return n angles arranged clockwise from 12 o'clock.

        n == 1  → single angle at 12 o'clock.
        n > 1   → evenly spaced over 300°, leaving a 60° gap at 6 o'clock so
                  the arc has a clear top-to-bottom reading direction that
                  matches the source file: earliest symbol at top, latest at
                  bottom.
        """
        if n == 1:
            return [-math.pi / 2]
        arc = 5 * math.pi / 3   # 300°
        start = -math.pi / 2    # 12 o'clock
        return [start + (i / (n - 1)) * arc for i in range(n)]

    # ── Pre-compute per-dir max symbol orbit radius ────────────────────────
    def _max_sym_r_for_dir(d: str) -> float:
        return max(
            (sym_orbit_r(len(file_syms.get(f, []))) for f in dir_files.get(d, [])),
            default=0.45,
        )

    per_dir_max_sym_r = {d: _max_sym_r_for_dir(d) for d in dirs}
    global_max_sym_r  = max(per_dir_max_sym_r.values(), default=0.45)

    max_file_r = max(
        (file_orbit_r(len(dir_files[d]), per_dir_max_sym_r[d]) for d in dirs if dir_files[d]),
        default=1.8,
    )

    # ── Cumulative descendant weight per directory ─────────────────────────
    # dir_files/file_syms/sym_subsyms only capture *direct* children at each
    # level, so a directory whose room-need comes from a deep/wide nested
    # subtree (subdirectories full of files/symbols) was previously invisible
    # to Pass 1's spacing — it was scaled identically to an empty directory.
    # Nested dir→dir 'contains' edges aren't tracked anywhere else in this
    # file, so build that map here, then weight = direct files+symbols+
    # sub-symbols beneath this dir, plus the same recursively through every
    # nested subdirectory.
    dir_children: dict[str, list[str]] = {d: [] for d in dirs}
    for u, v, edata in G.edges(data=True):
        if edata.get("kind") not in _CONTAINS_KINDS:
            continue
        if G.nodes[u].get("depth", 1) == 0 and G.nodes[v].get("depth", 1) == 0:
            dir_children.setdefault(u, []).append(v)

    def _dir_weight(d: str, _seen: set[str]) -> int:
        if d in _seen:
            return 0
        _seen.add(d)
        weight = 0
        for f in dir_files.get(d, []):
            weight += 1 + len(file_syms.get(f, []))
            for sym in file_syms.get(f, []):
                weight += len(sym_subsyms.get(sym, []))
        for child in dir_children.get(d, []):
            weight += _dir_weight(child, _seen)
        return weight

    dir_weight = {d: max(1, _dir_weight(d, set())) for d in dirs}
    avg_dir_weight = sum(dir_weight.values()) / len(dirs) if dirs else 1

    pos: dict[str, tuple[float, float]] = {}

    # ── Pass 1: spring layout for dirs ─────────────────────────────────────
    if not dirs:
        raw = nx.spring_layout(G, seed=42)
        return {n: (float(xy[0]), float(xy[1])) for n, xy in raw.items()}

    if len(dirs) == 1:
        dir_pos: dict[str, tuple[float, float]] = {dirs[0]: (0.0, 0.0)}
    else:
        dir_subgraph = G.subgraph(dirs)
        raw_dir = nx.spring_layout(dir_subgraph, seed=42)
        cluster_r = max_file_r + global_max_sym_r
        scale = math.sqrt(len(dirs)) * cluster_r * 1.6
        x_stretch, y_stretch = 1.6, 0.7
        dir_pos = {}
        for n, xy in raw_dir.items():
            # Directories with an above-average cumulative subtree are
            # pushed proportionally further from the pack's centroid (spring
            # layout is already ~zero-centered), giving them more orbital
            # room than a same-position, near-empty directory would need.
            weight_factor = math.sqrt(dir_weight[n] / avg_dir_weight)
            node_scale = scale * weight_factor
            dir_pos[n] = (
                float(xy[0]) * node_scale * x_stretch,
                float(xy[1]) * node_scale * y_stretch,
            )

    for d, xy in dir_pos.items():
        pos[d] = xy

    # ── Pass 2: file orbits around parent dir ──────────────────────────────
    orphan_files: list[str] = []
    for f in files:
        p = file_parent.get(f)
        if p is None or p not in pos:
            orphan_files.append(f)
            continue
        dx, dy = pos[p]
        n_files = len(dir_files[p])
        r = file_orbit_r(n_files, per_dir_max_sym_r.get(p, 0.45))
        idx = dir_files[p].index(f)
        angle = (2 * math.pi * idx) / max(n_files, 1) + math.pi / 6
        pos[f] = (dx + r * math.cos(angle), dy + r * math.sin(angle))

    if orphan_files:
        r_orph = file_orbit_r(len(orphan_files)) * 0.5
        for i, f in enumerate(orphan_files):
            angle = (2 * math.pi * i) / max(len(orphan_files), 1)
            pos[f] = (r_orph * math.cos(angle), r_orph * math.sin(angle))

    # ── Pass 3: symbols in source-order arc around parent file ─────────────
    # Symbols are sorted by their ``line`` attribute so the arc reads like a
    # minimap of the file: top (12 o'clock) = line 1, clockwise = later lines.
    orphan_syms: list[str] = []
    for f in files:
        local_syms = sorted(file_syms.get(f, []), key=_line)
        if not local_syms or f not in pos:
            orphan_syms.extend(s for s in local_syms if s not in sym_parent or sym_parent[s] not in pos)
            continue
        fx, fy = pos[f]
        r = sym_orbit_r(len(local_syms))
        angles = _arc_angles(len(local_syms))
        for sym_id, angle in zip(local_syms, angles):
            pos[sym_id] = (fx + r * math.cos(angle), fy + r * math.sin(angle))

    # Handle orphan syms (no file parent found above)
    for sym in syms:
        if sym in pos:
            continue
        orphan_syms.append(sym)

    if orphan_syms:
        r_orph = sym_orbit_r(len(orphan_syms)) * 0.5
        for i, sym in enumerate(set(orphan_syms)):
            angle = (2 * math.pi * i) / max(len(orphan_syms), 1)
            pos[sym] = (r_orph * math.cos(angle), r_orph * math.sin(angle))

    # ── Pass 4: sub-symbols in source-order arc around parent symbol ────────
    orphan_subsyms: list[str] = []
    for sym in syms:
        local_subs = sorted(sym_subsyms.get(sym, []), key=_line)
        if not local_subs or sym not in pos:
            orphan_subsyms.extend(s for s in local_subs)
            continue
        sx, sy = pos[sym]
        r = subsym_orbit_r(len(local_subs))
        angles = _arc_angles(len(local_subs))
        for sub_id, angle in zip(local_subs, angles):
            pos[sub_id] = (sx + r * math.cos(angle), sy + r * math.sin(angle))

    # ── Pass 4b: bare module-level statements orbit their file directly ────
    # No depth-2 symbol ancestor exists for these (e.g. a top-level call or
    # constant not nested inside any function/class), so they orbit the
    # file itself, pushed just outside its real symbol-orbit ring so they
    # don't collide with actual depth-2 symbols orbiting the same file.
    for f in files:
        local_direct_subs = sorted(file_direct_subsyms.get(f, []), key=_line)
        if not local_direct_subs or f not in pos:
            continue
        fx, fy = pos[f]
        sym_ring_r = sym_orbit_r(len(file_syms.get(f, []))) if file_syms.get(f) else 0.0
        r = sym_ring_r + subsym_orbit_r(len(local_direct_subs))
        angles = _arc_angles(len(local_direct_subs))
        for sub_id, angle in zip(local_direct_subs, angles):
            pos[sub_id] = (fx + r * math.cos(angle), fy + r * math.sin(angle))

    for sub in subsyms:
        if sub in pos:
            continue
        orphan_subsyms.append(sub)

    if orphan_subsyms:
        r_orph = subsym_orbit_r(len(orphan_subsyms)) * 0.5
        for i, sub in enumerate(set(orphan_subsyms)):
            angle = (2 * math.pi * i) / max(len(orphan_subsyms), 1)
            pos[sub] = (r_orph * math.cos(angle), r_orph * math.sin(angle))

    return pos
