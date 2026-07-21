import { GraphNode, GraphEdge } from './graph_renderer';

export interface GroupBounds {
  nodeId: string;
  cx: number;
  cy: number;
  radius: number;
  label: string;
  depth: number; // 0 = directory, 1 = file
}

interface ParentChain {
  dirs: GraphNode[];
  files: GraphNode[];
  syms2: GraphNode[];
  syms3: GraphNode[];
  fileToDir: Map<string, GraphNode>;
  sym2ToFile: Map<string, GraphNode>;
  sym3ToSym2: Map<string, GraphNode>;
}

/**
 * Computes bounding circles and drag-propagation groups for compound layout.
 *
 * Groups are derived from the real backend `relation === "contains"` edges
 * (dir→file, file→symbol, symbol→sub-symbol) — the backend already computed
 * this structure (compound_layout.py) and sends it down the wire in the same
 * graph payload, so re-deriving it from node positions was pure duplication.
 * Nearest-neighbor spatial assignment is used only as a fallback for orphan
 * nodes with no matching contains edge, mirroring compound_layout.py's own
 * orphan fallback-ring behavior.
 *
 * For non-compound layouts (spring, circular, etc.) the circles would be
 * nonsensical — callers should only invoke this when layout is 'compound_layout'.
 */
export class CompoundLayoutManager {
  private _buildParentChain(nodes: GraphNode[], edges: GraphEdge[]): ParentChain {
    const dirs  = nodes.filter(n => (n.depth as number) === 0 && n.x != null && n.y != null);
    const files = nodes.filter(n => (n.depth as number) === 1 && n.x != null && n.y != null);
    const syms2 = nodes.filter(n => (n.depth as number) === 2 && n.x != null && n.y != null);
    const syms3 = nodes.filter(n => ((n.depth as number) ?? 0) >= 3 && n.x != null && n.y != null);

    return {
      dirs,
      files,
      syms2,
      syms3,
      fileToDir: this._assignParents(edges, files, dirs),
      sym2ToFile: this._assignParents(edges, syms2, files),
      sym3ToSym2: this._assignParents(edges, syms3, syms2),
    };
  }

  /**
   * Maps each child to its parent using real `relation === "contains"`
   * edges between the two sets. A child with no such edge (an orphan, same
   * concept compound_layout.py itself falls back on) is instead assigned to
   * its nearest parent by position.
   */
  private _assignParents(
    edges: GraphEdge[],
    children: GraphNode[],
    parents: GraphNode[],
  ): Map<string, GraphNode> {
    const parentById = new Map(parents.map(p => [p.id, p]));
    const childIds = new Set(children.map(c => c.id));
    const result = new Map<string, GraphNode>();

    for (const e of edges) {
      if (e.relation !== 'contains') continue;
      const sourceId = typeof e.source === 'string' ? e.source : (e.source as GraphNode).id;
      const targetId = typeof e.target === 'string' ? e.target : (e.target as GraphNode).id;
      if (!childIds.has(targetId)) continue;
      const parent = parentById.get(sourceId);
      if (parent) result.set(targetId, parent);
    }

    for (const c of children) {
      if (result.has(c.id) || c.x == null || c.y == null) continue;
      let best: GraphNode | null = null;
      let bestDist = Infinity;
      for (const p of parents) {
        if (p.x == null || p.y == null) continue;
        const dist = Math.hypot(c.x - p.x, c.y - p.y);
        if (dist < bestDist) { bestDist = dist; best = p; }
      }
      if (best) result.set(c.id, best);
    }

    return result;
  }

