import math
import networkx as nx


def compound_layout(G: nx.DiGraph) -> dict:
    """Three-tier hierarchical layout: dirs → files → symbols.

    Pass 1 — spring layout on directory nodes, scaled so clusters don't overlap.
    Pass 2 — file nodes placed in even orbits around their parent dir.
    Pass 3 — symbol nodes placed in even orbits around their parent file.
    Orphans (no parent detected via edges or node attributes) land on a fallback ring.

    Returns a flat {node_id: (x, y)} dict. graph_serializer.py multiplies by
    spread=100, so 1.0 unit here ≈ 100 px in the browser.
    """
    # ── Categorise nodes by depth ──────────────────────────────────────────
    dirs: list[str] = []
    files: list[str] = []
    syms: list[str] = []
    for node, data in G.nodes(data=True):
        depth = data.get("depth", 1)
        if depth == 0:
            dirs.append(node)
        elif depth == 1:
            files.append(node)
        else:
            syms.append(node)

    # ── Build parent maps from 'contains' edges ────────────────────────────
    file_parent: dict[str, str] = {}  # file_id → dir_id
    sym_parent: dict[str, str] = {}   # sym_id  → nearest file_id ancestor

    for u, v, edata in G.edges(data=True):
        if edata.get("relation") != "contains":
            continue
        u_depth = G.nodes[u].get("depth", 1)
        v_depth = G.nodes[v].get("depth", 1)
        if u_depth == 0 and v_depth == 1:
            file_parent[v] = u
        elif u_depth == 1 and v_depth >= 2:
            sym_parent[v] = u
        elif u_depth >= 2 and v_depth >= 2:
            # depth-3+ symbols: trace up to nearest depth-1 file ancestor
            ancestor = u
            visited: set[str] = set()
            while ancestor and ancestor not in visited:
                visited.add(ancestor)
                if G.nodes[ancestor].get("depth", 2) == 1:
                    sym_parent[v] = ancestor
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

    # ── Group children per parent ──────────────────────────────────────────
    dir_files: dict[str, list[str]] = {d: [] for d in dirs}
    for f in files:
        p = file_parent.get(f)
        if p in dir_files:
            dir_files[p].append(f)

    file_syms: dict[str, list[str]] = {f: [] for f in files}
    for sym in syms:
        p = sym_parent.get(sym)
        if p in file_syms:
            file_syms[p].append(sym)

    # ── Orbit radius helpers ───────────────────────────────────────────────
    def file_orbit_r(n: int) -> float:
        return max(1.8, math.sqrt(max(n, 1)) * 0.9)

    def sym_orbit_r(n: int) -> float:
        return max(0.45, math.sqrt(max(n, 1)) * 0.28)

    max_file_r = max(
        (file_orbit_r(len(fs)) for fs in dir_files.values() if fs),
        default=1.8,
    )
    max_sym_r = max(
        (sym_orbit_r(len(ss)) for ss in file_syms.values() if ss),
        default=0.45,
    )

    pos: dict[str, tuple[float, float]] = {}

    # ── Pass 1: spring layout for dirs ─────────────────────────────────────
    if not dirs:
        # No directory nodes — fall back to plain spring layout
        raw = nx.spring_layout(G, seed=42)
        return {n: (float(xy[0]), float(xy[1])) for n, xy in raw.items()}

    if len(dirs) == 1:
        dir_pos: dict[str, tuple[float, float]] = {dirs[0]: (0.0, 0.0)}
    else:
        dir_subgraph = G.subgraph(dirs)
        raw_dir = nx.spring_layout(dir_subgraph, seed=42)
        # Scale so cluster radii don't overlap.
        # Spring spans ≈ [-1, 1]; each cluster needs radius ≈ max_file_r + max_sym_r.
        # Target inter-dir distance ≥ 2.8 × cluster_radius.
        cluster_r = max_file_r + max_sym_r
        scale = math.sqrt(len(dirs)) * cluster_r * 1.6
        dir_pos = {
            n: (float(xy[0]) * scale, float(xy[1]) * scale)
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
        r = file_orbit_r(n_files)
        idx = dir_files[p].index(f)
        angle = (2 * math.pi * idx) / max(n_files, 1) + math.pi / 6
        pos[f] = (dx + r * math.cos(angle), dy + r * math.sin(angle))

    if orphan_files:
        r_orph = max_file_r * 0.5
        for i, f in enumerate(orphan_files):
            angle = (2 * math.pi * i) / max(len(orphan_files), 1)
            pos[f] = (r_orph * math.cos(angle), r_orph * math.sin(angle))

    # ── Pass 3: symbol orbits around parent file ───────────────────────────
    orphan_syms: list[str] = []
    for sym in syms:
        p = sym_parent.get(sym)
        if p is None or p not in pos:
            orphan_syms.append(sym)
            continue
        fx, fy = pos[p]
        n_syms = len(file_syms[p])
        r = sym_orbit_r(n_syms)
        idx = file_syms[p].index(sym)
        angle = (2 * math.pi * idx) / max(n_syms, 1)
        pos[sym] = (fx + r * math.cos(angle), fy + r * math.sin(angle))

    if orphan_syms:
        r_orph = max_sym_r * 0.5
        for i, sym in enumerate(orphan_syms):
            angle = (2 * math.pi * i) / max(len(orphan_syms), 1)
            pos[sym] = (r_orph * math.cos(angle), r_orph * math.sin(angle))

    return pos
