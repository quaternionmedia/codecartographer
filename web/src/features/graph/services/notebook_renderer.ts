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
    styling?: GraphStylingOptions
  ): void {
    // Validate data format
    if (!this.canHandle(data)) {
      logger.warn('NotebookGraphRenderer: Data is GraphData JSON, not pre-rendered HTML');
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--c-warning, #ffa500);">
          <h3>⚠️ Notebook Renderer Unavailable</h3>
          <p>The Notebook renderer only works with pre-rendered HTML visualizations.</p>
          <p>Current data is in GraphData JSON format (from backend).</p>
          <p><strong>Please select D3 or Gravis renderer instead.</strong></p>
        </div>
      `;
      return;
    }

    logger.debug('NotebookGraphRenderer.render - rendering notebook outputs');

    // Convert data to array if single output
    let dataArray: NotebookOutput[];
    if (Array.isArray(data)) {
      dataArray = data as NotebookOutput[];
    } else if (typeof data === 'object' && data !== null && 'text/html' in data) {
      dataArray = [data as NotebookOutput];
    } else {
      logger.error('NotebookGraphRenderer: Unexpected data format');
      container.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--c-error, #ff0000);">
          <h3>Error: Invalid Data Format</h3>
          <p>Expected notebook output with 'text/html' field.</p>
        </div>
      `;
      return;
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

    const background = this.getThemeBackground(styling);

    // Create iframes for each HTML output
    htmlOutputs.forEach((output) => {
      const iframe = document.createElement('iframe');
      iframe.className = 'graph_content nbFrame';
      iframe.srcdoc = this.injectThemeStyles(output['text/html'] as string, styling);

      // Style iframe to fill container
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.style.border = 'none';
      iframe.style.backgroundColor = background;

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

  /**
   * Inject theme CSS variables and base styles into HTML.
   */
  private injectThemeStyles(html: string, styling?: GraphStylingOptions): string {
    const rootStyle = getComputedStyle(document.documentElement);
    const themeVars = [
      '--c-primary',
      '--c-secondary',
      '--c-accent',
      '--c-font',
      '--c-font-muted',
      '--f-root-font',
      '--f-heading-font'
    ];

    const cssVars = themeVars
      .map((name) => `${name}: ${rootStyle.getPropertyValue(name).trim()};`)
      .join(' ');

    const themeBackground = rootStyle.getPropertyValue('--c-primary').trim() || '#0a0a0a';
    const themeFont = rootStyle.getPropertyValue('--c-font').trim() || '#00ff41';
    const fallbackFont = rootStyle.getPropertyValue('--f-root-font').trim() || 'Consolas, Monaco, monospace';
    const background = this.getThemeBackground(styling);

    const styleBlock = `
<style>
:root { ${cssVars} }
html, body {
  margin: 0;
  height: 100%;
  background: ${background} !important;
  color: ${themeFont};
  font-family: ${fallbackFont};
}
body, .vis-network, .vis-network canvas, canvas, svg {
  background: ${background} !important;
}
div[id$="-main-div"],
div[id$="-left-div"],
div[id$="-left-inner-div"],
div[id$="-graph-div"] {
  height: 100% !important;
}
div[id$="-graph-div"] {
  resize: none !important;
}
div[id$="-main-div"],
div[id$="-left-div"],
div[id$="-right-div"],
div[id$="-left-inner-div"],
div[id$="-right-inner-div"],
div[id$="-graph-div"],
div[id$="-details-div"] {
  background: ${background} !important;
}
</style>`;

    const scriptBlock = `
<script>
(function () {
  function resizeGraph() {
    try {
      if (typeof ui !== 'undefined' && ui.composites && ui.composites.responsiveContainer && ui.composites.graph) {
        ui.composites.responsiveContainer.adaptToResize();
        ui.composites.graph.updateGraphDrawingArea();
      }
    } catch (err) {
      // Ignore errors from unknown notebook content.
    }
  }

  window.addEventListener('resize', resizeGraph);
  window.addEventListener('load', function () {
    setTimeout(resizeGraph, 0);
  });

  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(function () {
      resizeGraph();
    });
    ro.observe(document.body);
  }
})();
</script>`;

    const injection = `${styleBlock}${scriptBlock}`;

    if (html.includes('</body>')) {
      return html.replace('</body>', `${injection}</body>`);
    }

    if (html.includes('</head>')) {
      return html.replace('</head>', `${injection}</head>`);
    }

    if (html.includes('<body')) {
      return html.replace(/<body([^>]*)>/i, `<body$1>${injection}`);
    }

    return `${injection}${html}`;
  }

  private getThemeBackground(styling?: GraphStylingOptions): string {
    const rootStyle = getComputedStyle(document.documentElement);
    const themeBackground = rootStyle.getPropertyValue('--c-primary').trim() || '#0a0a0a';
    if (styling?.backgroundColor && styling.backgroundColor !== 'transparent') {
      return styling.backgroundColor;
    }
    return themeBackground;
  }
}
