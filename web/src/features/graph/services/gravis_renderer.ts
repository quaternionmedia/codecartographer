import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { IGraphRenderer } from './base_renderer';
import { GraphData, GraphNode, GraphEdge } from './graph_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

/**
 * Gravis-style graph renderer using vis-network
 * Renders graphs using vis-network (same library used by Python gravis internally)
 */
export class GravisGraphRenderer implements IGraphRenderer {
  readonly type = 'gravis';
  readonly name = 'Gravis-style (vis-network) Renderer';

  private network: Network | null = null;
  private resizeObserver: ResizeObserver | null = null;

  /**
   * Render graph data using vis-network
   */
  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void {
    if (!this.canHandle(data)) {
      throw new Error('GravisGraphRenderer: Invalid data format');
    }

    this.cleanup();

    const graphData = data as GraphData;
    logger.debug('GravisGraphRenderer.render - rendering with vis-network');

    // Clear container
    container.innerHTML = '';

    // vis-network requires explicit pixel dimensions, not just CSS percentages
    // Get the parent dimensions and set them explicitly
    const parentRect = container.parentElement?.getBoundingClientRect();
    const width = parentRect?.width || container.clientWidth || 800;
    const height = parentRect?.height || container.clientHeight || 600;
    container.style.width = '100%';
    container.style.height = '100%';
    logger.debug(`GravisGraphRenderer: Container dimensions set to ${width}x${height}`);

    // Apply optional background color
    if (styling?.backgroundColor) {
      container.style.backgroundColor = styling.backgroundColor;
    }

    // Convert data to vis-network format
    const { nodes, edges } = this.convertToVisFormat(graphData, styling);

    // Create DataSets
    const nodesDataSet = new DataSet(nodes);
    const edgesDataSet = new DataSet(edges);

    // Configure network options
    const options = this.getNetworkOptions(graphData, styling);

    // Create network
    this.network = new Network(
      container,
      {
        nodes: nodesDataSet,
        edges: edgesDataSet
      },
      options
    );

    if (this.network) {
      this.network.setSize(`${width}px`, `${height}px`);
    }

    // Add event listeners
    this.addEventListeners();

    if (typeof ResizeObserver !== 'undefined') {
      let resizeRaf = 0;
      const resizeTarget = container.parentElement || container;
      const handleResize = () => {
        if (resizeRaf) {
          cancelAnimationFrame(resizeRaf);
        }
        resizeRaf = requestAnimationFrame(() => {
          resizeRaf = 0;
          if (!this.network) return;
          const rect = resizeTarget.getBoundingClientRect();
          const nextWidth = rect.width || container.clientWidth;
          const nextHeight = rect.height || container.clientHeight;
          if (!nextWidth || !nextHeight) return;
          this.network.setSize(`${nextWidth}px`, `${nextHeight}px`);
          this.network.redraw();
        });
      };

      this.resizeObserver = new ResizeObserver(handleResize);
      this.resizeObserver.observe(resizeTarget);
    }

    logger.debug('GravisGraphRenderer: Rendering complete');
  }

