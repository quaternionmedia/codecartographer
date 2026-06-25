import * as d3 from 'd3';
import { IGraphRenderer } from './base_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

// ── C Semantic Graph types ────────────────────────────────────────────────────

export interface CSemanticNode {
  id: string;
  kind: 'struct' | 'union' | 'enum' | 'typedef' | 'function' | 'variable' | 'field' | 'enum_constant' | 'macro';
  name: string;
  file: string;
  line: number;
  qualifiers: string[];
  type_str: string;
  field_count?: number;
  member_count?: number;
  param_count?: number;
  is_definition?: boolean;
  // D3 simulation mutable fields
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface CSemanticEdge {
  src: string;
  dst: string;
  kind: 'CALLS' | 'FIELD_OF' | 'POINTS_TO' | 'ALIASES';
  weight: number;
  // D3 link resolved fields
  source?: CSemanticNode | string;
  target?: CSemanticNode | string;
}

export interface CSemanticGraph {
  nodes: CSemanticNode[];
  edges: CSemanticEdge[];
  meta: {
    files: string[];
    node_count: number;
    edge_count: number;
    kind_counts: Record<string, number>;
    edge_kinds: Record<string, number>;
  };
}

// ── Visual constants ──────────────────────────────────────────────────────────

const NODE_COLOR: Record<string, string> = {
  struct:       '#4a90d9',
  union:        '#6ab0e8',
  enum:         '#9b59b6',
  typedef:      '#1abc9c',
  function:     '#e67e22',
  variable:     '#95a5a6',
  field:        '#2c3e6e',
  enum_constant:'#6c3483',
  macro:        '#7f8c8d',
};

const EDGE_COLOR: Record<string, string> = {
  CALLS:    '#e67e22',
  FIELD_OF: '#555e6e',
  POINTS_TO:'#1abc9c',
  ALIASES:  '#1abc9c',
};

const EDGE_DASH: Record<string, string | null> = {
  CALLS:    null,
  FIELD_OF: null,
  POINTS_TO:'5,4',
  ALIASES:  '8,4',
};

function nodeRadius(node: CSemanticNode): number {
  switch (node.kind) {
    case 'struct':    return 16 + Math.min((node.field_count ?? 0) * 1.8, 18);
    case 'function':  return 14 + (node.param_count ?? 0) * 2;
    case 'enum':      return 15;
    case 'typedef':   return 10;
    case 'field':
    case 'enum_constant': return 6;
    default:          return 10;
  }
}

/** Build an SVG path string for kind-specific shapes. */
function nodePath(node: CSemanticNode): string {
  const r = nodeRadius(node);
  switch (node.kind) {
    case 'struct':
    case 'union': {
      // N-gon with sides = min(field_count, 10), min 5 sides
      const sides = Math.max(5, Math.min(node.field_count ?? 5, 10));
      return ngonPath(r, sides);
    }
    case 'function':
      return diamondPath(r);
    case 'field':
      return squarePath(r * 0.9);
    case 'enum_constant':
      return diamondPath(r * 0.9);
    default:
      // circle fallback
      return circlePath(r);
  }
}

function ngonPath(r: number, sides: number): string {
  const pts: string[] = [];
  for (let i = 0; i < sides; i++) {
    const angle = (2 * Math.PI * i) / sides - Math.PI / 2;
    pts.push(`${r * Math.cos(angle)},${r * Math.sin(angle)}`);
  }
  return `M${pts.join('L')}Z`;
}

function diamondPath(r: number): string {
  return `M0,${-r}L${r},0L0,${r}L${-r},0Z`;
}

function squarePath(r: number): string {
  return `M${-r},${-r}L${r},${-r}L${r},${r}L${-r},${r}Z`;
}

function circlePath(r: number): string {
  return (
    `M${r},0` +
    `A${r},${r},0,1,1,${-r},0` +
    `A${r},${r},0,1,1,${r},0Z`
  );
}

// ── Sidebar HTML builder ──────────────────────────────────────────────────────

function buildSidebarHTML(node: CSemanticNode, allEdges: CSemanticEdge[]): string {
  const incoming = allEdges.filter(e => (typeof e.target === 'object' ? (e.target as CSemanticNode).id : e.target) === node.id);
  const outgoing = allEdges.filter(e => (typeof e.source === 'object' ? (e.source as CSemanticNode).id : e.source) === node.id);

  const inList = incoming.map(e => {
    const src = typeof e.source === 'object' ? (e.source as CSemanticNode).name : e.src;
    return `<li><span class="edge-kind ${e.kind.toLowerCase()}">${e.kind}</span> ${escHtml(src)}</li>`;
  }).join('');

  const outList = outgoing.map(e => {
    const dst = typeof e.target === 'object' ? (e.target as CSemanticNode).name : e.dst;
    return `<li><span class="edge-kind ${e.kind.toLowerCase()}">${e.kind}</span> ${escHtml(dst)}</li>`;
  }).join('');

  const quals = node.qualifiers.length ? node.qualifiers.join(', ') : '—';
  const meta: string[] = [];
  if (node.field_count !== undefined)  meta.push(`<b>Fields:</b> ${node.field_count}`);
  if (node.member_count !== undefined) meta.push(`<b>Members:</b> ${node.member_count}`);
  if (node.param_count !== undefined)  meta.push(`<b>Params:</b> ${node.param_count}`);

  return `
    <div class="c-sidebar">
      <h3 class="c-sidebar-title">${escHtml(node.name)}</h3>
      <div class="c-sidebar-kind kind-${node.kind}">${node.kind}</div>
      <dl class="c-sidebar-meta">
        <dt>File</dt><dd>${escHtml(node.file)}</dd>
        <dt>Line</dt><dd>${node.line}</dd>
        <dt>Qualifiers</dt><dd>${escHtml(quals)}</dd>
        ${meta.map(m => `<dt></dt><dd>${m}</dd>`).join('')}
      </dl>
      ${incoming.length ? `<h4>Incoming (${incoming.length})</h4><ul class="c-sidebar-list">${inList}</ul>` : ''}
      ${outgoing.length ? `<h4>Outgoing (${outgoing.length})</h4><ul class="c-sidebar-list">${outList}</ul>` : ''}
    </div>
  `;
}

function escHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ── gJGF edge-kind → C semantic edge-kind ────────────────────────────────────

const GJGF_EDGE_KIND: Record<string, CSemanticEdge['kind']> = {
  field_of:  'FIELD_OF',
  calls:     'CALLS',
  type_of:   'POINTS_TO',
  aliases:   'ALIASES',
};

export class CSemanticRenderer implements IGraphRenderer {
  readonly type = 'c-semantic';
  readonly name = 'C Semantic Graph';

