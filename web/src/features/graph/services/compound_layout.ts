import type { GraphNode, GraphEdge } from './graph_types';
import { packEnclose } from 'd3';

/** A circle in graph coordinates. */
interface Circle {
  x: number;
  y: number;
  r: number;
}

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
  /** A member's file, through whatever holds it -- a symbol, or the file
   *  itself -- and none for a member nothing holds. */
  sym3ToFile: Map<string, GraphNode>;
}

/**
 * Computes bounding circles and drag-propagation groups for compound layout.
 *
 * Groups are derived from the real backend containment edges (`kind` of
 * `contains` or `field_of` — dir→file, file→symbol, symbol→sub-symbol) —
 * the backend already computed
 * this structure (compound_layout.py) and sends it down the wire in the same
 * graph payload, so re-deriving it from node positions was pure duplication.
 * Nearest-neighbor spatial assignment is used only as a fallback for orphan
 * nodes with no matching contains edge, mirroring compound_layout.py's own
 * orphan fallback-ring behavior.
 *
 * The renderer draws the outlines on every D3 layout while Group Outlines is
 * on. A layout that does not gather a group together (Spring, Circular) gives
 * it a wide outline that overlaps others; centring each on its group keeps it
 * as small as the group allows.
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
      sym3ToFile: this._assignParents(edges, syms3, files, false),
    };
  }

  /**
   * Maps each child to its parent using real containment edges between the
   * two sets (the unified schema's edge-kind field — `make_edge()` on the
   * backend — arriving either flat as `edge.kind` or, for gJGF-shaped
   * payloads, nested at `edge.metadata.kind`). Recognizes both `contains`
   * (the general kind every parser uses) and `field_of` (the C parser's
   * more specific kind for struct/union/enum -> field/enum_constant
   * membership — see compound_layout.py's `_CONTAINS_KINDS`, which this
   * mirrors). A child with no such edge (an orphan, same concept
   * compound_layout.py itself falls back on) is instead assigned to its
   * nearest parent by position.
   */
  private static readonly CONTAINS_KINDS = new Set(['contains', 'field_of']);

  private _isContainsEdge(e: GraphEdge): boolean {
    if (CompoundLayoutManager.CONTAINS_KINDS.has(e.kind as string)) return true;
    const meta = e.metadata as Record<string, unknown> | undefined;
    return CompoundLayoutManager.CONTAINS_KINDS.has(meta?.kind as string);
  }

  private _assignParents(
    edges: GraphEdge[],
    children: GraphNode[],
    parents: GraphNode[],
    byPosition = true,
  ): Map<string, GraphNode> {
    const parentById = new Map(parents.map(p => [p.id, p]));
    const childIds = new Set(children.map(c => c.id));
    const result = new Map<string, GraphNode>();

    // What holds each node, by its containment edge, the first one seen.
    const holder = new Map<string, string>();
    for (const e of edges) {
      if (!this._isContainsEdge(e)) continue;
      const sourceId = typeof e.source === 'string' ? e.source : (e.source as GraphNode).id;
      const targetId = typeof e.target === 'string' ? e.target : (e.target as GraphNode).id;
      if (!holder.has(targetId)) holder.set(targetId, sourceId);
      if (!childIds.has(targetId)) continue;
      const parent = parentById.get(sourceId);
      if (parent) result.set(targetId, parent);
    }

    // A node nested deeper than one level -- a member of a member, a project's
    // file under a directory under its root -- has no edge from a parent. It
    // is traced up what holds it to the nearest one, as compound_layout.py
    // traces it: grouped by position, a project's code in the whole corpus was
    // drawn in the outline of whichever neighbour's root it was nearest.
    for (const c of children) {
      if (result.has(c.id)) continue;
      const seen = new Set<string>([c.id]);
      for (let up = holder.get(c.id); up && !seen.has(up); up = holder.get(up)) {
        const parent = parentById.get(up);
        if (parent) { result.set(c.id, parent); break; }
        seen.add(up);
      }
    }

    // What nothing holds goes to the parent nearest it, unless `byPosition`
    // is off. A module imported from outside the repository is in none of
    // its directories, wherever it is drawn: placed beside one, it was drawn
    // in that directory's outline, which grew round every import it was given.
    for (const c of byPosition ? children : []) {
      if (result.has(c.id) || c.x == null || c.y == null || c.kind === 'external_module') continue;
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

  /**
   * One outline per directory and per file that holds anything drawn: the
   * smallest circle enclosing the group -- its own node and what it holds --
   * plus padding (`padding` for a directory, half of it for a file).
   *
   * A file's group is its node and its symbols, sub-symbols included. A
   * directory's is its node and its files, each by its own outline when it
   * has one. Centred on the group, not on its node: a layout that does not
   * place a node amid what it holds (Spring, Circular) would otherwise draw
   * a circle reaching from the node to its farthest child, twice the size,
   * and the fit that frames the outlines would draw the graph small.
   *
   * `radiusOf` is a node's drawn extent; it defaults to `baseNodeSize`.
   */
  computeGroupBounds(
    nodes: GraphNode[],
    edges: GraphEdge[],
    padding = 40,
    baseNodeSize = 4,
    radiusOf: (node: GraphNode) => number = () => baseNodeSize,
  ): GroupBounds[] {
    const { dirs, files, syms2, syms3, fileToDir, sym2ToFile, sym3ToSym2, sym3ToFile } =
      this._buildParentChain(nodes, edges);

    if (dirs.length === 0 && files.length === 0) return [];

    const circleOf = (n: GraphNode): Circle => ({ x: n.x!, y: n.y!, r: radiusOf(n) });
    const group = (members: Circle[]): Circle => packEnclose(members.map((c) => ({ ...c })));

    // Sub-symbols enclose within their symbol's file transitively, so a
    // file's circle covers both levels.
    const symsByFile = new Map<string, GraphNode[]>();
    for (const s of syms2) {
      const f = sym2ToFile.get(s.id);
      if (!f) continue;
      const list = symsByFile.get(f.id) ?? [];
      list.push(s);
      symsByFile.set(f.id, list);
    }
    // A member is its file's through whatever holds it. One its file holds
    // itself -- a module's own constant or name -- has no symbol above it,
    // and was given the symbol nearest it, often the next file's: that
    // file's outline reached across to it.
    for (const s of syms3) {
      const sym = sym3ToSym2.get(s.id);
      const f = sym3ToFile.get(s.id) ?? (sym && sym2ToFile.get(sym.id));
      if (!f) continue;
      const list = symsByFile.get(f.id) ?? [];
      list.push(s);
      symsByFile.set(f.id, list);
    }

    const bounds: GroupBounds[] = [];
    const fileCircle = new Map<string, Circle>();

    // ── File outlines (enclose the file and its symbols) ───────────────────
    for (const f of files) {
      const children = symsByFile.get(f.id) ?? [];
      if (children.length === 0) continue;
      const c = group([circleOf(f), ...children.map(circleOf)]);
      const outline = { x: c.x, y: c.y, r: c.r + padding * 0.5 };
      fileCircle.set(f.id, outline);
      bounds.push({
        nodeId: f.id,
        cx: outline.x,
        cy: outline.y,
        radius: outline.r,
        label: (f.label as string) || f.id,
        depth: 1,
      });
    }

    // ── Directory outlines (enclose the directory and its files' outlines) ─
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
      const c = group([circleOf(d), ...dirFiles.map((f) => fileCircle.get(f.id) ?? circleOf(f))]);
      bounds.push({
        nodeId: d.id,
        cx: c.x,
        cy: c.y,
        radius: c.r + padding,
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

/**
 * How far an outline is drawn past what it encloses, and how far each node it
 * encloses reaches: `radiusOf`, the node's drawn extent. A fresh drawing and
 * the redraw after a removal both take it from here, so an outline keeps its
 * size when a node outside its group is deleted.
 */
export interface OutlineSpacing {
  readonly padding: number;
  readonly baseNodeSize: number;
  readonly radiusOf: (node: GraphNode) => number;
}

/**
 * The outlines drawn once nodes leave the canvas (Delete, Collapse), given
 * those drawn before and the nodes and edges that remain.
 *
 * Recomputed around what remains, so an outline with nothing left inside it
 * -- a collapsed file's, or one whose node was deleted -- is dropped, and one
 * that lost some of what it enclosed is drawn around the rest. A fit frames
 * the outlines drawn, so one left at its old radius framed an empty circle.
 * None are drawn after a removal when none were before: Group Outlines is
 * off, or the stream has not finished.
 */
export function outlinesAfterRemoval(
  manager: CompoundLayoutManager,
  drawn: readonly GroupBounds[],
  remaining: GraphNode[],
  edges: GraphEdge[],
  spacing: OutlineSpacing,
): GroupBounds[] {
  if (drawn.length === 0) return [];
  return manager.computeGroupBounds(remaining, edges, spacing.padding, spacing.baseNodeSize, spacing.radiusOf);
}
