/**
 * StreamingGraphRenderer — progressively adds nodes/edges to D3 canvas as
 * they arrive over an SSE stream. Expects backend-computed (x, y) positions.
 *
 * Usage:
 *   const r = new StreamingGraphRenderer(container, styling);
 *   r.addNode(node);   // called for each SSE 'node' event
 *   r.addEdge(edge);   // called for each SSE 'edge' event
 *   r.finalize();      // called on SSE 'done'
 */

import * as d3 from 'd3';
import { GraphNode, GraphEdge } from './graph_types';
import { canvasPath } from './node_shapes';
import { drawnFill } from '../extensions/legend_marks';
import { GraphStylingOptions } from '../../../state/types';
import { CompoundLayoutManager, outlinesAfterRemoval } from './compound_layout';
import type { GroupBounds, OutlineSpacing } from './compound_layout';
import type { ExtensionContext } from '../extensions/base';
import { depthSizeMultiplier } from './depth_scale';
import { fitBadgeText, sourceTarget, type SourceTarget } from './node_info';
import { BADGE_MARGIN, badgePlace } from './source_badge';
import { fitTransform, framedExtents } from './fit';
import { placeOutlineLabels } from './outline_labels';
import type { Box, FramedNode, FramedOutline } from './fit';

/**
 * The event a showgraph's node sends when it is double-clicked: its `show`
 * attribute (`family:core`, `project:carlos`) as the detail. It bubbles from
 * the canvas, so whatever opens showgraphs listens on the document, and the
 * renderer needs no handle on it.
 */
export const SHOW_OPEN_EVENT = 'codecarto:show-open';

/** The smallest a map's name is drawn on screen, in pixels, however far out it is framed. */
const MAP_NAME_PX = 10;
/** The same for a map's outline names, which name whole groups. */
const MAP_OUTLINE_PX = 12;
/** The longest a map's name is drawn, in characters. */
const MAP_NAME_CHARS = 32;

// Nodes rendered per animation frame. Scales with total so large repos
// finish in ~2s while small repos show clearly progressive animation.
function nodesPerFrame(total: number): number {
  if (total <= 60)  return 1;
  if (total <= 200) return 3;
  if (total <= 600) return 6;
  return Math.ceil(total / 100);
}

export class StreamingGraphRenderer {
  private svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private g: d3.Selection<SVGGElement, unknown, null, undefined>;
  private linkGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
  private nodeGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
  private labelGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
  private zoom: d3.ZoomBehavior<SVGSVGElement, unknown>;
  private nodeById = new Map<string, GraphNode>();
  /**
   * How many nodes arrived without coordinates and were placed on a
   * depth ring instead.
   *
   * **THE RING IS A FALLBACK, AND NOTHING SHOULD BE REACHING IT.** Every
   * graph route in this project lays its nodes out server-side on the way
   * through `GraphSerializer.serialize_to_gjgf`, and a backend test
   * asserts that. This counter is the other half of that claim: the test
   * covers the routes it knows about, and this covers whatever actually
   * arrives. A non-zero count in the status line means a source is
   * streaming unpositioned nodes and the picture is a ring rather than a
   * layout -- which looks like a rendered graph, which is why it needs
   * saying out loud rather than leaving to be noticed.
   */
  private _ringPlaced = 0;
  /**
   * Drawn as a map: a showgraph, whose names are what it is for.
   *
   * **A CODE GRAPH HIDES ITS NAMES; A MAP CANNOT.** Labels are off by default
   * because a parsed repository has thousands of them. A showgraph has a few
   * dozen, and with its names hidden the index was nine circles of dots. So a
   * map draws every name its node does not leave to an outline (`label_at`
   * `none`), on the side `label_at` says, and keeps names and outline names
   * at least `MAP_NAME_PX` and `MAP_OUTLINE_PX` on screen however far out the
   * fit frames it. Its outlines take their group's hue.
   */
  private _map = false;
  /** Whether a map's names are on: the Graph Settings toggle still turns them off. */
  private _mapNames = true;
  private _zoomK = 1;
  private styling: GraphStylingOptions;
  private width: number;
  private height: number;
  /** The canvas: the element the svg fills, which the dock sizes. */
  private readonly _container: HTMLElement;
  // Set by `fitWhenResized`: the resize observer fits once the size lands.
  private _fitOnResize = false;

  // Internal queues — filled by addNode/addEdge, drained by rAF loop
  private _nodeQueue: GraphNode[] = [];
  private _edgeQueue: GraphEdge[] = [];
  // All edges seen so far, kept (not drained) so compound-group grouping can
  // read the real 'contains' edges — addEdge's queue above is consumed by
  // the rAF render loop and doesn't retain them.
  private _allEdges: GraphEdge[] = [];
  private _rafId: number | null = null;
  private _streamDone = false;
  private _batchSize = 1;           // updated when total is known via setTotal()
  private _totalNodes = 0;
  private _nodeCountByDepth = new Map<number, number>();

  // Loading overlay shown before first data arrives
  private _loadingOverlay: HTMLDivElement | null = null;

  // Compound layout backgrounds
  private _backgroundGroup: d3.Selection<SVGGElement, unknown, null, undefined>;
  private _compoundManager = new CompoundLayoutManager();
  private _childrenMap: Map<string, string[]> = new Map();
  // The group outlines as last drawn, so a fit frames them; empty while
  // Group Outlines is off.
  private _groupBounds: GroupBounds[] = [];
  // The box each outline's label was set in, by the outline's node id, so a
  // fit frames the label with its outline.
  private _outlineLabelBoxes = new Map<string, Box>();
  // Each outline's label as drawn, with the outline it names, so a map can set
  // it again when a zoom resizes it.
  private _outlineNames: { el: SVGTextElement; bound: GroupBounds }[] = [];
  // Which nodes the host's view state hides (`setHiddenTest`), so a fit
  // leaves them out; none until it says.
  private _isHidden: (id: string) => boolean = () => false;
  // O(1) lookup for child drag propagation — populated in _renderNode, avoids CSS selector per-frame
  private _nodeGroupEl = new Map<string, SVGGElement>();

  // Theme colors resolved once at init
  private themeSecondary: string;
  private themeAccent: string;
  private themeFontMuted: string;