  /**
   * Check if data is in gJGF format
   * Gravis can handle any graph data in gJGF format
   */
  canHandle(data: unknown): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }

    const obj = data as Record<string, unknown>;

    // Check for gJGF format
    if ('graph' in obj && 'metadata' in obj) {
      const graph = obj.graph as Record<string, unknown>;

      return (
        typeof graph === 'object' &&
        'nodes' in graph &&
        'edges' in graph
      );
    }

    return false;
  }

  /**
   * Convert gJGF to vis-network format
   */
  private convertToVisFormat(graphData: GraphData, styling?: GraphStylingOptions): {
    nodes: Array<{
      id: string;
      label?: string;
      title?: string;
      color?: string;
      shape?: string;
      size?: number;
      x?: number;
      y?: number;
    }>;
    edges: Array<{
      id?: string;
      from: string;
      to: string;
      label?: string;
      color?: string;
      arrows?: string;
    }>;
  } {
    const visNodes: any[] = [];
    const visEdges: any[] = [];

    // Convert nodes - handle both array format and gJGF object format
    let nodes: GraphNode[];
    if (Array.isArray(graphData.graph.nodes)) {
      nodes = graphData.graph.nodes;
    } else {
      // gJGF format: nodes is an object with node IDs as keys
      // Each node has attributes nested under 'metadata'
      nodes = Object.entries(graphData.graph.nodes).map(([id, nodeData]: [string, any]) => {
        const metadata = nodeData.metadata || {};
        return {
          id,
          label: nodeData.label || id,
          ...metadata,
        } as GraphNode;
      });
    }

    logger.debug(`GravisGraphRenderer: Converting ${nodes.length} nodes to vis-network format`);

    const nodeSize = styling?.nodeSize;
    const nodeOpacity = styling?.nodeOpacity ?? 1;
    const nodeColorOverride = styling?.nodeColorOverride;

    nodes.forEach((node: GraphNode) => {
      const baseColor = nodeColorOverride || node.color;
      const colorWithOpacity = this.applyOpacity(baseColor, nodeOpacity);

      const visNode: Record<string, unknown> = {
        id: node.id,
        label: node.label || node.id,
        title: node.label || node.id, // Tooltip
        shape: this.convertNodeShape(node.shape),
        x: node.x,
        y: node.y
      };

      if (colorWithOpacity) {
        visNode.color = {
          background: colorWithOpacity,
          border: colorWithOpacity
        };
      }

      if (nodeSize !== undefined) {
        visNode.size = nodeSize * 3;
      } else if (node.size) {
        visNode.size = Math.sqrt(node.size) / 2;
      }

      visNodes.push(visNode);
    });

    // Convert edges
    graphData.graph.edges.forEach((edge: GraphEdge, index: number) => {
      const sourceId = typeof edge.source === 'string' ? edge.source : edge.source.id;
      const targetId = typeof edge.target === 'string' ? edge.target : edge.target.id;

      const edgeColor = edge.color;
      const edgeOpacity = styling?.edgeOpacity ?? 0.7;
      const colorWithOpacity = this.applyOpacity(edgeColor, edgeOpacity);

      visEdges.push({
        id: `edge-${index}`,
        from: sourceId,
        to: targetId,
        label: edge.label,
        color: colorWithOpacity ? { color: colorWithOpacity } : undefined,
        arrows: graphData.graph.directed !== false ? 'to' : undefined
      });
    });

    return { nodes: visNodes, edges: visEdges };
  }

  /**
   * Convert node shape from gJGF to vis-network format
   */
  private convertNodeShape(shape?: string): string {
    if (!shape) return 'dot';

    const mapping: Record<string, string> = {
      'circle': 'dot',
      'square': 'square',
      'triangle': 'triangle',
      'diamond': 'diamond',
      'hexagon': 'hexagon',
      'star': 'star'
    };

    return mapping[shape.toLowerCase()] || 'dot';
  }

  /**
   * Apply opacity to a color string when possible.
   */
  private applyOpacity(color: string | undefined, opacity: number): string | undefined {
    if (!color || opacity >= 1) {
      return color;
    }

    const hexMatch = color.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
    if (hexMatch) {
      const hex = hexMatch[1];
      const normalized = hex.length === 3
        ? hex.split('').map((c) => c + c).join('')
        : hex;
      const r = parseInt(normalized.slice(0, 2), 16);
      const g = parseInt(normalized.slice(2, 4), 16);
      const b = parseInt(normalized.slice(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }

    const rgbMatch = color.match(/^rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)$/i);
    if (rgbMatch) {
      const [, r, g, b] = rgbMatch;
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }

    return color;
  }

  /**
   * Map edge style to vis-network dashes configuration.
   */
  private getEdgeDashes(style?: GraphStylingOptions['edgeStyle']): boolean | number[] {
    switch (style) {
      case 'dashed':
        return [6, 6];
      case 'dotted':
        return [2, 4];
      default:
        return false;
    }
  }

  /**
   * Get vis-network options based on styling
   */
  private getNetworkOptions(graphData: GraphData, styling?: GraphStylingOptions): any {
    const nodeSize = styling?.nodeSize || 6;
    const edgeWidth = styling?.edgeWidth || 1.5;
    const labelColor = styling?.labelColor || '#00ff41';
    const enablePhysics = styling?.enablePhysics !== false;
    const showNodeLabels = styling?.showNodeLabels ?? true;
    const showEdgeLabels = styling?.showEdgeLabels ?? false;
    const edgeColor = styling?.edgeColor || '#666666';
    const edgeDashes = this.getEdgeDashes(styling?.edgeStyle);
    const nodeOpacity = styling?.nodeOpacity ?? 1;
    const defaultNodeColor = this.applyOpacity('#00ff41', nodeOpacity) || '#00ff41';
    const defaultNodeHighlight = this.applyOpacity('#00d4ff', nodeOpacity) || '#00d4ff';
    const defaultNodeHover = this.applyOpacity('#33ff66', nodeOpacity) || '#33ff66';

    return {
      nodes: {
        shape: 'dot',
        size: nodeSize * 3,
        font: {
          size: showNodeLabels ? (styling?.labelSize || 11) : 0,
          color: showNodeLabels ? labelColor : 'transparent',
          face: 'Consolas, Monaco, monospace'
        },
        borderWidth: styling?.nodeBorderWidth || 2,
        borderWidthSelected: (styling?.nodeBorderWidth || 2) * 1.5,
        color: {
          border: defaultNodeColor,
          background: defaultNodeColor,
          highlight: {
            border: defaultNodeHighlight,
            background: defaultNodeHighlight
          },
          hover: {
            border: defaultNodeHover,
            background: defaultNodeHover
          }
        }
      },
      edges: {
        width: edgeWidth,
        color: {
          color: edgeColor,
          highlight: '#00ff41',
          hover: '#00ff41',
          opacity: styling?.edgeOpacity || 0.7
        },
        dashes: edgeDashes,
        arrows: {
          to: {
            enabled: graphData.graph.directed !== false,
            scaleFactor: 0.5
          }
        },
        smooth: {
          type: 'continuous',
          roundness: 0.5
        },
        font: {
          size: showEdgeLabels ? (styling?.labelSize || 11) - 2 : 0,
          color: showEdgeLabels ? labelColor : 'transparent',
          face: 'Consolas, Monaco, monospace',
          align: 'middle'
        }
      },
      physics: {
        enabled: enablePhysics,
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: styling?.chargeStrength || -50,
          centralGravity: 0.01,
          springLength: styling?.linkDistance || 100,
          springConstant: 0.08,
          damping: 0.4,
          avoidOverlap: 0.5
        },
        stabilization: {
          enabled: true,
          iterations: 200,
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        zoomView: true,
        dragView: true,
        dragNodes: true,
        selectable: true,
        multiselect: true,
        selectConnectedEdges: false
      },
      layout: {
        improvedLayout: true,
        randomSeed: 42
      }
    };
  }

  /**
   * Add interaction event listeners
   */
  private addEventListeners(): void {
    if (!this.network) return;

    // Node click
    this.network.on('click', (params) => {
      if (params.nodes.length > 0) {
        logger.debug('Node clicked:', params.nodes);
      }
    });

    // Node double click
    this.network.on('doubleClick', (params) => {
      if (params.nodes.length > 0) {
        logger.debug('Node double-clicked:', params.nodes);
        // Could focus on node or show details
      }
    });

    // Edge click
    this.network.on('selectEdge', (params) => {
      logger.debug('Edge selected:', params.edges);
    });

    // Stabilization complete
    this.network.on('stabilizationIterationsDone', () => {
      logger.debug('GravisGraphRenderer: Layout stabilization complete');
      if (this.network) {
        this.network.setOptions({ physics: false });
      }
    });
  }

  /**
   * Cleanup vis-network instance
   */
  cleanup(): void {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    if (this.network) {
      this.network.destroy();
      this.network = null;
      logger.debug('GravisGraphRenderer: Cleaned up network instance');
    }
  }
}
