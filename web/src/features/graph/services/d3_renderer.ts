/**
 * The D3 renderer, which is `StreamingGraphRenderer` handed a finished graph.
 *
 * **THERE IS ONE D3 CANVAS IN THIS APPLICATION.** There were two: this renderer
 * delegated to `graph_renderer.ts`, while every repository plot streamed through
 * `StreamingGraphRenderer`. They had separate node drawing, separate zoom and
 * drag, separate menus — a conformant radial menu on one and a bespoke one on
 * the other — and only one of them had a legend. A reader could not tell which
 * they were looking at, and neither could a test. ADR §7 collapses them onto the
 * streaming renderer, which is the one the real code-map paths already used.
 *
 * `mergeGraph` is what makes a streaming renderer take a complete graph: the
 * nodes arrive in one call instead of over an SSE connection, and the same
 * progressive rAF loop draws them. Nothing here re-implements drawing.
 *
 * The canvas is announced through `GraphSurface` so the menu and the key attach
 * to it, exactly as they do on a streamed plot. Without that this path would
 * render correctly and silently lack both.
 */

import { IGraphRenderer } from './base_renderer';
import { GraphData, GraphNode, GraphEdge } from './graph_types';
import { GraphSurface } from './graph_surface';
import { StreamingGraphRenderer } from './streaming_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

/**
 * gJGF keys nodes by id and carries their attributes under `metadata`; the
 * streaming path deals in flat node objects with an `id`. Both conventions are
 * real in this codebase, so both are accepted — guessing wrong renders an empty
 * graph and reports nothing, which is the worst available failure.
 */
function flattenNodes(nodes: unknown): GraphNode[] {
  if (Array.isArray(nodes)) return nodes as GraphNode[];
  if (!nodes || typeof nodes !== 'object') return [];
  return Object.entries(nodes as Record<string, Record<string, unknown>>).map(
    ([id, node]) => {
      const metadata = (node?.metadata as Record<string, unknown>) ?? node ?? {};
      return { ...metadata, ...node, id, metadata: undefined } as unknown as GraphNode;
    },
  );
}

export class D3GraphRenderer implements IGraphRenderer {
  readonly type = 'd3';
  readonly name = 'D3.js Force-Directed Graph';

  private renderer: StreamingGraphRenderer | null = null;

  render(container: HTMLElement, data: unknown, styling?: GraphStylingOptions): void {
    if (!this.canHandle(data)) {
      throw new Error('D3GraphRenderer: Invalid data format');
    }

    const graphData = data as GraphData;
    logger.debug('D3GraphRenderer.render - rendering with styling:', styling);

    this.cleanup();
    container.innerHTML = '';

    const renderer = new StreamingGraphRenderer(container, styling);
    const nodes = flattenNodes(graphData.graph?.nodes);
    const edges = (graphData.graph?.edges ?? []) as GraphEdge[];

    renderer.mergeGraph(nodes, edges);
    this.renderer = renderer;

    // Announced after the graph is in, so a subscriber reading the scene —
    // the legend counts what is on the canvas — sees the whole of it.
    GraphSurface.publish(renderer);
  }

  /**
   * Whether this is gJGF: `{ graph: { nodes, edges }, metadata }`.
   *
   * Unchanged by the merge deliberately. `findForData` asks every registered
   * renderer this question, so loosening it here would start claiming data that
   * belongs to another renderer.
   */
  canHandle(data: unknown): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }

    const obj = data as Record<string, unknown>;

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

  cleanup(): void {
    if (!this.renderer) return;
    if (GraphSurface.current() === this.renderer) GraphSurface.clear();
    this.renderer = null;
  }
}
