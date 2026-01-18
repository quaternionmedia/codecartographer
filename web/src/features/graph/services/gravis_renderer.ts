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

    const graphData = data as GraphData;
    logger.debug('GravisGraphRenderer.render - rendering with vis-network');

    // Clear container
    container.innerHTML = '';

    // Convert data to vis-network format
    const { nodes, edges } = this.convertToVisFormat(graphData);

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

    // Add event listeners
    this.addEventListeners();

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
  private convertToVisFormat(graphData: GraphData): {
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

    // Convert nodes
    const nodes = Array.isArray(graphData.graph.nodes)
      ? graphData.graph.nodes
      : Object.values(graphData.graph.nodes);

    nodes.forEach((node: GraphNode) => {
      visNodes.push({
        id: node.id,
        label: node.label || node.id,
        title: node.label || node.id, // Tooltip
        color: node.color || undefined,
        shape: this.convertNodeShape(node.shape),
        size: node.size ? Math.sqrt(node.size) / 2 : undefined,
        x: node.x,
        y: node.y
      });
    });

    // Convert edges
    graphData.graph.edges.forEach((edge: GraphEdge, index: number) => {
      const sourceId = typeof edge.source === 'string' ? edge.source : edge.source.id;
      const targetId = typeof edge.target === 'string' ? edge.target : edge.target.id;

      visEdges.push({
        id: `edge-${index}`,
        from: sourceId,
        to: targetId,
        label: edge.label,
        color: edge.color ? { color: edge.color } : undefined,
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
   * Get vis-network options based on styling
   */
  private getNetworkOptions(graphData: GraphData, styling?: GraphStylingOptions): any {
    const nodeSize = styling?.nodeSize || 6;
    const edgeWidth = styling?.edgeWidth || 1.5;
    const labelColor = styling?.labelColor || '#00ff41';
    const enablePhysics = styling?.enablePhysics !== false;

    return {
      nodes: {
        shape: 'dot',
        size: nodeSize * 3,
        font: {
          size: styling?.labelSize || 11,
          color: labelColor,
          face: 'Consolas, Monaco, monospace'
        },
        borderWidth: styling?.nodeBorderWidth || 2,
        borderWidthSelected: (styling?.nodeBorderWidth || 2) * 1.5,
        color: {
          border: '#00ff41',
          background: '#00ff41',
          highlight: {
            border: '#00d4ff',
            background: '#00d4ff'
          },
          hover: {
            border: '#33ff66',
            background: '#33ff66'
          }
        }
      },
      edges: {
        width: edgeWidth,
        color: {
          color: '#666666',
          highlight: '#00ff41',
          hover: '#00ff41',
          opacity: styling?.edgeOpacity || 0.7
        },
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
          size: (styling?.labelSize || 11) - 2,
          color: labelColor,
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
    if (this.network) {
      this.network.destroy();
      this.network = null;
      logger.debug('GravisGraphRenderer: Cleaned up network instance');
    }
  }
}