  private simulation: d3.Simulation<CSemanticNode, CSemanticEdge> | null = null;

  /**
   * CSemanticRenderer is an opt-in deep-dive view, not the default for C data.
   * Language-specific visual grammar is encoded by the parser into gJGF node
   * metadata (shape/color) and rendered by the active engine (D3, Gravis, etc.)
   * without needing a dedicated renderer per language.
   *
   * This renderer remains available for manual selection as a rich alternative
   * with its sidebar, polygon shapes, and live /c-parser/* endpoint support.
   * It is NOT registered in the main GraphRendererRegistry.
   */
  canHandle(_data: unknown): boolean {
    return false;
  }

  /** True when every depth-≥-2 node in a gJGF response has language 'c'. */
  private _isGjgfC(data: unknown): boolean {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    if (!('graph' in d)) return false;
    const graph = d.graph as Record<string, unknown>;
    if (!graph || typeof graph !== 'object') return false;
    const nodes = graph.nodes;
    if (!nodes || typeof nodes !== 'object' || Array.isArray(nodes)) return false;

    const entries = Object.values(nodes as Record<string, unknown>);
    // Filter to symbol nodes (depth >= 2)
    const symbolNodes = entries.filter((nd) => {
      const m = ((nd as Record<string, unknown>).metadata ?? {}) as Record<string, unknown>;
      const depth = m.depth;
      return typeof depth === 'number' && depth >= 2;
    });
    if (symbolNodes.length === 0) return false;
    // Auto-activate only when every symbol node is C (pure C parse)
    return symbolNodes.every((nd) => {
      const m = ((nd as Record<string, unknown>).metadata ?? {}) as Record<string, unknown>;
      return m.language === 'c';
    });
  }

