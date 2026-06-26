import * as d3 from 'd3';
import m from 'mithril';
import { logger } from '../../../core/logger';
import { InteractionManager, InteractionManagerCallbacks } from './interaction_manager';
import { RadialMenu, getContextMenuItems, RadialMenuContext, RadialMenuCallbacks } from '../components/radial_menu';
import {
  graphExtensions,
  ExtensionContext,
  DragExtension,
  SelectionExtension,
  ZoomExtension,
  HighlightExtension,
  TooltipExtension,
  ColorExtension,
} from '../extensions';

export interface GraphNode {
  id: string;
  label?: string;
  color?: string;
  shape?: string;
  size?: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  // Unified schema fields (depth 0=dir, 1=file, 2=symbol, 3=sub-symbol)
  depth?: number;
  language?: string;    // 'python' | 'c' | 'unknown'
  kind?: string;        // 'directory' | 'file' | 'class' | 'function' | ...
  meta?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  label?: string;
  color?: string;
  [key: string]: unknown;
}

export interface GraphData {
  graph: {
    nodes: Record<string, GraphNode> | GraphNode[];  // gJGF uses object, but also support array
    edges: GraphEdge[];
    directed?: boolean;
  };
    metadata: {
      layout: string;
      type: string;
      nodeCount: number;
      edgeCount: number;
      palette_id: string;
      background_color?: string;
      edge_color?: string;
      node_label_color?: string;
      edge_label_color?: string;
      arrow_color?: string;
      node_border_color?: string;
      node_label_size?: number;
      edge_label_size?: number;
      [key: string]: unknown;
    };
  }

export interface GraphStylingOptions {
  // Layout Algorithm
  layout?: string;

  // Physics Simulation
  enablePhysics?: boolean;
  chargeStrength?: number;      // in pixels (repulsion force)
  linkDistance?: number;         // in pixels (target edge length)

  // Node Appearance
  nodeSize?: number;            // in pixels (radius)
  nodeOpacity?: number;         // 0.0 to 1.0
  nodeBorderWidth?: number;     // in pixels

  // Edge Appearance
  edgeWidth?: number;           // in pixels
  edgeOpacity?: number;         // 0.0 to 1.0

  // Label Appearance
  showNodeLabels?: boolean;
  showEdgeLabels?: boolean;
  labelSize?: number;           // in pixels (font size)
  labelColor?: string;          // hex color

  // Interactions
  interactionProfile?: string;  // Profile ID (default, cad, gaming, touch)
}

export class GraphRenderer {
  // Static state for radial menu and graph elements
  private static radialMenuContainer: HTMLElement | null = null;
  private static currentInteractionManager: InteractionManager | null = null;
  private static currentSvg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
  private static currentZoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
  private static currentSimulation: d3.Simulation<GraphNode, GraphEdge> | null = null;
  private static currentNodes: GraphNode[] = [];
  private static selectedNodes: Set<GraphNode> = new Set();
  private static onGraphChange: (() => void) | null = null;
  private static currentUpdatePositions: (() => void) | null = null;
  private static currentResizeObserver: ResizeObserver | null = null;

  // Extensions system
  private static dragExtension: DragExtension | null = null;
  private static selectionExtension: SelectionExtension | null = null;
  private static zoomExtension: ZoomExtension | null = null;
  private static highlightExtension: HighlightExtension | null = null;
  private static tooltipExtension: TooltipExtension | null = null;
  private static colorExtension: ColorExtension | null = null;

  /** Deselected-state border colour — amber for nodes whose source file had
   * parser diagnostics (see c_parser.py has_parse_warning), white otherwise. */
  private static nodeBorderColor(d: GraphNode): string {
    return d.has_parse_warning ? '#f5a623' : '#fff';
  }

  /** Deselected-state border dasharray — dashed for parse-warning nodes. */
  private static nodeBorderDash(d: GraphNode): string | null {
    return d.has_parse_warning ? '3,2' : null;
  }

