import m from 'mithril';
import { IGraphRenderer } from './base_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

/**
 * Data format for notebook/iframe rendering
 * Typically an array of notebook cell outputs with HTML content
 */
export interface NotebookOutput {
  'text/html'?: string;
  'text/plain'?: string;
  [key: string]: unknown;
}

/**
 * Notebook-based graph renderer
 * Renders pre-rendered HTML visualizations (from Jupyter notebooks, Gravis, etc.)
 * in iframes
 */
export class NotebookGraphRenderer implements IGraphRenderer {
  readonly type = 'notebook';
  readonly name = 'Notebook HTML Renderer';

  /**
   * Render notebook HTML output in iframes
   */
  render(
    container: HTMLElement,
    data: unknown,
    _styling?: GraphStylingOptions
  ): void {
    // Validate data format
    if (!this.canHandle(data)) {
      throw new Error('NotebookGraphRenderer: Invalid data format');
    }

    logger.debug('NotebookGraphRenderer.render - rendering notebook outputs');

    // Convert data to array if single output
    let dataArray: NotebookOutput[];
    if (Array.isArray(data)) {
      dataArray = data as NotebookOutput[];
    } else if (typeof data === 'object' && data !== null && 'text/html' in data) {
      dataArray = [data as NotebookOutput];
    } else {
      throw new Error('NotebookGraphRenderer: Data is not in expected format');
    }

    // Filter outputs that have HTML content
    const htmlOutputs = dataArray.filter(
      (output): output is NotebookOutput => {
        return (
          typeof output === 'object' &&
          output !== null &&
          'text/html' in output &&
          typeof output['text/html'] === 'string'
        );
      }
    );

    if (htmlOutputs.length === 0) {
      logger.warn('NotebookGraphRenderer: No HTML outputs found');
      container.innerHTML = '<div style="padding: 20px;">No visualization available</div>';
      return;
    }

    // Clear container
    container.innerHTML = '';

    // Create iframes for each HTML output
    htmlOutputs.forEach((output) => {
      const iframe = document.createElement('iframe');
      iframe.className = 'graph_content nbFrame';
      iframe.srcdoc = output['text/html'] as string;

      // Style iframe to fill container
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.style.border = 'none';

      container.appendChild(iframe);
    });

    logger.debug(`NotebookGraphRenderer: Created ${htmlOutputs.length} iframe(s)`);
  }

  /**
   * Check if data is in notebook output format
   */
  canHandle(data: unknown): boolean {
    if (!data) {
      return false;
    }

    // Handle array of outputs
    if (Array.isArray(data)) {
      // Must have at least one element with text/html
      return data.some(
        (item) =>
          typeof item === 'object' &&
          item !== null &&
          'text/html' in item
      );
    }

    // Handle single output object
    if (typeof data === 'object' && data !== null) {
      return 'text/html' in data;
    }

    return false;
  }

  /**
   * No cleanup needed for iframes
   */
  cleanup(): void {
    // No-op
  }
}