  /**
   * Convert a gJGF response {graph: {nodes: {}, edges: []}} to CSemanticGraph.
   * Called by render() when _isGjgfC() is true.
   */
  private _fromGjgf(data: unknown): CSemanticGraph {
    const d = data as Record<string, unknown>;
    const gjgfGraph = d.graph as Record<string, unknown>;
    const gjgfNodes = gjgfGraph.nodes as Record<string, Record<string, unknown>>;
    const gjgfEdges = (gjgfGraph.edges ?? []) as Array<Record<string, unknown>>;

    const nodes: CSemanticNode[] = Object.entries(gjgfNodes)
      .filter(([, nd]) => {
        const m = (nd.metadata ?? {}) as Record<string, unknown>;
        return m.language === 'c';
      })
      .map(([id, nd]) => {
        const m = (nd.metadata ?? {}) as Record<string, unknown>;
        const meta = (m.meta ?? {}) as Record<string, unknown>;
        return {
          id,
          kind:       (m.kind ?? 'variable')   as CSemanticNode['kind'],
          name:       (nd.label ?? id)          as string,
          file:       (m.file  ?? '')           as string,
          line:       (m.line  ?? 0)            as number,
          qualifiers: (meta.qualifiers ?? [])   as string[],
          type_str:   (meta.type_str   ?? '')   as string,
          field_count:  meta.field_count  as number | undefined,
          member_count: meta.member_count as number | undefined,
          param_count:  meta.param_count  as number | undefined,
          is_definition: meta.is_definition as boolean | undefined,
        };
      });

    // Build a set of node IDs present in this renderer's filtered list
    const nodeIds = new Set(nodes.map(n => n.id));

    const edges: CSemanticEdge[] = gjgfEdges
      .filter(e => nodeIds.has(e.source as string) && nodeIds.has(e.target as string))
      .map(e => {
        const em = (e.metadata ?? {}) as Record<string, unknown>;
        const rawKind = (em.kind ?? '') as string;
        const kind: CSemanticEdge['kind'] = GJGF_EDGE_KIND[rawKind] ?? 'FIELD_OF';
        return {
          src:    e.source as string,
          dst:    e.target as string,
          kind,
          weight: (em.weight ?? 1.0) as number,
        };
      });

    const kindCounts: Record<string, number> = {};
    nodes.forEach(n => { kindCounts[n.kind] = (kindCounts[n.kind] ?? 0) + 1; });

    return {
      nodes,
      edges,
      meta: {
        files:      [...new Set(nodes.map(n => n.file))],
        node_count: nodes.length,
        edge_count: edges.length,
        kind_counts: kindCounts,
        edge_kinds:  {},
      },
    };
  }

  private _validateData(data: unknown): boolean {
    if (!data || typeof data !== 'object') return false;
    const d = data as Record<string, unknown>;
    return (
      Array.isArray(d['nodes']) &&
      Array.isArray(d['edges']) &&
      typeof d['meta'] === 'object' &&
      d['meta'] !== null &&
      'kind_counts' in (d['meta'] as object)
    );
  }

