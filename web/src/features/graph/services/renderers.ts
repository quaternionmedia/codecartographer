/**
 * Graph Renderer System
 *
 * This module provides a pluggable architecture for different graph visualization libraries.
 * Each renderer implements the IGraphRenderer interface and can be selected at runtime.
 *
 * Available renderers:
 * - NotebookRenderer: Renders pre-rendered HTML from Jupyter notebooks (for demos)
 * - D3Renderer: Interactive D3.js force-directed graphs (for imported repos)
 * - GravisRenderer: Future gravis.js client-side rendering
 *
 * Usage:
 *   import { GraphRendererRegistry } from './renderers';
 *
 *   // Auto-detect renderer based on data
 *   const renderer = GraphRendererRegistry.findForData(data);
 *   renderer.render(container, data, styling);
 *
 *   // Or use specific renderer
 *   const d3Renderer = GraphRendererRegistry.get('d3');
 *   d3Renderer.render(container, data, styling);
 */

// Re-export base types and classes
export type { IGraphRenderer, RendererFactory } from './base_renderer';
export { GraphRendererRegistry } from './base_renderer';

// Re-export renderer implementations
export { D3GraphRenderer } from './d3_renderer';
export { NotebookGraphRenderer } from './notebook_renderer';
export { GravisGraphRenderer } from './gravis_renderer';

// Import for initialization
import { GraphRendererRegistry } from './base_renderer';
import { D3GraphRenderer } from './d3_renderer';
import { NotebookGraphRenderer } from './notebook_renderer';
import { GravisGraphRenderer } from './gravis_renderer';

/**
 * Initialize all renderers and register them
 * Called automatically when this module is imported
 */
function initializeRenderers(): void {
  // Register notebook renderer (for demos with pre-rendered HTML)
  GraphRendererRegistry.register('notebook', () => new NotebookGraphRenderer());

  // Register D3 renderer (for interactive graphs from imported repos)
  GraphRendererRegistry.register('d3', () => new D3GraphRenderer());

  // Register gravis renderer (future implementation)
  GraphRendererRegistry.register('gravis', () => new GravisGraphRenderer());

  // Set D3 as default for new graphs
  GraphRendererRegistry.setDefault('d3');
}

// Auto-initialize on module load
initializeRenderers();