  computeGroupBounds(
    nodes: GraphNode[],
    edges: GraphEdge[],
    padding = 40,
    baseNodeSize = 4,
  ): GroupBounds[] {
    const { dirs, files, syms2, syms3, fileToDir, sym2ToFile, sym3ToSym2 } =
      this._buildParentChain(nodes, edges);

    if (dirs.length === 0 && files.length === 0) return [];

    // Sub-symbols enclose within their symbol's file transitively, so a
    // file's circle still covers both levels like it did before.
    const symsByFile = new Map<string, GraphNode[]>();
    for (const s of syms2) {
      const f = sym2ToFile.get(s.id);
      if (!f) continue;
      const list = symsByFile.get(f.id) ?? [];
      list.push(s);
      symsByFile.set(f.id, list);
    }
    for (const s of syms3) {
      const sym = sym3ToSym2.get(s.id);
      const f = sym && sym2ToFile.get(sym.id);
      if (!f) continue;
      const list = symsByFile.get(f.id) ?? [];
      list.push(s);
      symsByFile.set(f.id, list);
    }

    const bounds: GroupBounds[] = [];

    // ── File bounding circles (enclose their symbols) ──────────────────────
    for (const f of files) {
      const children = symsByFile.get(f.id) ?? [];
      if (children.length === 0) continue;
      let maxR = 0;
      for (const s of children) {
        const r = Math.hypot(s.x! - f.x!, s.y! - f.y!) + baseNodeSize * 1.0;
        if (r > maxR) maxR = r;
      }
      bounds.push({
        nodeId: f.id,
        cx: f.x!,
        cy: f.y!,
        radius: maxR + padding * 0.5,
        label: (f.label as string) || f.id,
        depth: 1,
      });
    }

    // ── Dir bounding circles (enclose files + their symbol orbits) ─────────
    const filesByDir = new Map<string, GraphNode[]>();
    for (const f of files) {
      const d = fileToDir.get(f.id);
      if (!d) continue;
      const list = filesByDir.get(d.id) ?? [];
      list.push(f);
      filesByDir.set(d.id, list);
    }

    for (const d of dirs) {
      const dirFiles = filesByDir.get(d.id) ?? [];
      if (dirFiles.length === 0) continue;
      let maxR = 0;
      for (const f of dirFiles) {
        const fileBound = bounds.find(b => b.nodeId === f.id);
        const distToFile = Math.hypot(f.x! - d.x!, f.y! - d.y!);
        const r = distToFile + (fileBound?.radius ?? baseNodeSize * 1.8);
        if (r > maxR) maxR = r;
      }
      bounds.push({
        nodeId: d.id,
        cx: d.x!,
        cy: d.y!,
        radius: maxR + padding,
        label: (d.label as string) || d.id,
        depth: 0,
      });
    }

    // Depth=0 first so SVG renders large circles behind small circles
    bounds.sort((a, b) => a.depth - b.depth);
    return bounds;
  }

  /**
   * Builds a parent→[ALL descendant-ids] map covering all four depth levels
   * (dir→file→symbol→sub-symbol), from the same real 'contains' edges
   * computeGroupBounds uses.
   *
   * Dragging a dir moves its files, their symbols, AND those symbols'
   * sub-symbols. Dragging a file moves its symbols and sub-symbols.
   * Dragging a depth-2 symbol moves only its depth-3 children.
   */
  computeChildrenMap(nodes: GraphNode[], edges: GraphEdge[]): Map<string, string[]> {
    const { files, syms2, syms3, fileToDir, sym2ToFile, sym3ToSym2 } =
      this._buildParentChain(nodes, edges);

    const result = new Map<string, string[]>();

    // depth-2 sym → direct depth-3 children
    for (const s of syms3) {
      const sym = sym3ToSym2.get(s.id);
      if (!sym) continue;
      const list = result.get(sym.id) ?? [];
      list.push(s.id);
      result.set(sym.id, list);
    }

    // depth-1 file → depth-2 syms + their depth-3 children
    for (const s of syms2) {
      const f = sym2ToFile.get(s.id);
      if (!f) continue;
      const list = result.get(f.id) ?? [];
      list.push(s.id);
      list.push(...(result.get(s.id) ?? []));
      result.set(f.id, list);
    }

    // depth-0 dir → files + all their descendants
    for (const f of files) {
      const d = fileToDir.get(f.id);
      if (!d) continue;
      const list = result.get(d.id) ?? [];
      list.push(f.id);
      list.push(...(result.get(f.id) ?? []));
      result.set(d.id, list);
    }

    return result;
  }
}