  /**
   * Render graph data using D3.js with enhanced interactions
   */
  public static renderD3(
    container: HTMLElement,
    graphData: GraphData,
    stylingOptions?: GraphStylingOptions
  ): void {
    const { graph, metadata } = graphData;

    // Apply default styling options
    const styling: Required<GraphStylingOptions> = {
      layout: stylingOptions?.layout ?? 'spring_layout',
      enablePhysics: stylingOptions?.enablePhysics ?? true,
      chargeStrength: stylingOptions?.chargeStrength ?? -100,
      linkDistance: stylingOptions?.linkDistance ?? 55,
      nodeSize: stylingOptions?.nodeSize ?? 5,
      nodeOpacity: stylingOptions?.nodeOpacity ?? 1.0,
      nodeBorderWidth: stylingOptions?.nodeBorderWidth ?? 1.5,
      edgeWidth: stylingOptions?.edgeWidth ?? 1.0,
      edgeOpacity: stylingOptions?.edgeOpacity ?? 1.0,
      showNodeLabels: stylingOptions?.showNodeLabels ?? true,
      showEdgeLabels: stylingOptions?.showEdgeLabels ?? false,
      labelSize: stylingOptions?.labelSize ?? 10,
      labelColor: stylingOptions?.labelColor ?? '#333333',
      interactionProfile: stylingOptions?.interactionProfile ?? 'default',
    };

    logger.debug('GraphRenderer.renderD3 - rendering graph:', metadata);
    logger.debug('GraphRenderer.renderD3 - graph structure:', graph);
    logger.debug('GraphRenderer.renderD3 - styling options:', styling);

    if (this.currentResizeObserver) {
      this.currentResizeObserver.disconnect();
      this.currentResizeObserver = null;
    }

    // Clear existing content
    container.innerHTML = '';

    // Create legend module
    const legendContainer = document.createElement('div');
    legendContainer.className = 'graph-legend';
    legendContainer.innerHTML = `
      <div class="legend-header">
        <span class="legend-title">${metadata.layout || 'Graph'} - ${metadata.nodeCount || 0} nodes, ${metadata.edgeCount || 0} edges</span>
        <button class="legend-toggle" aria-label="Toggle legend">▼</button>
      </div>
      <div class="legend-content">
        <div class="legend-section">
          <h4>Node Shapes</h4>
          <div class="legend-items">
            <div class="legend-item"><svg width="16" height="16"><path d="M 8 2 L 14.928 6 L 14.928 10 L 8 14 L 1.072 10 L 1.072 6 Z" fill="var(--c-secondary)" stroke="#fff" stroke-width="1"></path></svg> Function</div>
            <div class="legend-item"><svg width="16" height="16"><rect x="4" y="4" width="8" height="8" fill="var(--c-accent)" stroke="#fff" stroke-width="1"></rect></svg> Class</div>
            <div class="legend-item"><svg width="16" height="16"><path d="M 8 4 L 12 8 L 8 12 L 4 8 Z" fill="#9b59b6" stroke="#fff" stroke-width="1"></path></svg> File/Module</div>
            <div class="legend-item"><svg width="16" height="16"><path d="M 8 4 L 12 12 L 4 12 Z" fill="#e74c3c" stroke="#fff" stroke-width="1"></path></svg> Import/Dependency</div>
            <div class="legend-item"><svg width="16" height="16"><circle cx="8" cy="8" r="4" fill="#95a5a6" stroke="#fff" stroke-width="1"></circle></svg> Variable</div>
            <div class="legend-item"><svg width="16" height="16"><path d="M 8 2 L 8 14 M 2 8 L 14 8" stroke="#f39c12" stroke-width="2" fill="none"></path></svg> Control Flow</div>
          </div>
        </div>
        <div class="legend-section">
          <h4>Interactions</h4>
          <div class="legend-items">
            <div class="legend-item">Click - Select node</div>
            <div class="legend-item">Drag - Move node</div>
            <div class="legend-item">Shift+Drag - Box select</div>
            <div class="legend-item">Right-click - Context menu</div>
            <div class="legend-item">Scroll - Zoom</div>
          </div>
        </div>
      </div>
    `;
    container.appendChild(legendContainer);

    // Add legend toggle functionality
    const legendHeader = legendContainer.querySelector('.legend-header') as HTMLDivElement;
    const legendToggle = legendContainer.querySelector('.legend-toggle') as HTMLButtonElement;
    const legendContent = legendContainer.querySelector('.legend-content') as HTMLDivElement;
    let legendExpanded = false;

    const toggleLegend = () => {
      legendExpanded = !legendExpanded;
      legendContent.style.display = legendExpanded ? 'block' : 'none';
      legendToggle.textContent = legendExpanded ? '▲' : '▼';
    };

    legendHeader.addEventListener('click', toggleLegend);

    // Start collapsed
    legendContent.style.display = 'none';

    // Convert gJGF nodes object to array if needed
    let nodes: GraphNode[];
    if (!graph || !graph.nodes) {
      logger.error('GraphRenderer.renderD3 - invalid graph structure:', graphData);
      container.innerHTML = '<div style="padding: 20px; color: red;">Error: Invalid graph data structure</div>';
      return;
    }

    if (Array.isArray(graph.nodes)) {
      nodes = graph.nodes;
    } else {
      // gJGF format: nodes is an object with node IDs as keys
      // Each node has attributes nested under 'metadata'
      nodes = Object.entries(graph.nodes).map(([id, nodeData]: [string, any]) => {
        // Flatten metadata into the node object
        const metadata = nodeData.metadata || {};
        return {
          id,
          ...metadata,
        };
      });
    }

    logger.debug('GraphRenderer.renderD3 - converted nodes:', nodes.length);

    // Get theme colors from CSS variables
    const getThemeColor = (variable: string, fallback: string): string => {
      return getComputedStyle(document.documentElement).getPropertyValue(variable).trim() || fallback;
    };

    const themeSecondary = getThemeColor('--c-secondary', '#00ff41');
    const themeAccent = getThemeColor('--c-accent', '#00d4ff');
    const themeFontMuted = getThemeColor('--c-font-muted', '#00aa2a');

    // Auto-assign shapes and colors based on node type/kind/depth if not already specified
    nodes.forEach(node => {
      const kind = node.kind as string | undefined;
      const type = node.type as string | undefined;
      const depth = node.depth as number | undefined;

      // ── Depth-first shape assignment (unified schema) ──────────────────────
      if (!node.shape) {
        if (depth === 0) {
          // Directory nodes → large diamond
          node.shape = 'diamond';
        } else if (depth === 1) {
          // File nodes → square
          node.shape = 'square';
        } else if (depth === 2 || depth === 3) {
          // Symbol / sub-symbol → kind-based
          if (kind === 'function' || kind === 'async_function' || type === 'function') {
            node.shape = 'hexagon';
          } else if (kind === 'class' || type === 'class') {
            node.shape = 'square';
          } else if (kind === 'struct' || kind === 'union') {
            node.shape = 'hexagon';
          } else if (kind === 'enum') {
            node.shape = 'diamond';
          } else if (kind === 'import' || kind === 'call' || type === 'dependency') {
            node.shape = 'triangle';
          } else if (kind === 'field' || kind === 'argument' || kind === 'enum_constant') {
            node.shape = 'circle';
          } else {
            node.shape = 'circle';
          }
        } else {
          // Legacy / unknown depth — fall back to kind-based
          if (kind === 'function' || kind === 'async_function' || type === 'function') {
            node.shape = 'hexagon';
          } else if (kind === 'class' || type === 'class') {
            node.shape = 'square';
          } else if (kind === 'module' || kind === 'file' || type === 'file') {
            node.shape = 'diamond';
          } else if (kind === 'import' || kind === 'call' || type === 'dependency') {
            node.shape = 'triangle';
          } else if (kind === 'variable' || kind === 'literal') {
            node.shape = 'circle';
          } else if (kind === 'control_flow' || kind === 'if' || kind === 'for' || kind === 'while') {
            node.shape = 'cross';
          } else {
            node.shape = 'circle';
          }
        }
      }

      // ── Depth-first color assignment (unified schema) ──────────────────────
      if (!node.color || node.color === 'steelblue') {
        if (depth === 0) {
          node.color = '#7f8c8d'; // Directory: muted grey
        } else if (depth === 1) {
          node.color = '#9b59b6'; // File: purple
        } else if (kind === 'function' || kind === 'async_function' || type === 'function') {
          node.color = themeSecondary;
        } else if (kind === 'class' || type === 'class') {
          node.color = themeAccent;
        } else if (kind === 'struct' || kind === 'union') {
          node.color = '#4a90d9'; // Blue
        } else if (kind === 'enum') {
          node.color = '#9b59b6'; // Purple
        } else if (kind === 'typedef') {
          node.color = '#1abc9c'; // Teal
        } else if (kind === 'module' || kind === 'file' || type === 'file') {
          node.color = '#9b59b6'; // Purple
        } else if (kind === 'import' || type === 'dependency') {
          node.color = '#e74c3c'; // Red
        } else if (kind === 'call') {
          node.color = themeFontMuted;
        } else if (kind === 'variable' || kind === 'literal' || kind === 'field') {
          node.color = '#95a5a6'; // Gray
        } else if (kind === 'control_flow' || kind === 'if' || kind === 'for' || kind === 'while') {
          node.color = '#f39c12'; // Orange
        } else {
          // Calculate color based on degree (connection count)
          const degree = (node.degree as number) || 0;
          const hue = (degree * 30) % 360;
          node.color = `hsl(${hue}, 70%, 60%)`;
        }
      }
    });

    // Large-graph mode: > 200 nodes switches to performance-optimised defaults
    const isLargeGraph = nodes.length > 200;
    if (isLargeGraph && !stylingOptions?.chargeStrength) styling.chargeStrength = -20;
    if (isLargeGraph && !stylingOptions?.linkDistance)   styling.linkDistance   = 30;

    // Set dimensions
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    // Create SVG with optional background color
    const svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])
      .style('background-color', styling.backgroundColor || 'transparent');

    // Create a group for zoom/pan
    const g = svg.append('g');

    // Create node lookup for edge linking
    const nodeById = new Map(nodes.map(n => [n.id, n]));

    // Convert edge source/target from string IDs to node objects
    const edges = graph.edges.map(e => ({
      ...e,
      source: typeof e.source === 'string' ? nodeById.get(e.source) || e.source : e.source,
      target: typeof e.target === 'string' ? nodeById.get(e.target) || e.target : e.target,
    }));

    logger.debug('GraphRenderer.renderD3 - processed edges:', edges.length);

    // Check if nodes have pre-computed positions
    const hasPositions = nodes.length > 0 && nodes[0].x !== undefined;

    let simulation: d3.Simulation<GraphNode, GraphEdge> | null = null;

    if (!hasPositions && styling.enablePhysics) {
      // No positions provided - use force simulation
      simulation = d3
        .forceSimulation(nodes as any)
        .force(
          'link',
          d3
            .forceLink(edges)
            .id((d: GraphNode) => d.id)
            .distance(styling.linkDistance)
        )
        .force('charge', d3.forceManyBody().strength(styling.chargeStrength))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(isLargeGraph ? 8 : 20));

      if (isLargeGraph) {
        // Settle in ~90 ticks instead of 300; more damping reduces thrashing
        simulation.alphaDecay(0.05).velocityDecay(0.6);
      }
    } else if (!hasPositions && !styling.enablePhysics) {
      // No positions and physics disabled - use simple circular layout
      nodes.forEach((n, i) => {
        const angle = (i / nodes.length) * 2 * Math.PI;
        const radius = Math.min(width, height) * 0.3;
        n.x = width / 2 + radius * Math.cos(angle);
        n.y = height / 2 + radius * Math.sin(angle);
      });
    }

    if (hasPositions) {
      // Center the pre-computed layout
      const centerX = width / 2;
      const centerY = height / 2;

      // Find current center
      const avgX = nodes.reduce((sum, n) => sum + (n.x || 0), 0) / nodes.length;
      const avgY = nodes.reduce((sum, n) => sum + (n.y || 0), 0) / nodes.length;

      // Offset to center
      const offsetX = centerX - avgX;
      const offsetY = centerY - avgY;

      nodes.forEach((n) => {
        n.x = (n.x || 0) + offsetX;
        n.y = (n.y || 0) + offsetY;
      });
    }

    // Helper to get stroke-dasharray for edge style
    const getEdgeDashArray = (style?: string): string | null => {
      switch (style) {
        case 'dashed': return '5,5';
        case 'dotted': return '2,2';
        default: return null;
      }
    };

    // Edge-kind visual mapping. `label` carries the semantic edge kind
    // (e.g. C parser: CALLS/FIELD_OF/POINTS_TO/ALIASES — see c_parser.py).
    // Unrecognised kinds (other languages, untyped edges) fall through to
    // the existing default styling untouched.
    const EDGE_KIND_COLOR: Record<string, string> = {
      CALLS:     '#e67e22',
      FIELD_OF:  '#555e6e',
      POINTS_TO: '#1abc9c',
      ALIASES:   '#1abc9c',
    };
    const EDGE_KIND_DASH: Record<string, string> = {
      POINTS_TO: '5,4',
      ALIASES:   '8,4',
    };

    // Draw edges with styling
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(edges)
      .enter()
      .append('line')
      .attr('stroke', (d) => (d.color as string) || EDGE_KIND_COLOR[d.label as string] || styling.edgeColor || '#999')
      .attr('stroke-opacity', styling.edgeOpacity * 0.6)
      .attr('stroke-width', (d) => {
        const weight = (d.weight as number) ?? 1;
        return d.label === 'CALLS' ? styling.edgeWidth * Math.min(3, 0.5 + weight * 0.4) : styling.edgeWidth;
      })
      .attr('stroke-dasharray', (d) => getEdgeDashArray(styling.edgeStyle) ?? EDGE_KIND_DASH[d.label as string] ?? null);

    // Store references for radial menu callbacks (except zoom - will be set later)
    this.currentSvg = svg;
    this.currentSimulation = simulation;
    this.currentNodes = nodes;
    this.selectedNodes.clear(); // Clear previous selections

    // State for node selection and interaction (use static reference)
    const selectedNodes = this.selectedNodes;

    // Forward declare updatePositions function (will be fully defined after nodes/edges/labels are created)
    let updatePositions: (() => void) | null = null;

    // Helper function to get SVG path for node shape.
    // `data` is passed for shapes that depend on node metadata (e.g. ngon reads meta.sides).
    const getNodePath = (shape: string | undefined, size: number, data?: GraphNode): string => {
      const s = size;

      switch (shape) {
        case 'square':
        case 'rectangle':
          return `M ${-s} ${-s} L ${s} ${-s} L ${s} ${s} L ${-s} ${s} Z`;

        case 'triangle':
          const h = s * 1.5;
          return `M 0 ${-h} L ${s} ${h} L ${-s} ${h} Z`;

        case 'diamond':
          return `M 0 ${-s} L ${s} 0 L 0 ${s} L ${-s} 0 Z`;

        case 'hexagon':
          const a = s * 0.866; // cos(30°)
          const b = s * 0.5;   // sin(30°)
          return `M 0 ${-s} L ${a} ${-b} L ${a} ${b} L 0 ${s} L ${-a} ${b} L ${-a} ${-b} Z`;

        case 'ngon': {
          // Generic N-gon. Sides come from meta.sides (set by the parser).
          // Falls back to meta.field_count, then 5.
          const meta = (data?.meta ?? {}) as Record<string, unknown>;
          const sides = Math.max(3, Math.min(Number(meta['sides'] ?? meta['field_count'] ?? 5), 12));
          let path = '';
          for (let i = 0; i < sides; i++) {
            const angle = (2 * Math.PI * i) / sides - Math.PI / 2;
            path += `${i === 0 ? 'M' : 'L'} ${s * Math.cos(angle)} ${s * Math.sin(angle)} `;
          }
          return path + 'Z';
        }

        case 'star':
          const outerR = s;
          const innerR = s * 0.4;
          let starPath = '';
          for (let i = 0; i < 10; i++) {
            const angle = (i * Math.PI) / 5 - Math.PI / 2;
            const r = i % 2 === 0 ? outerR : innerR;
            const x = r * Math.cos(angle);
            const y = r * Math.sin(angle);
            starPath += `${i === 0 ? 'M' : 'L'} ${x} ${y} `;
          }
          return starPath + 'Z';

        case 'cross':
          const w = s * 0.4;
          return `M ${-w} ${-s} L ${w} ${-s} L ${w} ${-w} L ${s} ${-w} L ${s} ${w} L ${w} ${w} L ${w} ${s} L ${-w} ${s} L ${-w} ${w} L ${-s} ${w} L ${-s} ${-w} L ${-w} ${-w} Z`;

        default:
          // Circle (using path for consistency)
          return `M ${s} 0 A ${s} ${s} 0 1 1 ${-s} 0 A ${s} ${s} 0 1 1 ${s} 0 Z`;
      }
    };

    // Draw nodes with varying shapes
    const nodeGroup = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'graph-node');

    // Add shape paths to nodes — size scales by depth when present
    const depthSizeMultiplier = (d: GraphNode): number => {
      const dep = d.depth as number | undefined;
      if (dep === 0) return 3.0;   // directory: 3× larger
      if (dep === 1) return 1.8;   // file: 1.8×
      if (dep === 3) return 0.6;   // sub-symbol: 0.6×
      return 1.0;                  // symbol (depth=2) and legacy: base size
    };

    nodeGroup
      .append('path')
      .attr('d', (d) => getNodePath(d.shape as string, styling.nodeSize * depthSizeMultiplier(d), d))
      .attr('fill', (d) => styling.nodeColorOverride || d.color || 'steelblue')
      .attr('fill-opacity', styling.nodeOpacity)
      // Parser diagnostics (e.g. C: missing header / unknown type in this
      // node's source file — see c_parser.py has_parse_warning) get a
      // dashed amber border instead of the default solid white.
      .attr('stroke', (d) => this.nodeBorderColor(d))
      .attr('stroke-width', styling.nodeBorderWidth)
      .attr('stroke-dasharray', (d) => this.nodeBorderDash(d));

    // Add interaction handlers to node groups
    const node = nodeGroup
      .on('click', (event: MouseEvent, d: GraphNode) => {
        event.stopPropagation();

        // Toggle selection
        const path = d3.select(event.currentTarget as SVGGElement).select('path');
        if (selectedNodes.has(d)) {
          selectedNodes.delete(d);
          path
            .attr('stroke', this.nodeBorderColor(d))
            .attr('stroke-width', styling.nodeBorderWidth)
            .attr('stroke-dasharray', this.nodeBorderDash(d));
        } else {
          if (!event.ctrlKey && !event.metaKey) {
            // Clear other selections if not multi-select
            selectedNodes.forEach((node) => {
              d3.selectAll('.graph-node')
                .filter((n: GraphNode) => n.id === node.id)
                .select('path')
                .attr('stroke', this.nodeBorderColor(node))
                .attr('stroke-width', styling.nodeBorderWidth)
                .attr('stroke-dasharray', this.nodeBorderDash(node));
            });
            selectedNodes.clear();
          }

          selectedNodes.add(d);
          path
            .attr('stroke', '#00ff41')
            .attr('stroke-width', styling.nodeBorderWidth * 2);
        }
      })
      .on('contextmenu', (event: MouseEvent, d: GraphNode) => {
        event.preventDefault();
        event.stopPropagation();
        this.showRadialMenu({
          type: 'node',
          target: d,
          position: { x: event.clientX, y: event.clientY },
        }, simulation, styling);
      })
      .call(
        d3
          .drag()
          .on('start', (event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) => {
            if (simulation) {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            }
          })
          .on('drag', (event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) => {
            // Update both regular and fixed positions for consistent behavior
            d.x = event.x;
            d.y = event.y;
            d.fx = event.x;
            d.fy = event.y;

            // Immediate visual update for the dragged node (don't wait for tick)
            d3.select(event.currentTarget as SVGGElement)
              .attr('transform', `translate(${event.x}, ${event.y})`);

            if (simulation) {
              // Simulation will handle edge updates via tick
            } else {
              // No simulation - update edges manually
              if (updatePositions) updatePositions();
            }
          })
          .on('end', (event: d3.D3DragEvent<SVGGElement, GraphNode, GraphNode>, d: GraphNode) => {
            if (simulation) {
              if (!event.active) simulation.alphaTarget(0);
              // Keep node pinned at dragged position
              d.fx = event.x;
              d.fy = event.y;
            }
          }) as any
      );

    // Add node labels (conditionally visible)
    const label = g
      .append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .text((d) => {
        const name = d.label || d.id;
        if (!isLargeGraph) return name;
        // Strip file-path prefix (e.g. 'hiredis::redisConnect' → 'redisConnect')
        const parts = name.split('::');
        return parts[parts.length - 1] || name;
      })
      .attr('font-size', styling.labelSize)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', styling.labelColor)
      // Large graphs: hide labels initially; LOD zoom handler reveals them when zoomed in
      .style('display', (styling.showNodeLabels && !isLargeGraph) ? 'block' : 'none')
      .style('pointer-events', 'none');

    // Add edge labels (if enabled)
    let edgeLabel: d3.Selection<SVGTextElement, GraphEdge, SVGGElement, unknown> | null = null;
    if (styling.showEdgeLabels) {
      edgeLabel = g
        .append('g')
        .attr('class', 'edge-labels')
        .selectAll('text')
        .data(edges)
        .enter()
        .append('text')
        .text((d) => d.label || '')
        .attr('font-size', styling.labelSize * 0.8)
        .attr('text-anchor', 'middle')
        .attr('fill', styling.labelColor)
        .attr('opacity', 0.7)
        .attr('dy', -2)
        .style('pointer-events', 'none');
    }

    // Add tooltips
    node.append('title').text((d) => d.label || d.id);

    // Define update positions function (now that all elements are created)
    updatePositions = () => {
      link
        .attr('x1', (d: GraphEdge) => (d.source as GraphNode).x || 0)
        .attr('y1', (d: GraphEdge) => (d.source as GraphNode).y || 0)
        .attr('x2', (d: GraphEdge) => (d.target as GraphNode).x || 0)
        .attr('y2', (d: GraphEdge) => (d.target as GraphNode).y || 0);

      // Update node group positions (translate transform)
      node.attr('transform', (d: GraphNode) => `translate(${d.x || 0}, ${d.y || 0})`);

      label.attr('x', (d: GraphNode) => d.x || 0).attr('y', (d: GraphNode) => d.y || 0);

      // Update edge label positions (midpoint of edge)
      if (edgeLabel) {
        edgeLabel
          .attr('x', (d: GraphEdge) => {
            const sourceX = (d.source as GraphNode).x || 0;
            const targetX = (d.target as GraphNode).x || 0;
            return (sourceX + targetX) / 2;
          })
          .attr('y', (d: GraphEdge) => {
            const sourceY = (d.source as GraphNode).y || 0;
            const targetY = (d.target as GraphNode).y || 0;
            return (sourceY + targetY) / 2;
          });
      }
    };

    // Store reference for radial menu callbacks
    this.currentUpdatePositions = updatePositions;

    if (simulation) {
      simulation.on('tick', updatePositions);
    } else {
      // Static layout - just update once
      updatePositions();
    }

    // Shift-drag box selection (must be set up BEFORE zoom)
    let selectionBox: d3.Selection<SVGRectElement, unknown, null, undefined> | null = null;
    let selectionStartPoint: { x: number; y: number } | null = null;
    let isShiftDragging = false;

    // Add zoom and pan with filter to allow shift-drag
    const labelThreshold = isLargeGraph ? 0.4 : 0.15;
    const zoom = d3
      .zoom()
      .scaleExtent([isLargeGraph ? 0.01 : 0.05, 10])
      .filter((event: any) => {
        // Prevent zoom from interfering with shift-drag box selection
        return !event.shiftKey && !event.button;
      })
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        // LOD: show labels only when zoomed in enough to read them
        const k = event.transform.k;
        label.style('display', k >= labelThreshold ? 'block' : 'none');
      });

    svg.call(zoom as any);

    // Store zoom reference for radial menu callbacks (now that it's created)
    this.currentZoom = zoom;

    // Auto-fit large graphs once the simulation first settles
    // (alphaDecay=0.05 → simulation.on('end') fires in ~1.5 s)
    if (simulation && isLargeGraph) {
      simulation.on('end', () => {
        const svgW = parseFloat(svg.attr('width'));
        const svgH = parseFloat(svg.attr('height'));
        const xs = nodes.map(n => n.x || 0);
        const ys = nodes.map(n => n.y || 0);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        const bw = maxX - minX || 1;
        const bh = maxY - minY || 1;
        const s = Math.max(0.01, Math.min(0.9 * Math.min(svgW / bw, svgH / bh), 10));
        const tx = svgW / 2 - s * ((minX + maxX) / 2);
        const ty = svgH / 2 - s * ((minY + maxY) / 2);
        svg.transition().duration(600).call(
          zoom.transform as any,
          d3.zoomIdentity.translate(tx, ty).scale(s)
        );
      });
    }

    // Set up shift-drag box selection handlers
    svg.on('mousedown.selection', (event: MouseEvent) => {
      // Only start box selection if shift is pressed and clicking on canvas (not a node)
      if (event.shiftKey && (event.target === svg.node() || (event.target as Element).tagName === 'svg')) {
        isShiftDragging = true;

        // Get mouse position in SVG coordinates (accounting for zoom/pan)
        const [mouseX, mouseY] = d3.pointer(event, g.node());
        selectionStartPoint = { x: mouseX, y: mouseY };

        // Create selection box
        selectionBox = g
          .append('rect')
          .attr('class', 'selection-box')
          .attr('x', mouseX)
          .attr('y', mouseY)
          .attr('width', 0)
          .attr('height', 0)
          .attr('fill', 'rgba(0, 255, 65, 0.1)')
          .attr('stroke', '#00ff41')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '4,4')
          .style('pointer-events', 'none'); // Don't interfere with other events

        event.preventDefault();
        event.stopPropagation();
      }
    });

    svg.on('mousemove.selection', (event: MouseEvent) => {
      if (isShiftDragging && selectionBox && selectionStartPoint) {
        // Get current mouse position
        const [mouseX, mouseY] = d3.pointer(event, g.node());

        // Calculate box dimensions
        const x = Math.min(selectionStartPoint.x, mouseX);
        const y = Math.min(selectionStartPoint.y, mouseY);
        const width = Math.abs(mouseX - selectionStartPoint.x);
        const height = Math.abs(mouseY - selectionStartPoint.y);

        // Update box
        selectionBox
          .attr('x', x)
          .attr('y', y)
          .attr('width', width)
          .attr('height', height);

        event.preventDefault();
      }
    });

    svg.on('mouseup.selection', (event: MouseEvent) => {
      if (isShiftDragging && selectionBox && selectionStartPoint) {
        // Get final mouse position
        const [mouseX, mouseY] = d3.pointer(event, g.node());

        // Calculate final box bounds
        const x1 = Math.min(selectionStartPoint.x, mouseX);
        const x2 = Math.max(selectionStartPoint.x, mouseX);
        const y1 = Math.min(selectionStartPoint.y, mouseY);
        const y2 = Math.max(selectionStartPoint.y, mouseY);

        // Find all nodes within the box
        const selectedNodesInBox: GraphNode[] = [];
        nodes.forEach((node) => {
          const nx = node.x || 0;
          const ny = node.y || 0;
          if (nx >= x1 && nx <= x2 && ny >= y1 && ny <= y2) {
            selectedNodesInBox.push(node);
          }
        });

        // Clear previous selection
        selectedNodes.clear();

        // Add all nodes in box to selection
        selectedNodesInBox.forEach((node) => selectedNodes.add(node));

        // Update visual highlighting
        d3.selectAll('.graph-node')
          .select('path')
          .attr('stroke', (d: GraphNode) => this.nodeBorderColor(d))
          .attr('stroke-width', styling.nodeBorderWidth)
          .attr('stroke-dasharray', (d: GraphNode) => this.nodeBorderDash(d));

        selectedNodesInBox.forEach((node) => {
          d3.selectAll('.graph-node')
            .filter((d: GraphNode) => d.id === node.id)
            .select('path')
            .attr('stroke', '#00ff41')
            .attr('stroke-width', styling.nodeBorderWidth * 2);
        });

        logger.debug('Box selected nodes:', selectedNodesInBox.length);

        // Remove selection box
        selectionBox.remove();
        selectionBox = null;
        selectionStartPoint = null;
        isShiftDragging = false;
      }
    });

    // Initialize extensions system
    this.initializeExtensions(container, svg, g, node, link, label, zoom, simulation, nodes, edges);

    // Canvas context menu (right-click on empty space)
    svg.on('contextmenu', (event: MouseEvent) => {
      event.preventDefault();
      const target = event.target as Element;
      if (target.tagName === 'svg' || target.closest('g')?.classList.contains('nodes') === false) {
        this.showRadialMenu({
          type: 'canvas',
          position: { x: event.clientX, y: event.clientY },
        }, simulation, styling);
      }
    });

    // Setup interaction manager for keyboard/touch
    const interactionCallbacks: InteractionManagerCallbacks = {
      onZoomChange: (scale) => {
        logger.debug('Zoom changed:', scale);
      },
      onFitToScreen: () => {
        // Calculate bounds of all nodes
        const bounds = {
          minX: Math.min(...nodes.map((n) => n.x || 0)),
          maxX: Math.max(...nodes.map((n) => n.x || 0)),
          minY: Math.min(...nodes.map((n) => n.y || 0)),
          maxY: Math.max(...nodes.map((n) => n.y || 0)),
        };

        const width = bounds.maxX - bounds.minX;
        const height = bounds.maxY - bounds.minY;
        const midX = (bounds.minX + bounds.maxX) / 2;
        const midY = (bounds.minY + bounds.maxY) / 2;

        const svgWidth = parseFloat(svg.attr('width'));
        const svgHeight = parseFloat(svg.attr('height'));

        const scale = 0.9 * Math.min(svgWidth / width, svgHeight / height);
        const translate = [svgWidth / 2 - scale * midX, svgHeight / 2 - scale * midY];

        svg.transition().duration(750).call(
          zoom.transform as any,
          d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
      },
      onTogglePhysics: () => {
        if (simulation) {
          if (simulation.alpha() > 0) {
            simulation.stop();
          } else {
            simulation.alpha(1).restart();
          }
        }
      },
      onRestartSimulation: () => {
        if (simulation) {
          simulation.alpha(1).restart();
        }
      },
      onContextMenu: (context) => {
        this.showRadialMenu(context, simulation, styling);
      },
      onNodeDeselect: () => {
        selectedNodes.clear();
        d3.selectAll('.graph-node').select('path')
          .attr('stroke', (d: GraphNode) => this.nodeBorderColor(d))
          .attr('stroke-width', styling.nodeBorderWidth)
          .attr('stroke-dasharray', (d: GraphNode) => this.nodeBorderDash(d));
      },
    };

    // Initialize interaction manager
    if (this.currentInteractionManager) {
      this.currentInteractionManager.destroy();
    }

    this.currentInteractionManager = new InteractionManager(interactionCallbacks, {
      profileId: styling.interactionProfile,
      panSpeed: 50,
      zoomSpeed: 0.1,
    });

    this.currentInteractionManager.initialize(container, svg, zoom);

    if (typeof ResizeObserver !== 'undefined') {
      let resizeRaf = 0;
      const handleResize = () => {
        if (resizeRaf) {
          cancelAnimationFrame(resizeRaf);
        }
        resizeRaf = requestAnimationFrame(() => {
          resizeRaf = 0;
          const nextWidth = container.clientWidth || width;
          const nextHeight = container.clientHeight || height;
          if (!nextWidth || !nextHeight) return;

          svg
            .attr('width', nextWidth)
            .attr('height', nextHeight)
            .attr('viewBox', [0, 0, nextWidth, nextHeight]);

          if (simulation) {
            simulation.force('center', d3.forceCenter(nextWidth / 2, nextHeight / 2));
            simulation.alpha(0.3).restart();
          }

          if (updatePositions) {
            updatePositions();
          }
        });
      };

      const resizeObserver = new ResizeObserver(handleResize);
      resizeObserver.observe(container);
      this.currentResizeObserver = resizeObserver;
    }

    logger.debug('GraphRenderer.renderD3 - render complete with interactive controls');
  }

  /**
   * Initialize extension system with current graph context
   */
  private static initializeExtensions(
    container: HTMLElement,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
    graphGroup: d3.Selection<SVGGElement, unknown, null, undefined>,
    nodes: d3.Selection<SVGCircleElement, GraphNode, SVGGElement, unknown>,
    edges: d3.Selection<SVGLineElement, GraphEdge, SVGGElement, unknown>,
    labels: d3.Selection<SVGTextElement, GraphNode, SVGGElement, unknown>,
    zoom: d3.ZoomBehavior<SVGSVGElement, unknown>,
    simulation: d3.Simulation<GraphNode, GraphEdge> | null,
    nodeData: GraphNode[],
    edgeData: GraphEdge[]
  ): void {
    // Create extension context
    const context: ExtensionContext<GraphNode, GraphEdge> = {
      svg,
      graphGroup,
      nodes,
      edges,
      labels,
      zoom,
      simulation: simulation || undefined,
      container,
      data: {
        nodes: nodeData,
        edges: edgeData,
      },
      selectedNodes: this.selectedNodes,
      onGraphChange: this.onGraphChange || undefined,
    };

    // Initialize drag extension (with multi-drag and grid snap)
    this.dragExtension = new DragExtension({
      multiDrag: true,
      gridSnap: false,
      showGhost: false,
    });
    this.dragExtension.initialize(context);
    this.dragExtension.apply();

    // Initialize selection extension (box and lasso select)
    this.selectionExtension = new SelectionExtension({
      enableBoxSelect: true,
      enableLassoSelect: true,
      onSelectionChange: (selected) => {
        logger.debug('Selection changed:', selected.size, 'nodes');
      },
    });
    this.selectionExtension.initialize(context);
    this.selectionExtension.apply();

    // Initialize zoom extension (with advanced zoom utilities)
    this.zoomExtension = new ZoomExtension({
      showZoomLevel: true,
      transitionDuration: 750,
      fitPadding: 0.1,
    });
    this.zoomExtension.initialize(context);
    this.zoomExtension.apply();

    // Initialize highlight extension (hover highlighting with neighbors)
    this.highlightExtension = new HighlightExtension({
      enableHover: true,
      highlightNeighbors: true,
      fadeOpacity: 0.15,
    });
    this.highlightExtension.initialize(context);
    this.highlightExtension.apply();

    // Initialize tooltip extension (rich tooltips with metadata)
    this.tooltipExtension = new TooltipExtension({
      enabled: true,
      showDelay: 300,
      hideDelay: 100,
      showMetadata: true,
      followCursor: false,
    });
    this.tooltipExtension.initialize(context);
    this.tooltipExtension.apply();

    // Initialize color extension (color schemes and utilities)
    this.colorExtension = new ColorExtension({
      scheme: 'category10',
      colorBy: 'type',
      autoApply: false, // Don't auto-apply, let user choose
    });
    this.colorExtension.initialize(context);
    this.colorExtension.apply();

    logger.debug('Extensions system initialized with 6 extensions');
  }

  /**
   * Show radial context menu
   */
  private static showRadialMenu(
    context: RadialMenuContext,
    simulation: d3.Simulation<GraphNode, GraphEdge> | null,
    styling: Required<GraphStylingOptions>
  ): void {
    // Remove existing menu if present
    if (this.radialMenuContainer) {
      document.body.removeChild(this.radialMenuContainer);
      this.radialMenuContainer = null;
    }

    // Create menu container
    this.radialMenuContainer = document.createElement('div');
    document.body.appendChild(this.radialMenuContainer);

    // Create callbacks for menu actions
    const callbacks: RadialMenuCallbacks = {
      onPinNode: (node: GraphNode) => {
        // Toggle pin/unpin
        if (node.fx !== undefined) {
          node.fx = null;
          node.fy = null;
        } else {
          node.fx = node.x;
          node.fy = node.y;
        }
        logger.debug('Node pin toggled', node);
      },
      onColorNode: (node: GraphNode, color: string) => {
        node.color = color;
        // Update visual
        d3.selectAll('.graph-node')
          .filter((n: GraphNode) => n.id === node.id)
          .attr('fill', color);
        logger.debug('Node color changed', node, color);
      },
      onHideNode: (node: GraphNode) => {
        d3.selectAll('.graph-node')
          .filter((n: GraphNode) => n.id === node.id)
          .attr('opacity', 0)
          .style('pointer-events', 'none');
        logger.debug('Node hidden', node);
      },
      onDeleteNode: (node: GraphNode) => {
        // Remove from selection
        this.selectedNodes.delete(node);
        // Hide from view (actual deletion would require re-render)
        d3.selectAll('.graph-node')
          .filter((n: GraphNode) => n.id === node.id)
          .remove();
        d3.selectAll('.menu-label')
          .filter((n: GraphNode) => n.id === node.id)
          .remove();
        logger.debug('Node deleted', node);
      },
      onFitToScreen: () => {
        if (!this.currentSvg || !this.currentZoom || this.currentNodes.length === 0) return;

        const bounds = {
          minX: Math.min(...this.currentNodes.map((n) => n.x || 0)),
          maxX: Math.max(...this.currentNodes.map((n) => n.x || 0)),
          minY: Math.min(...this.currentNodes.map((n) => n.y || 0)),
          maxY: Math.max(...this.currentNodes.map((n) => n.y || 0)),
        };

        const width = bounds.maxX - bounds.minX;
        const height = bounds.maxY - bounds.minY;
        const midX = (bounds.minX + bounds.maxX) / 2;
        const midY = (bounds.minY + bounds.maxY) / 2;

        const svgWidth = parseFloat(this.currentSvg.attr('width'));
        const svgHeight = parseFloat(this.currentSvg.attr('height'));

        const scale = 0.9 * Math.min(svgWidth / width, svgHeight / height);
        const translate = [svgWidth / 2 - scale * midX, svgHeight / 2 - scale * midY];

        this.currentSvg.transition().duration(750).call(
          this.currentZoom.transform as any,
          d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
        logger.debug('Fit to screen executed');
      },
      onZoomIn: () => {
        if (!this.currentSvg || !this.currentZoom) return;
        this.currentSvg.transition().duration(200).call(this.currentZoom.scaleBy as any, 1.3);
        logger.debug('Zoom in executed');
      },
      onZoomOut: () => {
        if (!this.currentSvg || !this.currentZoom) return;
        this.currentSvg.transition().duration(200).call(this.currentZoom.scaleBy as any, 0.7);
        logger.debug('Zoom out executed');
      },
      onTogglePhysics: () => {
        if (!this.currentSimulation) return;
        if (this.currentSimulation.alpha() > 0) {
          this.currentSimulation.stop();
          logger.debug('Physics stopped');
        } else {
          this.currentSimulation.alpha(1).restart();
          logger.debug('Physics restarted');
        }
      },
      onChangeLayout: (layout: string) => {
        logger.debug('Layout change requested:', layout);
        // This would require a full re-render with new layout
        // For now, just log it - actual implementation would need state management
        alert(`Layout change to ${layout} requires re-fetching from backend`);
      },
      onSelectNeighbors: (node: GraphNode) => {
        if (!graph || !graph.edges) return;

        // Find all neighbors of this node
        const neighbors = new Set<GraphNode>();
        graph.edges.forEach((edge: GraphEdge) => {
          const sourceNode = typeof edge.source === 'object' ? edge.source : this.currentNodes.find(n => n.id === edge.source);
          const targetNode = typeof edge.target === 'object' ? edge.target : this.currentNodes.find(n => n.id === edge.target);

          if (sourceNode && targetNode) {
            if (sourceNode.id === node.id) neighbors.add(targetNode);
            if (targetNode.id === node.id) neighbors.add(sourceNode);
          }
        });

        // Clear current selection and select neighbors
        this.selectedNodes.clear();
        neighbors.forEach(n => this.selectedNodes.add(n));

        // Update visual selection
        d3.selectAll('.graph-node').select('path')
          .attr('stroke', (d: GraphNode) => this.nodeBorderColor(d))
          .attr('stroke-width', styling.nodeBorderWidth)
          .attr('stroke-dasharray', (d: GraphNode) => this.nodeBorderDash(d));

        neighbors.forEach(n => {
          d3.selectAll('.graph-node')
            .filter((d: GraphNode) => d.id === n.id)
            .select('path')
            .attr('stroke', '#00ff41')
            .attr('stroke-width', styling.nodeBorderWidth * 2);
        });

        logger.debug('Selected neighbors:', neighbors.size);
      },
      onExpandNode: (node: GraphNode) => {
        logger.debug('Expand node (placeholder):', node);
        // Placeholder for future implementation
      },
      onCollapseNode: (node: GraphNode) => {
        logger.debug('Collapse node (placeholder):', node);
        // Placeholder for future implementation
      },
      onShowOnlyConnected: () => {
        // Hide all isolated nodes (nodes with no edges)
        const connectedNodeIds = new Set<string>();
        graph.edges.forEach((edge: GraphEdge) => {
          const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
          const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
          connectedNodeIds.add(sourceId);
          connectedNodeIds.add(targetId);
        });

        d3.selectAll('.graph-node').each(function(d: GraphNode) {
          if (!connectedNodeIds.has(d.id)) {
            d3.select(this).attr('opacity', 0).style('pointer-events', 'none');
          } else {
            d3.select(this).attr('opacity', 1).style('pointer-events', 'all');
          }
        });

        logger.debug('Showing only connected nodes');
      },
      onHideIsolated: () => {
        // Same as onShowOnlyConnected
        callbacks.onShowOnlyConnected?.();
      },
      onClusterByType: () => {
        logger.debug('Cluster by type (placeholder)');
        alert('Cluster by type requires re-layout from backend');
      },
      onArrangeByDegree: () => {
        logger.debug('Arrange by degree (placeholder)');
        alert('Arrange by degree requires re-layout from backend');
      },
      onArrangeHierarchical: () => {
        logger.debug('Arrange hierarchical (placeholder)');
        alert('Hierarchical layout requires re-layout from backend');
      },
      onSpreadNodes: () => {
        // Increase link distance if simulation exists
        if (this.currentSimulation) {
          const currentDistance = styling.linkDistance * 1.5;
          this.currentSimulation.force('link', d3.forceLink(edges).distance(currentDistance));
          this.currentSimulation.alpha(1).restart();
          logger.debug('Spread nodes - increased link distance');
        }
      },
      onCompactNodes: () => {
        // Decrease link distance if simulation exists
        if (this.currentSimulation) {
          const currentDistance = styling.linkDistance * 0.67;
          this.currentSimulation.force('link', d3.forceLink(edges).distance(currentDistance));
          this.currentSimulation.alpha(1).restart();
          logger.debug('Compact nodes - decreased link distance');
        }
      },
      onAlignNodes: (direction: 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom') => {
        if (this.selectedNodes.size === 0) return;

        const selectedArray = Array.from(this.selectedNodes);

        if (direction === 'left') {
          const minX = Math.min(...selectedArray.map(n => n.x || 0));
          selectedArray.forEach(n => { n.x = minX; n.fx = minX; });
        } else if (direction === 'right') {
          const maxX = Math.max(...selectedArray.map(n => n.x || 0));
          selectedArray.forEach(n => { n.x = maxX; n.fx = maxX; });
        } else if (direction === 'center') {
          const avgX = selectedArray.reduce((sum, n) => sum + (n.x || 0), 0) / selectedArray.length;
          selectedArray.forEach(n => { n.x = avgX; n.fx = avgX; });
        } else if (direction === 'top') {
          const minY = Math.min(...selectedArray.map(n => n.y || 0));
          selectedArray.forEach(n => { n.y = minY; n.fy = minY; });
        } else if (direction === 'bottom') {
          const maxY = Math.max(...selectedArray.map(n => n.y || 0));
          selectedArray.forEach(n => { n.y = maxY; n.fy = maxY; });
        } else if (direction === 'middle') {
          const avgY = selectedArray.reduce((sum, n) => sum + (n.y || 0), 0) / selectedArray.length;
          selectedArray.forEach(n => { n.y = avgY; n.fy = avgY; });
        }

        if (this.currentUpdatePositions) this.currentUpdatePositions();
        logger.debug('Aligned nodes:', direction);
      },
      onDistributeNodes: (direction: 'horizontal' | 'vertical') => {
        if (this.selectedNodes.size < 3) return;

        const selectedArray = Array.from(this.selectedNodes);

        if (direction === 'horizontal') {
          selectedArray.sort((a, b) => (a.x || 0) - (b.x || 0));
          const minX = selectedArray[0].x || 0;
          const maxX = selectedArray[selectedArray.length - 1].x || 0;
          const spacing = (maxX - minX) / (selectedArray.length - 1);
          selectedArray.forEach((n, i) => {
            n.x = minX + spacing * i;
            n.fx = n.x;
          });
        } else {
          selectedArray.sort((a, b) => (a.y || 0) - (b.y || 0));
          const minY = selectedArray[0].y || 0;
          const maxY = selectedArray[selectedArray.length - 1].y || 0;
          const spacing = (maxY - minY) / (selectedArray.length - 1);
          selectedArray.forEach((n, i) => {
            n.y = minY + spacing * i;
            n.fy = n.y;
          });
        }

        if (this.currentUpdatePositions) this.currentUpdatePositions();
        logger.debug('Distributed nodes:', direction);
      },
      onGroupSelection: (nodes: any[]) => {
        logger.debug('Group selection (placeholder):', nodes.length);
        // Placeholder for future grouping feature
      },
    };

    // Get context-appropriate menu items with callbacks
    const menuItems = getContextMenuItems(context, callbacks);

    // Mount radial menu using Mithril
    m.mount(this.radialMenuContainer, {
      view: () =>
        m('div', [
          // Overlay
          m('div.radial-menu-overlay', {
            onclick: () => this.closeRadialMenu(),
          }),
          // Menu
          m(RadialMenu, {
            items: menuItems,
            context,
            innerRadius: 60,
            outerRadius: 120,
            onClose: () => this.closeRadialMenu(),
          }),
        ]),
    });
  }

  /**
   * Close radial menu
   */
  private static closeRadialMenu(): void {
    if (this.radialMenuContainer) {
      m.mount(this.radialMenuContainer, null);
      document.body.removeChild(this.radialMenuContainer);
      this.radialMenuContainer = null;
    }
  }

  /**
   * Render using Three.js for 3D visualization
   * TODO: Implement Three.js renderer
   */
  public static renderThree(
    container: HTMLElement,
    graphData: GraphData
  ): void {
    logger.warn('Three.js renderer not yet implemented');
    container.innerHTML = '<div>Three.js rendering not yet implemented</div>';
  }

  /**
   * Render using vis.js
   * TODO: Implement vis.js renderer
   */
  public static renderVis(
    container: HTMLElement,
    graphData: GraphData
  ): void {
    logger.warn('vis.js renderer not yet implemented');
    container.innerHTML = '<div>vis.js rendering not yet implemented</div>';
  }

  /**
   * Get extension instances for advanced usage
   */
  public static getExtensions() {
    return {
      drag: this.dragExtension,
      selection: this.selectionExtension,
      zoom: this.zoomExtension,
      highlight: this.highlightExtension,
      tooltip: this.tooltipExtension,
      color: this.colorExtension,
    };
  }

  /**
   * Public API: Zoom to fit all nodes
   */
  public static zoomToFit(): void {
    if (this.zoomExtension && this.currentSvg) {
      const context = this.createExtensionContext();
      if (context) {
        this.zoomExtension.zoomToFit(context, true);
      }
    }
  }

  /**
   * Public API: Zoom to selected nodes
   */
  public static zoomToSelection(): void {
    if (this.zoomExtension && this.currentSvg) {
      const context = this.createExtensionContext();
      if (context) {
        this.zoomExtension.zoomToSelection(context, true);
      }
    }
  }

  /**
   * Public API: Select neighbors of currently selected nodes
   */
  public static selectNeighbors(): void {
    if (this.selectionExtension && this.currentSvg) {
      const context = this.createExtensionContext();
      if (context) {
        this.selectionExtension.selectNeighbors(context);
      }
    }
  }

  /**
   * Public API: Apply color scheme to nodes
   */
  public static applyColorScheme(scheme: string): void {
    if (this.colorExtension && this.currentSvg) {
      const context = this.createExtensionContext();
      if (context) {
        this.colorExtension.setColorScheme(scheme as any, context);
      }
    }
  }

  /**
   * Public API: Color nodes by degree (connectivity)
   */
  public static colorByDegree(): void {
    if (this.colorExtension && this.currentSvg) {
      const context = this.createExtensionContext();
      if (context) {
        this.colorExtension.colorByDegree(context);
      }
    }
  }

  /**
   * Create extension context from current state
   */
  private static createExtensionContext(): ExtensionContext<GraphNode, GraphEdge> | null {
    if (!this.currentSvg) return null;

    const graphGroup = this.currentSvg.select('g');
    const nodes = graphGroup.selectAll<SVGCircleElement, GraphNode>('.graph-node');
    const edges = graphGroup.selectAll<SVGLineElement, GraphEdge>('line');
    const labels = graphGroup.selectAll<SVGTextElement, GraphNode>('text');

    return {
      svg: this.currentSvg,
      graphGroup: graphGroup as any,
      nodes,
      edges,
      labels,
      zoom: this.currentZoom || undefined,
      simulation: this.currentSimulation || undefined,
      container: this.currentSvg.node()!.parentElement!,
      data: {
        nodes: this.currentNodes,
        edges: [], // Would need to store edges too
      },
      selectedNodes: this.selectedNodes,
      onGraphChange: this.onGraphChange || undefined,
    };
  }
}