  constructor(container: HTMLElement, styling?: GraphStylingOptions) {
    this.styling = {
      layout: styling?.layout ?? 'spring_layout',
      enablePhysics: styling?.enablePhysics ?? false,
      chargeStrength: styling?.chargeStrength ?? -350,
      linkDistance: styling?.linkDistance ?? 120,
      nodeSize: styling?.nodeSize ?? 4,
      nodeOpacity: styling?.nodeOpacity ?? 0.75,
      nodeBorderWidth: styling?.nodeBorderWidth ?? 0,
      edgeWidth: styling?.edgeWidth ?? 1.0,
      edgeOpacity: styling?.edgeOpacity ?? 1.0,
      showNodeLabels: styling?.showNodeLabels ?? false,
      showEdgeLabels: styling?.showEdgeLabels ?? false,
      labelSize: styling?.labelSize ?? 9,
      labelColor: styling?.labelColor ?? '#aaaaaa',
      interactionProfile: styling?.interactionProfile ?? 'default',
      colorBy: styling?.colorBy ?? 'auto',
    };

    container.innerHTML = '';
    this._container = container;
    this.width = container.clientWidth || 800;
    this.height = container.clientHeight || 600;

    const getThemeColor = (v: string, fb: string) =>
      getComputedStyle(document.documentElement).getPropertyValue(v).trim() || fb;
    this.themeSecondary = getThemeColor('--c-secondary', '#00ff41');
    this.themeAccent = getThemeColor('--c-accent', '#00d4ff');
    this.themeFontMuted = getThemeColor('--c-font-muted', '#00aa2a');

    this.svg = d3
      .select(container)
      .append('svg')
      .attr('width', this.width)
      .attr('height', this.height)
      .attr('viewBox', [0, 0, this.width, this.height]);

    this.zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.05, 10])
      .on('zoom', (event) => {
        this.g.attr('transform', event.transform);
        this._zoomK = event.transform.k;
        if (this._map) this._keepNamesReadable();
      })
      .on('end', () => {
        if (this._map) this._declutterNames();
      });

    this.svg.call(this.zoom);

    this.g = this.svg.append('g');
    // Background group must be first child so circles render behind links/nodes
    this._backgroundGroup = this.g.insert('g', ':first-child').attr('class', 'compound-backgrounds') as any;
    this.linkGroup = this.g.append('g').attr('class', 'links');
    this.nodeGroup = this.g.append('g').attr('class', 'nodes');
    this.labelGroup = this.g.append('g').attr('class', 'labels');

    // Backend spring layout places nodes at positions ≈ (x*100, y*100) centred on (0,0).
    // Without an initial transform that origin maps to the SVG top-left corner, so
    // nodes appear in the wrong place. Translate the origin to the viewport centre so
    // nodes are visible immediately as they stream in.
    this.svg.call(
      this.zoom.transform as any,
      d3.zoomIdentity.translate(this.width / 2, this.height / 2)
    );

    if (typeof ResizeObserver !== 'undefined') {
      const obs = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          const fit = this._fitOnResize;
          this._fitOnResize = false;
          const w = container.clientWidth || this.width;
          const h = container.clientHeight || this.height;
          if (!w || !h || (w === this.width && h === this.height)) return;
          this.width = w;
          this.height = h;
          this.svg.attr('width', w).attr('height', h).attr('viewBox', [0, 0, w, h]);
          if (fit) this._fitView();
        });
      });
      obs.observe(container);
    }

    // Large loading overlay — hidden once the first meta event arrives
    container.style.position = 'relative';
    const overlay = document.createElement('div');
    overlay.className = 'sr-loading-overlay';
    const icon = document.createElement('div');
    icon.className = 'sr-loading-icon';
    icon.textContent = '◈';
    const label = document.createElement('div');
    label.className = 'sr-loading-label';
    label.textContent = 'Fetching…';
    overlay.appendChild(icon);
    overlay.appendChild(label);
    container.appendChild(overlay);
    this._loadingOverlay = overlay;
  }

  /** Called from onMeta — tunes batch size and dismisses the loading overlay. */
  setTotal(total: number): void {
    this._totalNodes = total;
    this._batchSize = nodesPerFrame(total);
    if (this._loadingOverlay) {
      this._loadingOverlay.style.opacity = '0';
      setTimeout(() => { this._loadingOverlay?.remove(); this._loadingOverlay = null; }, 300);
    }
  }

  /** Enqueue a node — rendered progressively by the rAF loop. */
  addNode(node: GraphNode): void {
    this._assignVisuals(node);
    // Store position immediately so edges added later can reference it
    this.nodeById.set(node.id, node);
    this._nodeQueue.push(node);
    this._scheduleLoop();
  }

  /** Enqueue an edge — rendered after its source/target nodes appear. */
  addEdge(edge: GraphEdge): void {
    this._edgeQueue.push(edge);
    this._allEdges.push(edge);
    this._scheduleLoop();
  }

  /**
   * Nodes this renderer had to place itself, and nodes it drew in total.
   *
   * Read after `finalize()`. `placed` counts only the ones that arrived
   * without an `x` or a `y`; `total` is every node drawn, so a caller can
   * say "3 of 400" rather than a bare number that means nothing without
   * the denominator.
   */
  layoutFallback(): { placed: number; total: number } {
    return { placed: this._ringPlaced, total: this.nodeById.size };
  }

  /** Called when the SSE stream is complete. Drains remaining queue then fits view. */
  finalize(): void {
    this._streamDone = true;
    this._scheduleLoop();
  }

  /** Update styling options on a live renderer (e.g. toggling labels from Graph Settings). */
  updateStyling(options: Partial<GraphStylingOptions>): void {
    Object.assign(this.styling, options);
    if (options.showNodeLabels !== undefined) this._mapNames = options.showNodeLabels;
    if (options.showNodeLabels !== undefined || options.showLabelsByDepth !== undefined) {
      this.labelGroup
        .selectAll<SVGTextElement, unknown>('text')
        .style('display', (_, i, els) => {
          const nodeId = els[i].getAttribute('data-node-id');
          const n = nodeId ? this.nodeById.get(nodeId) : undefined;
          return n && this._labelShown(n) ? 'block' : 'none';
        });
    }
    if (options.labelSize !== undefined) {
      this.labelGroup.selectAll('text').attr('font-size', options.labelSize);
      if (this._map) this._keepNamesReadable();
    }
    if (options.labelColor !== undefined) {
      this.labelGroup.selectAll('text').attr('fill', options.labelColor);
    }
    if (options.colorBy !== undefined) {
      // Recolour in place: the drawn graph is the same graph, read by a
      // different property. `data-base-fill` moves too, so a highlight that
      // restores the base restores the colour now chosen.
      for (const [id, el] of this._nodeGroupEl) {
        const n = this.nodeById.get(id);
        if (!n) continue;
        const fill = this._fillFor(n);
        d3.select(el).select('path').attr('fill', fill).attr('data-base-fill', fill);
      }
    }
    if (options.showCompoundGroups !== undefined) {
      if (options.showCompoundGroups) {
        this._drawCompoundBackgrounds();
      } else {
        this._backgroundGroup.selectAll('*').remove();
        this._groupBounds = [];
        this._outlineLabelBoxes = new Map();
        this._outlineNames = [];
      }
    }
  }

  // ── Private: rAF drain loop ────────────────────────────────────────────────

  private _scheduleLoop(): void {
    if (this._rafId === null) {
      this._rafId = requestAnimationFrame(() => this._tick());
    }
  }

  private _tick(): void {
    this._rafId = null;

    // Process a batch of nodes
    const nodeBatch = this._nodeQueue.splice(0, this._batchSize);
    for (const node of nodeBatch) {
      this._renderNode(node);
    }

    // Process a matching batch of edges (only when node queue caught up)
    if (this._nodeQueue.length === 0) {
      const edgeBatch = this._edgeQueue.splice(0, this._batchSize * 2);
      for (const edge of edgeBatch) {
        this._renderEdge(edge);
      }
    }

    const queuesEmpty = this._nodeQueue.length === 0 && this._edgeQueue.length === 0;

    if (!queuesEmpty) {
      // More work to do — schedule next frame
      this._scheduleLoop();
    } else if (this._streamDone) {
      // Everything rendered: draw the group outlines, then fit the view to
      // the graph with them, since they are drawn too.
      if (this.styling.showCompoundGroups !== false) {
        this._drawCompoundBackgrounds();
      }
      this._fitView();
    }
    // else: queues empty but stream not done yet — wait for more addNode calls
  }

  // ── Private: DOM rendering ─────────────────────────────────────────────────

  private _getDepthAwarePosition(node: GraphNode): [number, number] {
    const depth = (node.depth as number | undefined) ?? 0;
    const nodeCountAtDepth = (this._nodeCountByDepth.get(depth) ?? 0) + 1;
    this._nodeCountByDepth.set(depth, nodeCountAtDepth);

    // Place each depth on a separate ring to reduce overlap across layers.
    const radius = 100 + depth * 180;
    const slots = Math.max(8, nodeCountAtDepth);
    const angle = ((nodeCountAtDepth - 1) * 2 * Math.PI) / slots;

    return [
      this.width / 2 + radius * Math.cos(angle),
      this.height / 2 + radius * Math.sin(angle),
    ];
  }

  /**
   * Local, deterministic collision nudge for a newly-placed node - the
   * streaming equivalent of graph_renderer.ts's seed-and-settle collision
   * pass, but a one-shot check-against-neighbors instead of a running
   * simulation: this renderer has no d3.forceSimulation at all (by
   * design - it expects backend-computed positions and adds nodes one at
   * a time, not as a batch a simulation could settle together), so
   * porting graph_renderer.ts's approach directly isn't a good fit.
   * Applies to BOTH real backend positions and the depth-ring
   * placeholder - neither was ever checked against already-placed
   * siblings before. Skipped above a node-count threshold: this is
   * O(already-placed) per new node, i.e. O(N^2) across a full stream,
   * fine at normal repo sizes but not worth paying for on huge graphs
   * where a single node's local overlap matters far less anyway.
   */
  private _resolveCollision(node: GraphNode, x: number, y: number): [number, number] {
    if (this.nodeById.size > 300) return [x, y];
    const gap = (n: GraphNode) => this.styling.nodeSize! * depthSizeMultiplier(n) * 1.3;
    const nodeGap = gap(node);
    let px = x;
    let py = y;
    for (let attempt = 0; attempt < 12; attempt++) {
      let collided = false;
      for (const other of this.nodeById.values()) {
        if (other === node || other.x === undefined || other.y === undefined) continue;
        const dx = px - other.x;
        const dy = py - other.y;
        const dist = Math.hypot(dx, dy);
        const minDist = (nodeGap + gap(other)) / 2;
        if (dist < 0.001) {
          px += minDist;
          collided = true;
        } else if (dist < minDist) {
          const push = (minDist - dist) + 2;
          px += (dx / dist) * push;
          py += (dy / dist) * push;
          collided = true;
        }
      }
      if (!collided) break;
    }
    return [px, py];
  }

  private _renderNode(node: GraphNode): void {
    let x = node.x;
    let y = node.y;
    if (x === undefined || y === undefined) {
      [x, y] = this._getDepthAwarePosition(node);
      this._ringPlaced += 1;
    }
    [x, y] = this._resolveCollision(node, x, y);
    node.x = x;
    node.y = y;
    const size = this.styling.nodeSize! * depthSizeMultiplier(node);

    const group = this.nodeGroup
      .append('g')
      .attr('class', 'graph-node')
      .attr('data-node-id', node.id)
      .attr('transform', `translate(${x},${y}) scale(0)`)
      .attr('opacity', 0);

    // Bind the datum so an ExtensionContext built from this renderer carries
    // real node data, the same way the static renderer's selections do.
    group.datum(node);

    // Cache element for O(1) drag-propagation lookups (avoids per-frame CSS selector)
    this._nodeGroupEl.set(node.id, group.node()!);

    const baseFill = this._fillFor(node);
    group
      .append('path')
      // Shapes come from `node_shapes`, so the legend's swatches match.
      .attr('d', canvasPath(node, size))
      .attr('fill', baseFill)
      // Remembered so a colour override can be undone without re-deriving
      // the parser's visual grammar here.
      .attr('data-base-fill', baseFill)
      .attr('fill-opacity', this.styling.nodeOpacity!)
      .attr('stroke', '#fff')
      .attr('stroke-width', this.styling.nodeBorderWidth!);

    // A producer's `hover` says more than the label -- a capability's claim, a
    // region's measured use -- and edges already show theirs.
    group.append('title').text((node.hover as string) || node.label || node.id);

    // Pop-in entrance animation
    group
      .transition()
      .duration(220)
      .ease(d3.easeCubicOut)
      .attr('opacity', 1)
      .attr('transform', `translate(${x},${y}) scale(1)`);

    // A map's name is at most `MAP_NAME_CHARS`: a record's title is a
    // sentence, and the node's hover holds all of it.
    const name = String(node.label || node.id);
    const textEl = this.labelGroup
      .append('text')
      .attr('data-node-id', node.id)
      .text(this._map && name.length > MAP_NAME_CHARS ? `${name.slice(0, MAP_NAME_CHARS - 1)}…` : name)
      .attr('font-size', this._map ? this._nameSize(this.styling.labelSize!, MAP_NAME_PX) : this.styling.labelSize!)
      .attr('fill', this.styling.labelColor!)
      .style('display', this._labelShown(node) ? 'block' : 'none')
      .style('pointer-events', 'none');
    this._placeLabel(textEl, node, x, y, size);

    if (this._labelShown(node)) {
      textEl.attr('opacity', 0).transition().delay(180).duration(200).attr('opacity', 1);
    } else {
      textEl.attr('opacity', 1);
    }

    // ── Source navigation ──────────────────────────────────────────────────
    // Double-click opens the node's source through `openSource`, the opener
    // View → Source uses, on every node that names a file -- a Python symbol,
    // whose parser records no line, included: it opens its file at the top, as
    // a file node does. On a node from no file it opens nothing, and the
    // double-click goes on to the zoom.
    //
    // **RIGHT-CLICK IS THE RADIAL MENU'S.** A handler here once opened the
    // source on right-click and stopped the event, and on every other node
    // stopped it for nothing -- so rad, which listens on the canvas, never
    // heard a right-click on any node, and the node ring could not be opened
    // by mouse at all. rad prevents the browser's menu itself, and offers the
    // source as View → Source.
    //
    // On a map, a node from no file is a family or a project, and its
    // double-click opens that one's own showgraph instead: the index's way
    // into a family, and a family's into a project.
    group.on('dblclick', (event: MouseEvent) => {
      if (this.openSource(node.id, { x: event.clientX, y: event.clientY })) {
        event.stopPropagation();
      } else if (this._map && typeof node.show === 'string') {
        event.stopPropagation();
        this.getContainer().dispatchEvent(
          new CustomEvent(SHOW_OPEN_EVENT, { bubbles: true, detail: node.show }));
      }
    });

    // Drag support (no simulation — positions are pre-computed)
    group.call(
      d3.drag<SVGGElement, unknown>()
        .on('drag', (event) => {
          const dx = event.x - (node.x ?? event.x);
          const dy = event.y - (node.y ?? event.y);
          node.x = event.x;
          node.y = event.y;
          group.attr('transform', `translate(${event.x},${event.y})`);
          this._updateEdgesForNode(node.id, event.x, event.y);
          this._updateLabelForNode(node.id, event.x, event.y, size);

          // Propagate delta to compound hierarchy descendants.
          if (dx !== 0 || dy !== 0) {
            for (const childId of (this._childrenMap.get(node.id) ?? [])) {
              const child = this.nodeById.get(childId);
              if (!child) continue;
              child.x = (child.x ?? 0) + dx;
              child.y = (child.y ?? 0) + dy;
              const childEl = this._nodeGroupEl.get(childId);
              if (childEl) childEl.setAttribute('transform', `translate(${child.x},${child.y})`);
              this._updateEdgesForNode(childId, child.x, child.y);
              this._updateLabelForNode(childId, child.x, child.y, this.styling.nodeSize! * depthSizeMultiplier(child));
            }
          }
        })
        .on('end', () => {
          // Redraw compound background circles to follow moved nodes.
          if (this._childrenMap.size > 0) this._drawCompoundBackgrounds();
        }) as any
    );
  }

  private _renderEdge(edge: GraphEdge): void {
    const sourceId = typeof edge.source === 'string' ? edge.source : (edge.source as GraphNode).id;
    const targetId = typeof edge.target === 'string' ? edge.target : (edge.target as GraphNode).id;
    const src = this.nodeById.get(sourceId);
    const tgt = this.nodeById.get(targetId);

    // **THE CHANNELS RIDE IN `metadata`.** gJGF puts every edge attribute the
    // serializer was given -- `color`, `size`, `style`, `measured`, `hover` --
    // under `edge.metadata`, and this read `edge.color` at the top level, which
    // is never there. So a topology whose caveat said "an unmeasured edge is
    // drawn dashed, never thin" drew every edge solid grey at one width: the
    // producer's care at the far end, lost at the last step. A top-level field
    // still wins when a caller sets one.
    const md = (edge.metadata ?? {}) as Record<string, unknown>;
    const colour = (edge.color as string) || (md.color as string) || '#555';
    const width = typeof md.size === 'number' ? md.size : this.styling.edgeWidth!;
    const style = (edge.style as string) || (md.style as string) || 'solid';
    const title = (md.hover as string) || (md.title as string) || '';

    const line = this.linkGroup
      .append('line')
      .attr('class', 'stream-edge')
      .attr('data-from', sourceId)
      .attr('data-to', targetId)
      .attr('data-style', style)
      .attr('x1', src?.x ?? 0)
      .attr('y1', src?.y ?? 0)
      .attr('x2', tgt?.x ?? 0)
      .attr('y2', tgt?.y ?? 0)
      .attr('stroke', colour)
      .attr('stroke-opacity', this.styling.edgeOpacity! * 0.6)
      .attr('stroke-width', width)
      .attr('opacity', 0);
    if (style === 'dashed') line.attr('stroke-dasharray', '6,4');
    else if (style === 'dotted') line.attr('stroke-dasharray', '2,3');
    if (title) line.append('title').text(title);
    line.transition().duration(180).attr('opacity', 1);
  }

  // ── Extension seam ─────────────────────────────────────────────────────────
  //
  // The interaction layer used to hang off graph_renderer.ts, which no
  // code-map path mounts: Load Demo, plot repo, plot file, cache recall and
  // bookmark replay all render here. Everything below exists so an extension
  // can attach to THIS renderer, which is the whole of the M1 fix. Nothing
  // here knows what an extension does with it.

  /** Nodes rendered so far, by id. */
  getNodes(): GraphNode[] {
    return Array.from(this.nodeById.values());
  }

  getEdges(): GraphEdge[] {
    return this._allEdges;
  }

  /** The container the renderer was constructed against. */
  getContainer(): HTMLElement {
    return this.svg.node()!.parentElement as HTMLElement;
  }

  /**
   * An `ExtensionContext` describing the current scene.
   *
   * Rebuilt on request rather than cached: nodes stream in, so a context
   * captured once would describe a graph that no longer exists. Selections
   * are re-derived for the same reason.
   */
  buildExtensionContext(selectedNodes: Set<GraphNode>, onGraphChange?: () => void): ExtensionContext<GraphNode, GraphEdge> {
    return {
      svg: this.svg,
      graphGroup: this.g,
      nodes: this.nodeGroup.selectAll<SVGGElement, GraphNode>('g.graph-node'),
      edges: this.linkGroup.selectAll<SVGLineElement, GraphEdge>('line.stream-edge'),
      labels: this.labelGroup.selectAll<SVGTextElement, GraphNode>('text'),
      zoom: this.zoom,
      // No force simulation on this renderer — positions come from the
      // backend layout. Extensions must treat `simulation` as optional, and
      // the canvas ring disables `toggle-physics` accordingly.
      simulation: undefined,
      container: this.getContainer(),
      data: { nodes: this.getNodes(), edges: this._allEdges },
      selectedNodes,
      onGraphChange,
    };
  }

  /**
   * How to tell a hidden node, so a fit leaves it out. Hide is view state the
   * host keeps and paints (rad's `applyViewState` draws the node at opacity
   * 0); the node stays here, in `nodeById`, and a fit that framed it would be
   * centred off what is drawn.
   */
  setHiddenTest(isHidden: (id: string) => boolean): void {
    this._isHidden = isHidden;
  }

  /** Public so an intent can ask for a fit without reaching into the DOM. */
  fitView(): void {
    this._fitView();
  }

  /**
   * Fit the drawing to the canvas at the size the dock has just given it, or
   * do nothing when the canvas keeps its size, so the reader's zoom stands.
   *
   * **THE FIT WAITS FOR THE RESIZE OBSERVER.** The dock sizes the canvas at
   * once, and the canvas measures at its new size, but the svg and the size a
   * fit frames into (`width`, `height`) follow only when the observer fires.
   * A fit before then frames the drawing in the size the canvas had, and the
   * observer's frame comes when it comes, so no delay is the right one.
   *
   * A canvas back at its size before the observer saw it go -- into Read and
   * out within a frame -- clears the fit asked for: the observer will not
   * fire, and the fit would wait for the next resize, a reader's own.
   */
  fitWhenResized(): void {
    const w = this._container.clientWidth;
    const h = this._container.clientHeight;
    this._fitOnResize = !!w && !!h && (w !== this.width || h !== this.height);
  }

  /** Fit the viewport to these nodes only. Unknown ids are ignored. */
  fitTo(ids: string[]): void {
    const nodes = ids.map((id) => this.nodeById.get(id)).filter((n): n is GraphNode => !!n);
    this._fitNodes(nodes);
  }

  /** Remove nodes and any edge touching them. Used by the `delete` verb. */
  removeNodes(ids: string[]): void {
    const gone = new Set(ids);
    for (const id of ids) {
      this.nodeById.delete(id);
      this._nodeGroupEl.delete(id);
      this.nodeGroup.select(`g.graph-node[data-node-id="${CSS.escape(id)}"]`).remove();
      this.labelGroup.selectAll(`text[data-node-id="${CSS.escape(id)}"]`).remove();
    }
    this._allEdges = this._allEdges.filter(
      (e) => !gone.has(String(e.source)) && !gone.has(String(e.target)),
    );
    // Prune the containment map too. It is otherwise only rebuilt on the
    // next relayout, so until then `childIdsOf` would keep naming children
    // that are no longer on the canvas.
    for (const id of ids) this._childrenMap.delete(id);
    for (const [parent, kids] of this._childrenMap) {
      if (kids.some((k) => gone.has(k))) {
        this._childrenMap.set(parent, kids.filter((k) => !gone.has(k)));
      }
    }
    this.linkGroup
      .selectAll<SVGLineElement, GraphEdge>('line.stream-edge')
      .filter((d) => !!d && (gone.has(String(d.source)) || gone.has(String(d.target))))
      .remove();
    // The outlines are drawn around what remains: a collapsed file's goes,
    // and one that lost nodes shrinks to the rest. The fit frames the
    // outlines kept here, so one left as it was framed an empty circle.
    const drawn = this._groupBounds;
    this._groupBounds = outlinesAfterRemoval(
      this._compoundManager, drawn, Array.from(this.nodeById.values()), this._allEdges, this._outlineSpacing(),
    );
    if (drawn.length > 0) this._paintOutlines(this._groupBounds, false);
  }

  /** Ids of nodes whose parent is `id`, per the accumulated containment edges. */
  childIdsOf(id: string): string[] {
    return this._childrenMap.get(id) ?? [];
  }

  /** Merge freshly parsed nodes/edges into the live scene, then settle. */
  mergeGraph(nodes: GraphNode[], edges: GraphEdge[]): void {
    for (const n of nodes) {
      if (this.nodeById.has(n.id)) continue;
      this.addNode(n);
    }
    for (const e of edges) this.addEdge(e);
    this._streamDone = true;
    this._scheduleLoop();
  }

  private _fitView(): void {
    this._fitNodes(Array.from(this.nodeById.values()));
  }

  /**
   * Fit the viewport to a subset of nodes: each node's extent, its label
   * while labels are shown, and the group outline drawn around any of them,
   * framed whole (fit.ts). A hidden node is left out, and so is an outline
   * holding only hidden nodes.
   *
   * Split out of `_fitView` so `focus-group` can frame one subtree. A verb
   * that says "focus" and fits the whole graph is the kind of near-miss the
   * legacy menu was full of.
   */
  private _fitNodes(nodes: GraphNode[]): void {
    const t = this._map ? this._fitMap(nodes) : this._fitAsDrawn(nodes);
    if (!t) return;

    this.svg
      .transition()
      .duration(700)
      .call(
        this.zoom.transform as any,
        d3.zoomIdentity.translate(t.x, t.y).scale(t.k)
      );
  }

  /** The transform that frames `nodes` with their labels and outlines as they are drawn now. */
  private _fitAsDrawn(nodes: GraphNode[]): ReturnType<typeof fitTransform> {
    const labels = this._shownLabelBoxes();
    const framed: FramedNode[] = nodes.map((n) => ({
      id: n.id,
      x: n.x ?? 0,
      y: n.y ?? 0,
      reach: this._extentOf(n),
      label: labels.get(n.id) ?? null,
    }));
    const outlines: FramedOutline[] = this._groupBounds.map((b) => ({
      nodeId: b.nodeId, x: b.cx, y: b.cy, r: b.radius, label: this._outlineLabelBoxes.get(b.nodeId) ?? null,
    }));
    const extents = framedExtents(framed, outlines, (id) => this._childrenMap.get(id) ?? [], this._isHidden);
    return fitTransform(extents, { width: this.width, height: this.height });
  }

  /**
   * The fit of a map: framed with its names at the size they are drawn at the
   * zoom it lands on.
   *
   * **A MAP'S NAMES ARE SIZED BY THE ZOOM, SO THE FIT CANNOT MEASURE THEM
   * FIRST.** A name is drawn at least `MAP_NAME_PX` on screen, so the further
   * out the fit frames, the more of the graph it takes. The fit measured the
   * names as they were drawn before it moved -- at zoom 1, a third of their
   * size at the index's fit -- framed those, and the names then grew past what
   * was framed and across their outlines' rims; a second Fit measured them
   * grown and chose another frame. Here the names are sized for a zoom, the
   * fit for that size is found, and the names sized for its zoom, until the
   * zoom holds. It starts from zoom 1 every time, so a second Fit over the same
   * graph lands where the first did.
   */
  private _fitMap(nodes: GraphNode[]): ReturnType<typeof fitTransform> {
    let k = 1;
    let t: ReturnType<typeof fitTransform> = null;
    for (let tries = 0; tries < 8; tries++) {
      this._sizeNames(k);
      t = this._fitAsDrawn(nodes);
      if (!t) break;
      const held = Math.abs(t.k - k) <= k * 1e-3;
      k = t.k;
      if (held) break;
    }
    // Drawn for the zoom on screen until the fit's transition moves it.
    this._sizeNames(this._zoomK);
    return t;
  }

  /**
   * The box each shown node label is drawn in, by node id, in graph
   * coordinates. A label is drawn `size + 12` under its node, centred, as
   * wide as its text, so a long one at the graph's edge reaches well past its
   * node; with outlines off, nothing else frames it. A label the label
   * settings hide is not drawn and has no box, and neither has one on a canvas
   * not yet laid out (a hidden tab), which measures as nothing.
   */
  private _shownLabelBoxes(): Map<string, Box> {
    const boxes = new Map<string, Box>();
    this.labelGroup.selectAll<SVGTextElement, unknown>('text').each(function () {
      const id = this.getAttribute('data-node-id');
      if (!id || this.style.display === 'none') return;
      let drawn: DOMRect;
      try {
        drawn = this.getBBox();
      } catch {
        return;
      }
      if (drawn.width === 0 && drawn.height === 0) return;
      boxes.set(id, { minX: drawn.x, minY: drawn.y, maxX: drawn.x + drawn.width, maxY: drawn.y + drawn.height });
    });
    return boxes;
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  /** How far a node's shape reaches from its centre: a shape drawn at `size`
   *  reaches 1.5 × size at most (a triangle's apex). */
  private _extentOf(n: GraphNode): number {
    return 1.5 * this.styling.nodeSize! * depthSizeMultiplier(n);
  }

  /** How far an outline is drawn past what it encloses, and how far each node in it reaches. */
  private _outlineSpacing(): OutlineSpacing {
    return { padding: 40, baseNodeSize: this.styling.nodeSize! * 3.0, radiusOf: (n) => this._extentOf(n) };
  }

  private _drawCompoundBackgrounds(): void {
    const nodes = Array.from(this.nodeById.values());
    const { padding, baseNodeSize, radiusOf } = this._outlineSpacing();
    const bounds = this._compoundManager.computeGroupBounds(nodes, this._allEdges, padding, baseNodeSize, radiusOf);
    this._childrenMap = this._compoundManager.computeChildrenMap(nodes, this._allEdges);
    this._groupBounds = bounds;
    this._paintOutlines(bounds, true);
  }

  /**
   * Draw `bounds` in place of the outlines drawn before. A fresh drawing
   * fades them in; a redraw after a removal sets them at once, as the others
   * were already on screen.
   */
  private _paintOutlines(bounds: readonly GroupBounds[], fadeIn: boolean): void {
    this._backgroundGroup.selectAll('*').remove();
    const labels: SVGTextElement[] = [];
    for (const b of bounds) {
      const isDir = b.depth === 0;
      // A map's outline is its group's: a family drawn in the family's hue.
      const hue = this._map ? d3.color(String(this.nodeById.get(b.nodeId)?.color ?? '')) : null;
      const tint = (opacity: number) => hue!.copy({ opacity }).formatRgb();
      const fill   = hue ? tint(isDir ? 0.07 : 0.10) : isDir ? 'rgba(127,140,141,0.06)' : 'rgba(155,89,182,0.09)';
      const stroke = hue ? tint(isDir ? 0.45 : 0.55) : isDir ? 'rgba(127,140,141,0.30)' : 'rgba(155,89,182,0.35)';
      const dash   = isDir ? '8,4' : '4,2';
      const sw     = isDir ? 1.5 : 1.0;
      const grp = this._backgroundGroup.append('g').attr('class', `compound-group depth-${b.depth}`);
      const circle = grp.append('circle')
        .attr('cx', b.cx)
        .attr('cy', b.cy)
        .attr('r', b.radius)
        .attr('fill', fill)
        .attr('stroke', stroke)
        .attr('stroke-width', sw)
        .attr('stroke-dasharray', dash);
      if (fadeIn) circle.style('opacity', 0).transition().delay(300).duration(500).style('opacity', 1);
      labels.push(grp.append('text')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('data-base-size', isDir ? 11 : 9)
        .attr('font-size', this._map ? this._nameSize(isDir ? 11 : 9, MAP_OUTLINE_PX) : isDir ? 11 : 9)
        .attr('fill', hue ? tint(0.9) : isDir ? 'rgba(127,140,141,0.70)' : 'rgba(155,89,182,0.70)')
        .style('pointer-events', 'none')
        .style('opacity', fadeIn ? 0 : 1)
        .text(b.label)
        .node()!);
    }
    this._outlineNames = labels.map((el, i) => ({ el, bound: bounds[i] }));
    this._placeOutlineNames();
    if (fadeIn) {
      for (const label of labels) d3.select(label).transition().delay(300).duration(500).style('opacity', 1);
    }
  }

  /**
   * Each outline's label where it covers no other label and no node, inside
   * its outline when it fits there (outline_labels.ts), measured at the size
   * it is drawn: after a removal too, and on a map whenever a zoom resizes
   * the names. Each label's box as placed is what the fit frames with its
   * outline.
   */
  private _placeOutlineNames(): void {
    const names = this._outlineNames;
    const nodes = Array.from(this.nodeById.values());
    const sizes = names.map(({ el }) => el.getBBox());
    const places = placeOutlineLabels(
      names.map(({ bound: b }, i) => ({ cx: b.cx, cy: b.cy, r: b.radius, w: sizes[i].width, h: sizes[i].height })),
      nodes.map((n) => ({ x: n.x ?? 0, y: n.y ?? 0, r: this._extentOf(n) })),
    );
    this._outlineLabelBoxes = new Map();
    names.forEach(({ el, bound }, i) => {
      el.setAttribute('x', String(places[i].x));
      el.setAttribute('y', String(places[i].y));
      const { width, height } = sizes[i];
      this._outlineLabelBoxes.set(bound.nodeId, {
        minX: places[i].x - width / 2,
        minY: places[i].y - height / 2,
        maxX: places[i].x + width / 2,
        maxY: places[i].y + height / 2,
      });
    });
  }

  /**
   * Where a node's source is, read against the graph drawn here: a symbol that
   * names only its file's stem or module is found through the file node it is
   * drawn inside. Null for a node from no file.
   */
  sourceTargetOf(id: string): SourceTarget | null {
    const node = this.nodeById.get(id);
    return node ? sourceTarget(node, { nodes: this.nodeById, edges: this._allEdges }) : null;
  }

  /**
   * Open a node's source: its forge page in a new tab, or for a file with no
   * page (read from disk, or uploaded) a badge naming the file and line beside
   * `at` (the node's own place on screen when not given), on one line and
   * wholly inside the canvas. View → Source and a double-click both call
   * this. False for a node from no file, which opens nothing.
   */
  openSource(id: string, at?: { x: number; y: number }): boolean {
    const target = this.sourceTargetOf(id);
    if (!target) return false;
    if (target.kind === 'forge') {
      window.open(target.href, '_blank', 'noopener');
      return true;
    }

    const point = at ?? this._screenCentreOf(id);
    document.querySelectorAll('.source-badge').forEach((old) => old.remove());
    // The badge stays inside the canvas, and so inside the window: a path from
    // a deep checkout is wider than the space to the pointer's right, and
    // often than the canvas. `area` is the part of the window the canvas
    // covers, in viewport coordinates.
    const canvas = this.getContainer().getBoundingClientRect();
    const view = {
      width: document.documentElement.clientWidth || window.innerWidth,
      height: document.documentElement.clientHeight || window.innerHeight,
    };
    const areaLeft = Math.max(0, canvas.left);
    const areaTop = Math.max(0, canvas.top);
    const area = {
      left: areaLeft,
      top: areaTop,
      width: Math.max(0, Math.min(canvas.right, view.width) - areaLeft),
      height: Math.max(0, Math.min(canvas.bottom, view.height) - areaTop),
    };
    const room = Math.max(0, area.width - 2 * BADGE_MARGIN);
    const badge = document.createElement('div');
    badge.className = 'source-badge';
    // Measured at the window's top left, where its whole width is free, on one
    // line; shortened to `room` when it is wider, then placed by `badgePlace`
    // so that none of it is outside `area`.
    badge.style.cssText = [
      'position:fixed',
      'left:0',
      'top:0',
      `max-width:${room}px`,
      'box-sizing:border-box',
      'overflow:hidden',
      'z-index:9999',
      'background:#1a1a1a',
      'border:1px solid #00ff4140',
      'color:#00ff41',
      'padding:4px 8px',
      'font-size:11px',
      'font-family:monospace',
      'border-radius:4px',
      // It takes the pointer, so its title shows the whole path when the
      // text is shortened; it sits beside the pointer, never under it.
      'cursor:default',
      'white-space:nowrap',
    ].join(';');
    badge.title = target.text;
    badge.textContent = target.text;
    document.body.appendChild(badge);
    // Shortened from the middle when it does not fit (node_info.ts). The font
    // is monospace, so a character's width is the measured mean.
    const padding = 16;
    const textWidth = badge.scrollWidth - padding;
    const chrome = badge.offsetWidth - badge.clientWidth + padding; // border and padding
    if (textWidth + chrome > room && target.text.length > 0) {
      const perChar = textWidth / target.text.length;
      badge.textContent = fitBadgeText(target.text, Math.floor((room - chrome) / perChar));
    }
    const drawn = badge.getBoundingClientRect();
    const place = badgePlace(
      { x: point.x - area.left, y: point.y - area.top },
      { width: drawn.width, height: drawn.height },
      area,
    );
    badge.style.left = `${area.left + place.left}px`;
    badge.style.top = `${area.top + place.top}px`;
    setTimeout(() => badge.remove(), 3500);
    return true;
  }

  /** Where a node is drawn, in viewport coordinates; the canvas centre if it is not. */
  private _screenCentreOf(id: string): { x: number; y: number } {
    const rect = (this._nodeGroupEl.get(id) ?? this.svg.node())?.getBoundingClientRect();
    return rect ? { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 } : { x: 0, y: 0 };
  }

  /** Draw this graph as a map (see `_map`). Called before its nodes arrive. */
  presentAsMap(): void {
    this._map = true;
  }

  /** Whether a node's name is drawn: on a map, unless an outline already says it. */
  private _labelShown(node: GraphNode): boolean {
    if (this._map) return this._mapNames && node.label_at !== 'none';
    return this._shouldShowLabel((node.depth as number) ?? 2);
  }

  /** A font size, in the graph's units, that is at least `floorPx` on screen at zoom `k`. */
  private _nameSize(base: number, floorPx: number, k = this._zoomK): number {
    return Math.max(base, floorPx / (k || 1));
  }

  /** On a map, every name at least its floor on screen, at the zoom just set. */
  private _keepNamesReadable(): void {
    this._sizeNames(this._zoomK);
  }

  /**
   * Every name at least its floor on screen at zoom `k`, and the outline names
   * set again for that size when it changed theirs: placed for a name a third
   * the size, each was drawn across its outline's rim and over its
   * neighbours'.
   */
  private _sizeNames(k: number): void {
    this.labelGroup.selectAll<SVGTextElement, unknown>('text')
      .attr('font-size', this._nameSize(this.styling.labelSize!, MAP_NAME_PX, k));
    let resized = false;
    for (const { el } of this._outlineNames) {
      const size = String(this._nameSize(Number(el.getAttribute('data-base-size')), MAP_OUTLINE_PX, k));
      if (el.getAttribute('font-size') === size) continue;
      el.setAttribute('font-size', size);
      resized = true;
    }
    if (resized) this._placeOutlineNames();
  }

  /**
   * On a map, hide each name that would overlap one ranked above it, once a
   * zoom has settled; zooming in gives them room and they come back.
   *
   * **A NAME KEPT READABLE TAKES MORE OF THE GRAPH THE FURTHER OUT IT IS.**
   * At the index's fit a ten-pixel name is about twenty-five units of the
   * graph high and a long one two hundred wide, so neighbours' names met
   * however the server spaced them -- spacing is framed away by the fit.
   * Outline names are never hidden, and hold their place first. Then
   * families, then projects, then repositories, then anything else; a
   * shorter name before a longer one. A hidden name stays in its node's
   * hover.
   */
  private _declutterNames(): void {
    if (!this._mapNames) return;
    type Box = { x: number; y: number; width: number; height: number };
    const meets = (a: Box, b: Box) =>
      a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
    const taken: Box[] = this._backgroundGroup
      .selectAll<SVGTextElement, unknown>('text').nodes().map((t) => t.getBBox());
    const rank: Record<string, number> = { family: 0, project: 1, repository: 2 };
    const texts = this.labelGroup.selectAll<SVGTextElement, unknown>('text').nodes()
      .filter((t) => t.style.display !== 'none')
      .map((t) => {
        const node = this.nodeById.get(t.getAttribute('data-node-id') ?? '');
        return { t, rank: rank[String(node?.kind)] ?? 3, length: (t.textContent ?? '').length };
      })
      .sort((a, b) => a.rank - b.rank || a.length - b.length);
    for (const { t } of texts) {
      const box = t.getBBox();
      const hidden = taken.some((other) => meets(box, other));
      t.setAttribute('visibility', hidden ? 'hidden' : 'visible');
      if (!hidden) taken.push(box);
    }
  }

  /**
   * Where a node's name goes. Under it, centred, as every graph has it, or on
   * a map on the side its `label_at` says: outward from the ring the server
   * packed it on, so neighbours' names do not run into each other.
   */
  private _placeLabel(
    text: d3.Selection<SVGTextElement, unknown, null, undefined>,
    node: GraphNode, x: number, y: number, size: number,
  ): void {
    const side = this._map ? node.label_at : undefined;
    const gap = size + 5;
    const [dx, dy, anchor, baseline] =
      side === 'right' ? [gap, 0, 'start', 'central']
      : side === 'left' ? [-gap, 0, 'end', 'central']
      : side === 'above' ? [0, -gap, 'middle', 'auto']
      : side === 'below' ? [0, gap, 'middle', 'hanging']
      : [0, size + 12, 'middle', 'auto'];
    text.attr('x', x + dx).attr('y', y + dy)
      .attr('text-anchor', anchor).attr('dominant-baseline', baseline);
  }

  private _shouldShowLabel(depth: number): boolean {
    const byDepth = this.styling.showLabelsByDepth as Partial<Record<number, boolean>> | undefined;
    if (byDepth && depth in byDepth) return byDepth[depth]!;
    return this.styling.showNodeLabels ?? false;
  }

  private _assignVisuals(node: GraphNode): void {
    const kind = node.kind as string | undefined;
    const depth = node.depth as number | undefined;

    if (!node.shape) {
      if (depth === 0) node.shape = 'diamond';
      else if (depth === 1) node.shape = 'square';
      else if (kind === 'function' || kind === 'async_function') node.shape = 'hexagon';
      else if (kind === 'class' || kind === 'struct') node.shape = 'square';
      else if (kind === 'import' || kind === 'call') node.shape = 'triangle';
      else node.shape = 'circle';
    }

    if (!node.color || node.color === 'steelblue') {
      if (depth === 0) node.color = '#7f8c8d';
      else if (depth === 1) node.color = '#9b59b6';
      else if (kind === 'function' || kind === 'async_function') node.color = this.themeSecondary;
      else if (kind === 'class') node.color = this.themeAccent;
      else if (kind === 'struct' || kind === 'union') node.color = '#4a90d9';
      else if (kind === 'import') node.color = '#e74c3c';
      else if (kind === 'call') node.color = this.themeFontMuted;
      else node.color = '#95a5a6';
    }
  }

  /**
   * The fill a node is drawn with: `drawnFill`, which the key reads too, so a
   * swatch and the node it stands for are one decision rather than two.
   */
  private _fillFor(node: GraphNode): string {
    return drawnFill(node, this.styling.colorBy);
  }

  private _updateEdgesForNode(nodeId: string, x: number, y: number): void {
    this.linkGroup.selectAll<SVGLineElement, unknown>(`[data-from="${nodeId}"]`)
      .attr('x1', x).attr('y1', y);
    this.linkGroup.selectAll<SVGLineElement, unknown>(`[data-to="${nodeId}"]`)
      .attr('x2', x).attr('y2', y);
  }

  private _updateLabelForNode(nodeId: string, x: number, y: number, size: number): void {
    // Labels are rendered in document order matching nodeById insertion order
    // We track them by data attribute for simplicity
    const node = this.nodeById.get(nodeId);
    const text = this.labelGroup.selectAll<SVGTextElement, unknown>(`text[data-node-id="${nodeId}"]`);
    if (node) {
      text.each((_, i, els) => this._placeLabel(d3.select(els[i]), node, x, y, size));
    } else {
      text.attr('x', x).attr('y', y + size + 12);
    }
  }
}