  render(container: HTMLElement, data: unknown, _styling?: GraphStylingOptions): void {
    // Convert gJGF to CSemanticGraph when needed
    const resolved = this._isGjgfC(data) ? this._fromGjgf(data) : data;
    if (!this._validateData(resolved)) {
      throw new Error('CSemanticRenderer: data must be a C semantic graph {nodes, edges, meta}');
    }
    const graph = resolved as CSemanticGraph;
    logger.debug('CSemanticRenderer.render - %d nodes, %d edges', graph.meta.node_count, graph.meta.edge_count);

    container.innerHTML = '';
    container.style.position = 'relative';
    container.style.overflow = 'hidden';

    const W = container.clientWidth  || 900;
    const H = container.clientHeight || 600;

    // ── sidebar panel ──
    const sidebar = document.createElement('div');
    sidebar.className = 'c-semantic-sidebar';
    sidebar.style.cssText = [
      'position:absolute;top:0;right:0;width:260px;height:100%;',
      'background:rgba(15,20,35,0.92);color:#cdd;overflow-y:auto;',
      'font-size:12px;font-family:monospace;padding:10px;box-sizing:border-box;',
      'border-left:1px solid #2a3a5e;z-index:10;',
    ].join('');
    sidebar.innerHTML = '<div style="color:#556;padding:20px 0;text-align:center">Click a node to inspect</div>';
    container.appendChild(sidebar);

    const graphW = W - 260;

    // ── SVG ──
    const svg = d3.select(container)
      .append('svg')
      .attr('width', graphW)
      .attr('height', H)
      .style('background', '#0a0f1e')
      .style('display', 'block');

    // Arrow markers
    const defs = svg.append('defs');
    Object.entries(EDGE_COLOR).forEach(([kind, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${kind}`)
        .attr('viewBox', '0 -4 8 8')
        .attr('refX', 18)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', color);
    });

    // Zoom
    const root = svg.append('g');
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => root.attr('transform', event.transform))
    );

    // ── Build D3-compatible link objects ──
    const nodeById = new Map(graph.nodes.map(n => [n.id, n]));
    const links: CSemanticEdge[] = graph.edges
      .filter(e => nodeById.has(e.src) && nodeById.has(e.dst))
      .map(e => ({ ...e, source: e.src, target: e.dst }));

    // ── Force simulation ──
    this.simulation = d3.forceSimulation<CSemanticNode>(graph.nodes)
      .force('link', d3.forceLink<CSemanticNode, CSemanticEdge>(links)
        .id(d => d.id)
        .distance(e => {
          const w = (e as CSemanticEdge).weight ?? 1;
          if (e.kind === 'FIELD_OF') return 60;
          if (e.kind === 'CALLS')    return 120 / w;
          return 100;
        })
        .strength(e => {
          if (e.kind === 'CALLS')    return 0.06;
          if (e.kind === 'FIELD_OF') return 0.1;
          return 0.03;
        })
      )
      .force('charge', d3.forceManyBody<CSemanticNode>()
        .strength(d => d.kind === 'struct' || d.kind === 'union' ? -24000 : -9000)
      )
      .force('center', d3.forceCenter(graphW / 2, H / 2))
      .force('collision', d3.forceCollide<CSemanticNode>().radius(d => nodeRadius(d) + 10))
      .alphaDecay(0.02)
      .velocityDecay(0.18);

    // ── Edges ──
    const edgeGroup = root.append('g').attr('class', 'edges');
    const edgeSel = edgeGroup.selectAll<SVGLineElement, CSemanticEdge>('line')
      .data(links)
      .join('line')
      .attr('stroke', e => EDGE_COLOR[e.kind] ?? '#555')
      .attr('stroke-width', e => e.weight * 1.2)
      .attr('stroke-dasharray', e => EDGE_DASH[e.kind] ?? null as unknown as string)
      .attr('stroke-opacity', e => e.kind === 'FIELD_OF' ? 0.35 : 0.7)
      .attr('marker-end', e => e.kind !== 'FIELD_OF' ? `url(#arrow-${e.kind})` : null as unknown as string);

    // ── Nodes ──
    const nodeGroup = root.append('g').attr('class', 'nodes');
    const nodeSel = nodeGroup.selectAll<SVGGElement, CSemanticNode>('g')
      .data(graph.nodes)
      .join('g')
      .attr('class', 'node')
      .style('cursor', 'pointer');

    // node shape
    nodeSel.append('path')
      .attr('d', d => nodePath(d))
      .attr('fill', d => NODE_COLOR[d.kind] ?? '#888')
      .attr('fill-opacity', 0.85)
      .attr('stroke', d => NODE_COLOR[d.kind] ?? '#888')
      .attr('stroke-width', d => d.kind === 'typedef' ? 1.5 : 0)
      .attr('stroke-dasharray', d => d.kind === 'typedef' ? '4,2' : null as unknown as string);

    // enum inner dots
    nodeSel.filter(d => d.kind === 'enum').each(function(d) {
      const g = d3.select(this);
      const count = Math.min(d.member_count ?? 3, 6);
      for (let i = 0; i < count; i++) {
        const angle = (2 * Math.PI * i) / count;
        const dotR = nodeRadius(d) * 0.38;
        g.append('circle')
          .attr('cx', dotR * Math.cos(angle))
          .attr('cy', dotR * Math.sin(angle))
          .attr('r', 2)
          .attr('fill', '#fff')
          .attr('opacity', 0.6);
      }
    });

    // label
    nodeSel.append('text')
      .text(d => d.name)
      .attr('dy', d => nodeRadius(d) + 11)
      .attr('text-anchor', 'middle')
      .attr('font-size', d => (d.kind === 'field' || d.kind === 'enum_constant') ? 8 : 10)
      .attr('fill', '#aac')
      .attr('pointer-events', 'none');

    // tooltip
    nodeSel
      .on('mouseenter', function(_event, d) {
        d3.select(this).select('path').attr('fill-opacity', 1).attr('filter', 'brightness(1.4)');
        const tip = document.createElement('div');
        tip.id = 'c-semantic-tip';
        tip.style.cssText = 'position:fixed;background:rgba(10,15,30,0.95);color:#cde;font:11px monospace;padding:6px 10px;border-radius:4px;pointer-events:none;z-index:999;border:1px solid #2a4a7e;white-space:nowrap;';
        tip.textContent = `${d.kind}: ${d.name}  (${d.file}:${d.line})`;
        document.body.appendChild(tip);
      })
      .on('mousemove', (event) => {
        const tip = document.getElementById('c-semantic-tip');
        if (tip) { tip.style.left = (event.clientX + 14) + 'px'; tip.style.top = (event.clientY + 8) + 'px'; }
      })
      .on('mouseleave', function() {
        d3.select(this).select('path').attr('fill-opacity', 0.85).attr('filter', null);
        document.getElementById('c-semantic-tip')?.remove();
      })
      .on('click', (_event, d) => {
        sidebar.innerHTML = buildSidebarHTML(d, links);
      });

    // drag
    nodeSel.call(
      d3.drag<SVGGElement, CSemanticNode>()
        .on('start', (event, d) => {
          if (!event.active && this.simulation) this.simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active && this.simulation) this.simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    );

    // ── Tick ──
    this.simulation.on('tick', () => {
      edgeSel
        .attr('x1', e => (e.source as CSemanticNode).x ?? 0)
        .attr('y1', e => (e.source as CSemanticNode).y ?? 0)
        .attr('x2', e => (e.target as CSemanticNode).x ?? 0)
        .attr('y2', e => (e.target as CSemanticNode).y ?? 0);
      nodeSel.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });
  }

  cleanup(): void {
    this.simulation?.stop();
    this.simulation = null;
    document.getElementById('c-semantic-tip')?.remove();
  }
}
