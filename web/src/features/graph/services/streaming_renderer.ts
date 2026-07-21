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
import { GraphNode, GraphEdge } from './graph_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { CompoundLayoutManager } from './compound_layout';
import { depthSizeMultiplier } from './depth_scale';

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
  private styling: GraphStylingOptions;
  private width: number;
  private height: number;

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
    };

    container.innerHTML = '';
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
      .on('zoom', (event) => this.g.attr('transform', event.transform));

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
          const w = container.clientWidth || this.width;
          const h = container.clientHeight || this.height;
          if (!w || !h || (w === this.width && h === this.height)) return;
          this.width = w;
          this.height = h;
          this.svg.attr('width', w).attr('height', h).attr('viewBox', [0, 0, w, h]);
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

  /** Called when the SSE stream is complete. Drains remaining queue then fits view. */
  finalize(): void {
    this._streamDone = true;
    this._scheduleLoop();
  }

  /** Update styling options on a live renderer (e.g. toggling labels from Graph Settings). */
  updateStyling(options: Partial<GraphStylingOptions>): void {
    Object.assign(this.styling, options);
    if (options.showNodeLabels !== undefined || options.showLabelsByDepth !== undefined) {
      this.labelGroup
        .selectAll<SVGTextElement, unknown>('text')
        .style('display', (_, i, els) => {
          const nodeId = els[i].getAttribute('data-node-id');
          const n = nodeId ? this.nodeById.get(nodeId) : undefined;
          const depth = ((n?.depth as number) ?? 2);
          return this._shouldShowLabel(depth) ? 'block' : 'none';
        });
    }
    if (options.labelSize !== undefined) {
      this.labelGroup.selectAll('text').attr('font-size', options.labelSize);
    }
    if (options.labelColor !== undefined) {
      this.labelGroup.selectAll('text').attr('fill', options.labelColor);
    }
    if (options.showCompoundGroups !== undefined) {
      if (options.showCompoundGroups) {
        this._drawCompoundBackgrounds();
      } else {
        this._backgroundGroup.selectAll('*').remove();
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
      // Everything rendered — fit the view and draw compound group backgrounds
      this._fitView();
      if (this.styling.showCompoundGroups !== false) {
        this._drawCompoundBackgrounds();
      }
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

    // Cache element for O(1) drag-propagation lookups (avoids per-frame CSS selector)
    this._nodeGroupEl.set(node.id, group.node()!);

    group
      .append('path')
      .attr('d', this._nodePath(node.shape as string, size))
      .attr('fill', (node.color as string) || 'steelblue')
      .attr('fill-opacity', this.styling.nodeOpacity!)
      .attr('stroke', '#fff')
      .attr('stroke-width', this.styling.nodeBorderWidth!);

    group.append('title').text(node.label || node.id);

    // Pop-in entrance animation
    group
      .transition()
      .duration(220)
      .ease(d3.easeCubicOut)
      .attr('opacity', 1)
      .attr('transform', `translate(${x},${y}) scale(1)`);

    const textEl = this.labelGroup
      .append('text')
      .attr('data-node-id', node.id)
      .attr('x', x)
      .attr('y', y + size + 12)
      .text(node.label || node.id)
      .attr('font-size', this.styling.labelSize!)
      .attr('text-anchor', 'middle')
      .attr('fill', this.styling.labelColor!)
      .style('display', this._shouldShowLabel((node.depth as number) ?? 2) ? 'block' : 'none')
      .style('pointer-events', 'none');

    if (this._shouldShowLabel((node.depth as number) ?? 2)) {
      textEl.attr('opacity', 0).transition().delay(180).duration(200).attr('opacity', 1);
    } else {
      textEl.attr('opacity', 1);
    }

    // ── Source navigation ──────────────────────────────────────────────────
    // Right-click or double-click on a symbol node → open github.com/blob
    // view at the node's line number. Right-click calls preventDefault() so
    // the browser's native context menu never appears; double-click is the
    // modifier-key-free alternative.
    const depth = (node.depth as number) ?? 0;
    const line  = Number(node.line)  || 0;
    const file  = (node.file as string) || '';

    if (depth >= 2 && line > 0) {
      group
        .on('contextmenu', (event: MouseEvent) => {
          event.preventDefault();
          event.stopPropagation();
          this._openSource(file, line, (node.label as string) || node.id, event.clientX, event.clientY);
        })
        .on('dblclick', (event: MouseEvent) => {
          event.stopPropagation();
          this._openSource(file, line, (node.label as string) || node.id, event.clientX, event.clientY);
        });
    } else if (depth < 2) {
      // Dir/file nodes: right-click only prevents browser menu (no source to show)
      group.on('contextmenu', (event: MouseEvent) => {
        event.preventDefault();
        event.stopPropagation();
      });
    }

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

    this.linkGroup
      .append('line')
      .attr('class', 'stream-edge')
      .attr('data-from', sourceId)
      .attr('data-to', targetId)
      .attr('x1', src?.x ?? 0)
      .attr('y1', src?.y ?? 0)
      .attr('x2', tgt?.x ?? 0)
      .attr('y2', tgt?.y ?? 0)
      .attr('stroke', (edge.color as string) || '#555')
      .attr('stroke-opacity', this.styling.edgeOpacity! * 0.6)
      .attr('stroke-width', this.styling.edgeWidth!)
      .attr('opacity', 0)
      .transition()
      .duration(180)
      .attr('opacity', 1);
  }

  private _fitView(): void {
    if (this.nodeById.size === 0) return;
    const nodes = Array.from(this.nodeById.values());

    const avgX = nodes.reduce((s, n) => s + (n.x ?? 0), 0) / nodes.length;
    const avgY = nodes.reduce((s, n) => s + (n.y ?? 0), 0) / nodes.length;
    const minX = Math.min(...nodes.map(n => n.x ?? 0));
    const maxX = Math.max(...nodes.map(n => n.x ?? 0));
    const minY = Math.min(...nodes.map(n => n.y ?? 0));
    const maxY = Math.max(...nodes.map(n => n.y ?? 0));

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;
    const scale = 0.85 * Math.min(this.width / rangeX, this.height / rangeY);
    const tx = this.width / 2 - scale * avgX;
    const ty = this.height / 2 - scale * avgY;

    this.svg
      .transition()
      .duration(700)
      .call(
        this.zoom.transform as any,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      );
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  private _drawCompoundBackgrounds(): void {
    const nodes = Array.from(this.nodeById.values());
    const bounds = this._compoundManager.computeGroupBounds(
      nodes,
      this._allEdges,
      40,
      this.styling.nodeSize! * 3.0,
    );
    this._childrenMap = this._compoundManager.computeChildrenMap(nodes, this._allEdges);
    this._backgroundGroup.selectAll('*').remove();
    for (const b of bounds) {
      const isDir = b.depth === 0;
      const fill   = isDir ? 'rgba(127,140,141,0.06)' : 'rgba(155,89,182,0.09)';
      const stroke = isDir ? 'rgba(127,140,141,0.30)' : 'rgba(155,89,182,0.35)';
      const dash   = isDir ? '8,4' : '4,2';
      const sw     = isDir ? 1.5 : 1.0;
      const grp = this._backgroundGroup.append('g').attr('class', `compound-group depth-${b.depth}`);
      grp.append('circle')
        .attr('cx', b.cx)
        .attr('cy', b.cy)
        .attr('r', b.radius)
        .attr('fill', fill)
        .attr('stroke', stroke)
        .attr('stroke-width', sw)
        .attr('stroke-dasharray', dash)
        .style('opacity', 0)
        .transition()
        .delay(300)
        .duration(500)
        .style('opacity', 1);
      grp.append('text')
        .attr('x', b.cx)
        .attr('y', b.cy - b.radius + 16)
        .attr('text-anchor', 'middle')
        .attr('font-size', isDir ? 11 : 9)
        .attr('fill', isDir ? 'rgba(127,140,141,0.70)' : 'rgba(155,89,182,0.70)')
        .style('pointer-events', 'none')
        .style('opacity', 0)
        .text(b.label)
        .transition()
        .delay(300)
        .duration(500)
        .style('opacity', 1);
    }
  }

  /**
   * Open the source location for a symbol node.
   * GitHub raw URLs are converted to github.com/blob/#L{line} in a new tab.
   * Non-URL file paths show a small in-page toast at the click position.
   */
  private _openSource(file: string, line: number, label: string, cx: number, cy: number): void {
    const rawMatch = file.match(
      /^https:\/\/raw\.githubusercontent\.com\/([^/]+\/[^/]+)\/([^/]+)\/(.+)$/
    );
    if (rawMatch) {
      window.open(
        `https://github.com/${rawMatch[1]}/blob/${rawMatch[2]}/${rawMatch[3]}#L${line}`,
        '_blank', 'noopener',
      );
    } else if (file.startsWith('http')) {
      window.open(file, '_blank', 'noopener');
    } else {
      // Local file — show a compact floating badge near the cursor
      const badge = document.createElement('div');
      badge.style.cssText = [
        'position:fixed',
        `left:${cx + 8}px`,
        `top:${cy - 28}px`,
        'z-index:9999',
        'background:#1a1a1a',
        'border:1px solid #00ff4140',
        'color:#00ff41',
        'padding:4px 8px',
        'font-size:11px',
        'font-family:monospace',
        'border-radius:4px',
        'pointer-events:none',
        'white-space:nowrap',
      ].join(';');
      badge.textContent = `${label}  ${file}:${line}`;
      document.body.appendChild(badge);
      setTimeout(() => badge.remove(), 3500);
    }
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

  private _nodePath(shape: string | undefined, s: number): string {
    switch (shape) {
      case 'square':
      case 'rectangle':
        return `M ${-s} ${-s} L ${s} ${-s} L ${s} ${s} L ${-s} ${s} Z`;
      case 'triangle': {
        const h = s * 1.5;
        return `M 0 ${-h} L ${s} ${h} L ${-s} ${h} Z`;
      }
      case 'diamond':
        return `M 0 ${-s} L ${s} 0 L 0 ${s} L ${-s} 0 Z`;
      case 'hexagon': {
        const a = s * 0.866;
        const b = s * 0.5;
        return `M 0 ${-s} L ${a} ${-b} L ${a} ${b} L 0 ${s} L ${-a} ${b} L ${-a} ${-b} Z`;
      }
      default:
        return `M ${s} 0 A ${s} ${s} 0 1 1 ${-s} 0 A ${s} ${s} 0 1 1 ${s} 0 Z`;
    }
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
    this.labelGroup
      .selectAll<SVGTextElement, unknown>(`text[data-node-id="${nodeId}"]`)
      .attr('x', x)
      .attr('y', y + size + 12);
  }
}
