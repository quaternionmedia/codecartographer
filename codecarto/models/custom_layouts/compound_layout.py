import math
import networkx as nx


def compound_layout(G: nx.DiGraph) -> dict:
    """Four-tier hierarchical layout: dirs → files → symbols → sub-symbols.

    Pass 1 — spring layout on directory nodes, scaled so clusters don't overlap.
    Pass 2 — file nodes placed in even orbits around their parent dir.
    Pass 3 — symbol nodes placed in a source-ordered arc around their parent file.
             Symbols are sorted by their ``line`` attribute so the arc is a
             readable minimap of the file: early lines at 12 o'clock, later
             lines clockwise around the file node.
    Pass 4 — sub-symbol nodes (depth ≥ 3) orbit their nearest depth-2 symbol
             ancestor with the same source-order arc convention.

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
    subsym_parent: dict[str, str] = {}   # subsym_id → nearest depth-2 ancestor

    for u, v, edata in G.edges(data=True):
        if edata.get("relation") != "contains":
            continue
        u_depth = G.nodes[u].get("depth", 1)
        v_depth = G.nodes[v].get("depth", 1)

        if u_depth == 0 and v_depth == 1:
            file_parent[v] = u
        elif u_depth == 1 and v_depth == 2:
            sym_parent[v] = u
        elif u_depth == 2 and v_depth >= 3:
            subsym_parent[v] = u
        elif u_depth >= 3 and v_depth >= 3:
            # Deep nesting: trace up to nearest depth-2 ancestor
            ancestor = u
            visited: set[str] = set()
            while ancestor and ancestor not in visited:
                visited.add(ancestor)
                if G.nodes[ancestor].get("depth", 3) == 2:
                    subsym_parent[v] = ancestor
                    break
                found = None
                for pu, _pv, pdata in G.in_edges(ancestor, data=True):
                    if pdata.get("relation") == "contains":
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
    for sub in subsyms:
        p = subsym_parent.get(sub)
        if p in sym_subsyms:
            sym_subsyms[p].append(sub)

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
        dir_pos = {
            n: (float(xy[0]) * scale * x_stretch, float(xy[1]) * scale * y_stretch)
            for n, xy in raw_dir.items()
        }

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
        r_orph = max_file_r * 0.5
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
        r_orph = global_max_sym_r * 0.5
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
