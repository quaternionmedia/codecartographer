import { GraphNode } from './graph_renderer';

export interface GroupBounds {
  nodeId: string;
  cx: number;
  cy: number;
  radius: number;
  label: string;
  depth: number; // 0 = directory, 1 = file
}

/**
 * Computes bounding circles for compound layout groups.
 *
 * Uses spatial assignment: each file is assigned to its nearest dir, each
 * symbol to its nearest file. Works correctly after compound_layout backend
 * places nodes in hierarchical orbits.
 *
 * For non-compound layouts (spring, circular, etc.) the circles would be
 * nonsensical — callers should only invoke this when layout is 'compound_layout'.
 */
export class CompoundLayoutManager {
  computeGroupBounds(
    nodes: GraphNode[],
    padding = 40,
    baseNodeSize = 4,
  ): GroupBounds[] {
    const dirs  = nodes.filter(n => (n.depth as number) === 0 && n.x != null && n.y != null);
    const files = nodes.filter(n => (n.depth as number) === 1 && n.x != null && n.y != null);
    const syms  = nodes.filter(n => ((n.depth as number) ?? 2) >= 2 && n.x != null && n.y != null);

    if (dirs.length === 0 && files.length === 0) return [];

    // Assign each file to its nearest dir
    const fileToDir = new Map<string, GraphNode>();
    for (const f of files) {
      let best: GraphNode | null = null;
      let bestDist = Infinity;
      for (const d of dirs) {
        const dist = Math.hypot(f.x! - d.x!, f.y! - d.y!);
        if (dist < bestDist) { bestDist = dist; best = d; }
      }
      if (best) fileToDir.set(f.id, best);
    }

    // Assign each symbol to its nearest file
    const symToFile = new Map<string, GraphNode>();
    for (const s of syms) {
      let best: GraphNode | null = null;
      let bestDist = Infinity;
      for (const f of files) {
        const dist = Math.hypot(s.x! - f.x!, s.y! - f.y!);
        if (dist < bestDist) { bestDist = dist; best = f; }
      }
      if (best) symToFile.set(s.id, best);
    }

    const bounds: GroupBounds[] = [];

    // ── File bounding circles (enclose their symbols) ──────────────────────
    const symsByFile = new Map<string, GraphNode[]>();
    for (const [sid, f] of symToFile) {
      const sym = syms.find(s => s.id === sid);
      if (!sym) continue;
      const list = symsByFile.get(f.id) ?? [];
      list.push(sym);
      symsByFile.set(f.id, list);
    }

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
    for (const [fid, d] of fileToDir) {
      const file = files.find(f => f.id === fid);
      if (!file) continue;
      const list = filesByDir.get(d.id) ?? [];
      list.push(file);
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
   * Builds a parent→[descendant-ids] map using the same nearest-assignment
   * logic as computeGroupBounds. A dir's descendants include all files
   * assigned to it AND all symbols under those files. A file's descendants
   * include only its directly-assigned symbols.
   *
   * Used to propagate drag deltas hierarchically: dragging a dir moves its
   * files and their symbols; dragging a file moves its symbols.
   */
  computeChildrenMap(nodes: GraphNode[]): Map<string, string[]> {
    const dirs  = nodes.filter(n => (n.depth as number) === 0 && n.x != null && n.y != null);
    const files = nodes.filter(n => (n.depth as number) === 1 && n.x != null && n.y != null);
    const syms  = nodes.filter(n => ((n.depth as number) ?? 2) >= 2 && n.x != null && n.y != null);

    const fileToDir = new Map<string, string>();
    for (const f of files) {
      let bestId = '';
      let bestDist = Infinity;
      for (const d of dirs) {
        const dist = Math.hypot(f.x! - d.x!, f.y! - d.y!);
        if (dist < bestDist) { bestDist = dist; bestId = d.id; }
      }
      if (bestId) fileToDir.set(f.id, bestId);
    }

    const symToFile = new Map<string, string>();
    for (const s of syms) {
      let bestId = '';
      let bestDist = Infinity;
      for (const f of files) {
        const dist = Math.hypot(s.x! - f.x!, s.y! - f.y!);
        if (dist < bestDist) { bestDist = dist; bestId = f.id; }
      }
      if (bestId) symToFile.set(s.id, bestId);
    }

    const result = new Map<string, string[]>();

    // File → direct symbol children
    for (const [symId, fileId] of symToFile) {
      const list = result.get(fileId) ?? [];
      list.push(symId);
      result.set(fileId, list);
    }

    // Dir → files + those files' symbols (transitively)
    for (const [fileId, dirId] of fileToDir) {
      const dirList = result.get(dirId) ?? [];
      dirList.push(fileId);
      const fileSyms = result.get(fileId) ?? [];
      dirList.push(...fileSyms);
      result.set(dirId, dirList);
    }

    return result;
  }
}
