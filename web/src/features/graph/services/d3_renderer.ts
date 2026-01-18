import { IGraphRenderer } from './base_renderer';
import { GraphRenderer, GraphData } from './graph_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

/**
 * D3.js-based graph renderer
 * Renders interactive force-directed graphs using D3.js
 */
export class D3GraphRenderer implements IGraphRenderer {
  readonly type = 'd3';
  readonly name = 'D3.js Force-Directed Graph';

  /**
   * Render graph data using D3.js
   */
  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void {
    // Validate data format
    if (!this.canHandle(data)) {
      throw new Error('D3GraphRenderer: Invalid data format');
    }

    const graphData = data as GraphData;
    logger.debug('D3GraphRenderer.render - rendering with styling:', styling);

    // Delegate to existing D3 renderer implementation
    GraphRenderer.renderD3(container, graphData, styling);
  }

  /**
   * Check if data is in D3/gJGF format
   * D3 can handle any graph data in gJGF format
   */
  canHandle(data: unknown): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }

    const obj = data as Record<string, unknown>;

    // Check for gJGF format: { graph: { nodes, edges }, metadata }
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
   * Cleanup is handled by GraphRenderer static class
   */
  cleanup(): void {
    // No-op for now - GraphRenderer manages its own cleanup
  }
}
