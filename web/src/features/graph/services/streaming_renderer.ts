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
  private _rafId: number | null = null;
  private _streamDone = false;
  private _batchSize = 1;           // updated when total is known via setTotal()
  private _totalNodes = 0;

  // Loading overlay shown before first data arrives
  private _loadingOverlay: HTMLDivElement | null = null;

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
      nodeOpacity: styling?.nodeOpacity ?? 1.0,
      nodeBorderWidth: styling?.nodeBorderWidth ?? 1.5,
      edgeWidth: styling?.edgeWidth ?? 1.0,
      edgeOpacity: styling?.edgeOpacity ?? 1.0,
      showNodeLabels: styling?.showNodeLabels ?? true,
      showEdgeLabels: styling?.showEdgeLabels ?? false,
      labelSize: styling?.labelSize ?? 10,
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
    this._scheduleLoop();
  }

  /** Called when the SSE stream is complete. Drains remaining queue then fits view. */
  finalize(): void {
    this._streamDone = true;
    this._scheduleLoop();
  }

  /**
   * Smoothly move already-rendered nodes to new positions. Used by the
   * dedicated C-parser stream (/c-parser/stream-github), which has to place
   * nodes in a placeholder grid as they arrive (the chosen layout algorithm
   * needs the complete edge set to mean anything, and edges aren't known
   * until the whole repo is parsed) — once the real graph is known, this
   * call transitions everything to its actual layout position. Call before
   * finalize() so the fit-to-view uses final positions, not the grid.
   */
  repositionAll(positions: Record<string, { x: number; y: number }>): void {
    for (const [nodeId, pos] of Object.entries(positions)) {
      const node = this.nodeById.get(nodeId);
      if (node) {
        node.x = pos.x;
        node.y = pos.y;
      }
    }

    this.nodeGroup.selectAll<SVGGElement, unknown>('.graph-node')
      .transition()
      .duration(600)
      .ease(d3.easeCubicInOut)
      .attr('transform', function (this: SVGGElement) {
        const nodeId = this.getAttribute('data-node-id');
        const pos = nodeId ? positions[nodeId] : undefined;
        return pos ? `translate(${pos.x},${pos.y}) scale(1)` : null;
      });

    for (const [nodeId, pos] of Object.entries(positions)) {
      const node = this.nodeById.get(nodeId);
      const size = node ? this.styling.nodeSize! * this._depthScale(node) : 0;
      this._updateEdgesForNode(nodeId, pos.x, pos.y);
      this._updateLabelForNode(nodeId, pos.x, pos.y, size);
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
      // Everything rendered, fit the view
      this._fitView();
    }
    // else: queues empty but stream not done yet — wait for more addNode calls
  }

  // ── Private: DOM rendering ─────────────────────────────────────────────────

  private _renderNode(node: GraphNode): void {
    const x = node.x ?? this.width / 2;
    const y = node.y ?? this.height / 2;
    const size = this.styling.nodeSize! * this._depthScale(node);

    const group = this.nodeGroup
      .append('g')
      .attr('class', 'graph-node')
      .attr('data-node-id', node.id)
      .attr('transform', `translate(${x},${y}) scale(0)`)
      .attr('opacity', 0);

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

    if (this.styling.showNodeLabels) {
      this.labelGroup
        .append('text')
        .attr('data-node-id', node.id)
        .attr('x', x)
        .attr('y', y + size + 12)
        .text(node.label || node.id)
        .attr('font-size', this.styling.labelSize!)
        .attr('text-anchor', 'middle')
        .attr('fill', this.styling.labelColor!)
        .attr('opacity', 0)
        .style('pointer-events', 'none')
        .transition()
        .delay(180)
        .duration(200)
        .attr('opacity', 1);
    }

    // Drag support (no simulation — positions are pre-computed)
    group.call(
      d3.drag<SVGGElement, unknown>()
        .on('drag', (event) => {
          node.x = event.x;
          node.y = event.y;
          group.attr('transform', `translate(${event.x},${event.y})`);
          this._updateEdgesForNode(node.id, event.x, event.y);
          this._updateLabelForNode(node.id, event.x, event.y, size);
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

  private _depthScale(node: GraphNode): number {
    const d = node.depth as number | undefined;
    if (d === 0) return 3.0;
    if (d === 1) return 1.8;
    if (d === 3) return 0.6;
    return 1.0;
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
