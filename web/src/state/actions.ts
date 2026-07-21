import m from 'mithril';
import { StateController } from '../state/state_controller';
import { PlotService } from '../services/plot_service';
import { RepoService } from '../features/repository';
import { GraphData } from '../features/graph';
import { GraphStylingOptions } from './types';
import { GraphRendererRegistry } from '../features/graph/services/renderers';
import { Directory, RawFile, RawFolder, RepoInfo } from '../components/models/source';
import { logger } from '../core/logger';

/**
 * Convert frontend layout format to backend format
 * Frontend: 'spring_layout', 'spectral_layout', etc.
 * Backend: 'Spring', 'Spectral', 'Kamada_Kawai', etc.
 */
function convertLayoutToBackend(frontendLayout: string): string {
  const mapping: Record<string, string> = {
    'spring_layout': 'Spring',
    'spectral_layout': 'Spectral',
    'kamada_kawai_layout': 'Kamada_Kawai',
    'circular_layout': 'Circular',
    'spiral_layout': 'Spiral',
    'random_layout': 'Random',
    'shell_layout': 'Shell',
    'sorted_square_layout': 'Sorted_Square',
  };
  return mapping[frontendLayout] || 'Spring';
}

/**
 * Plot Actions - handles all graph/visualization related operations
 * Extracts business logic from components into a dedicated module
 */
export class PlotActions {
  constructor(private stateController: StateController) {}

  /**
   * Process plot data from backend and update state
   * Auto-detects format and uses appropriate renderer
   */
  handlePlotData(data: unknown): void {
    logger.debug('PlotActions.handlePlotData - raw data:', data);

    if (!data) {
      logger.error('PlotActions.handlePlotData - data is null');
      return;
    }

    // Auto-detect and select appropriate renderer
    const renderer = GraphRendererRegistry.findForData(data);

    if (!renderer) {
      logger.error('PlotActions.handlePlotData - no suitable renderer found for data format');
      return;
    }

    logger.info(`PlotActions.handlePlotData - using renderer: ${renderer.name} (${renderer.type})`);

    // Store data and render based on type
    if (renderer.type === 'd3' || renderer.type === 'gravis') {
      // For graph-based renderers, store data in state for re-rendering
      this.renderGraphData(data as GraphData);
    } else {
      // For notebook/HTML renderers, render directly
      this.renderWithRenderer(renderer, data);
    }
  }

  /**
   * Render data using a specific renderer (for notebook/HTML renderers)
   */
  private renderWithRenderer(renderer: ReturnType<typeof GraphRendererRegistry.findForData>, data: unknown): void {
    if (!renderer) return;

    // Create container element
    const container = m('div.graph_content.graphRenderer', {
      oncreate: (vnode: m.VnodeDOM) => {
        const element = vnode.dom as HTMLElement;
        element.style.height = '100%';
        element.style.width = '100%';

        try {
          renderer.render(element, data);
        } catch (error) {
          logger.error('Error rendering with renderer:', error);
          element.innerHTML = '<div style="padding: 20px; color: red;">Error rendering visualization. Check console for details.</div>';
        }
      }
    });

    this.stateController.updatePlotFrame([container]);
  }

  /**
   * Render graph data using client-side D3 renderer
   */
  private renderGraphData(graphData: GraphData): void {
    logger.info('PlotActions.renderGraphData - rendering client-side:', graphData.metadata);

    // Store graph data in state so we can re-render when styling changes
    this.stateController.update({ graphData });

    // Create the graph vnode
    this.createGraphVnode();
  }

  /**
   * Create vnode for the system renderer (PAM Auth Monitor).
   * Does not require graph data — the renderer has its own built-in demo.
   */
  public createSystemVnode(): void {
    const styling     = this.stateController.state.graphStyling;
    const httpBase    = this.stateController.api.base;
    const wsBase      = httpBase.replace(/^http/, 'ws');
    const systemStyling = {
      ...styling,
      systemId:      styling.systemId ?? 'pam',
      systemWsBase:  wsBase,
      // Legacy fields kept for backwards compatibility
      pamHttpBase:   `${httpBase}/pam`,
      pamWsUrl:      `${wsBase}/pam/ws/live`,
    };

    const renderer = GraphRendererRegistry.get('system');
    const container = m('div.graph_content.graphRenderer', {
      key: `system-${Date.now()}`,
      oncreate: (vnode: m.VnodeDOM) => {
        const element = vnode.dom as HTMLElement;
        element.style.height = '100%';
        element.style.width  = '100%';
        renderer.render(element, null, systemStyling);
      },
    });
    this.stateController.updatePlotFrame([container]);
  }

  /**
   * Create graph vnode from stored graph data
   * This can be called when graph data changes OR when styling changes
   */
  public createGraphVnode(): void {
    // System renderer has its own built-in demo — no graph data required
    const selectedRenderer = this.stateController.state.selectedRenderer;
    if (selectedRenderer === 'system') {
      this.createSystemVnode();
      return;
    }

    const graphData = this.stateController.state.graphData;
    if (!graphData) {
      logger.warn('createGraphVnode called but no graph data in state');
      return;
    }

    // Special handling for notebook renderer - needs async HTML conversion
    if (selectedRenderer === 'notebook') {
      this.createNotebookVnode(graphData);
      return;
    }

    // Render function that can be called on create and update
    const renderGraph = (element: HTMLElement) => {
      // Get fresh styling options from state
      const stylingOptions = this.stateController.state.graphStyling;
      console.log('[VISUAL] renderGraph called with styling:', JSON.stringify(stylingOptions));
      logger.debug('PlotActions.createGraphVnode - rendering with styling:', stylingOptions);

      // Set minimum height if not set by CSS
      if (!element.style.height) {
        element.style.height = '100%';
        element.style.width = '100%';
      }

      // Use renderer registry to get appropriate renderer
      try {
        // Priority 1: Use user-selected renderer from state
        let renderer;

        if (selectedRenderer) {
          try {
            renderer = GraphRendererRegistry.get(selectedRenderer);
            logger.debug(`Using user-selected renderer: ${renderer.name} (${selectedRenderer})`);
          } catch (error) {
            logger.warn(`Selected renderer '${selectedRenderer}' not found, falling back...`);
          }
        }

        // Priority 2: Try to get renderer by type from metadata
        if (!renderer && graphData.metadata?.type) {
          try {
            renderer = GraphRendererRegistry.get(graphData.metadata.type);
            logger.debug(`Using metadata renderer type: ${graphData.metadata.type}`);
          } catch {
            logger.warn(`Renderer type '${graphData.metadata.type}' not found, auto-detecting...`);
          }
        }

        // Priority 3: Fall back to auto-detection
        if (!renderer) {
          renderer = GraphRendererRegistry.findForData(graphData);
          logger.debug(`Auto-detected renderer: ${renderer?.name}`);
        }

        // Priority 4: Final fallback to default (D3)
        if (!renderer) {
          logger.warn('No suitable renderer found, using default (D3)');
          renderer = GraphRendererRegistry.getDefault();
        }

        logger.info(`Rendering with: ${renderer.name} (${renderer.type})`);
        renderer.render(element, graphData, stylingOptions);
      } catch (error) {
        logger.error('Error rendering graph:', error);
        element.innerHTML = '<div style="padding: 20px; color: red;">Error rendering graph. Check console for details.</div>';
      }
    };

    // Create container element for rendering
    // Use renderer + layout + timestamp as key to force re-render when they change
    // Timestamp ensures Mithril always sees a new key and re-creates the element
    const renderKey = `${this.stateController.state.selectedRenderer}-${this.stateController.state.graphStyling.layout}-${Date.now()}`;

    const container = m('div.graph_content.graphRenderer', {
      key: renderKey,
      oncreate: (vnode: m.VnodeDOM) => {
        renderGraph(vnode.dom as HTMLElement);
      }
    });

    this.stateController.updatePlotFrame([container]);
  }

  /**
   * Create vnode for notebook renderer by converting GraphData to HTML via backend
   */
    private createNotebookVnode(graphData: GraphData): void {
      const stylingOptions = this.stateController.state.graphStyling;
      const layout = convertLayoutToBackend(stylingOptions.layout);
      const themedGraphData = this.applyThemeToGraphData(graphData, stylingOptions);

    // Show loading state while fetching HTML
    const loadingContainer = m('div.graph_content.graphRenderer', {
      key: `notebook-loading-${Date.now()}`,
    }, m('div', { style: 'padding: 40px; text-align: center; color: var(--c-text, #ccc);' }, [
      m('p', '⏳ Converting graph to HTML...'),
      m('p', { style: 'font-size: 0.9em; opacity: 0.7;' }, 'This may take a moment for large graphs.'),
    ]));
    this.stateController.updatePlotFrame([loadingContainer]);

    // Fetch HTML from backend
      PlotService.renderToHtml(this.stateController.api.plotter, themedGraphData, layout)
        .then((htmlData) => {
        if (!htmlData) {
          logger.error('Failed to convert graph to HTML');
          const errorContainer = m('div.graph_content.graphRenderer', {
            key: `notebook-error-${Date.now()}`,
          }, m('div', { style: 'padding: 40px; text-align: center; color: var(--c-error, #ff6b6b);' }, [
            m('h3', '❌ Failed to render'),
            m('p', 'Could not convert graph data to HTML.'),
            m('p', 'Try selecting D3 or Gravis renderer instead.'),
          ]));
          this.stateController.updatePlotFrame([errorContainer]);
          return;
        }

        // Get notebook renderer and render the HTML
          const renderer = GraphRendererRegistry.get('notebook');

        const container = m('div.graph_content.graphRenderer', {
          key: `notebook-${Date.now()}`,
          oncreate: (vnode: m.VnodeDOM) => {
            const element = vnode.dom as HTMLElement;
            element.style.height = '100%';
            element.style.width = '100%';
            renderer.render(element, htmlData, stylingOptions);
          }
        });
        this.stateController.updatePlotFrame([container]);
        m.redraw();
      })
      .catch((error) => {
        logger.error('Error converting graph to HTML:', error);
        const errorContainer = m('div.graph_content.graphRenderer', {
          key: `notebook-error-${Date.now()}`,
        }, m('div', { style: 'padding: 40px; text-align: center; color: var(--c-error, #ff6b6b);' }, [
          m('h3', '❌ Error'),
          m('p', 'An error occurred while rendering.'),
          m('p', { style: 'font-size: 0.9em;' }, String(error)),
        ]));
        this.stateController.updatePlotFrame([errorContainer]);
        });
    }

    private applyThemeToGraphData(
      graphData: GraphData,
      styling: GraphStylingOptions
    ): GraphData {
      const themed = this.cloneGraphData(graphData);
      const palette = this.getThemePalette(styling);
      const nodeColorOverride = styling.nodeColorOverride;
      const defaultLabelColor = '#00ff41';
      const defaultEdgeColor = '#666666';
      const normalizeColor = (value?: string): string => (value || '').trim().toLowerCase();
      const resolveThemeColor = (value: string | undefined, fallback: string, defaultValue?: string): string => {
        if (!value) return fallback;
        if (defaultValue && normalizeColor(value) === normalizeColor(defaultValue)) {
          return fallback;
        }
        return value;
      };
      const labelColor = resolveThemeColor(styling.labelColor, palette.font, defaultLabelColor);
      const edgeColor = resolveThemeColor(styling.edgeColor, palette.muted, defaultEdgeColor);

      const resolveNodeColor = (kind?: string, type?: string): string => {
        if (nodeColorOverride) return nodeColorOverride;

        const combined = `${kind || ''} ${type || ''}`.toLowerCase();
        if (combined.includes('function')) return palette.secondary;
        if (combined.includes('class')) return palette.accent;
        if (combined.includes('module') || combined.includes('file')) return palette.accent;
        if (combined.includes('import') || combined.includes('dependency')) return palette.error;
        if (combined.includes('call')) return palette.muted;
        if (combined.includes('variable') || combined.includes('literal')) return palette.disabled;
        if (combined.includes('control') || combined.includes('if') || combined.includes('for') || combined.includes('while') || combined.includes('try') || combined.includes('loop')) {
          return palette.warning;
        }
        return palette.secondary;
      };

      if (Array.isArray(themed.graph.nodes)) {
        themed.graph.nodes.forEach((node) => {
          const metadata = (node as Record<string, unknown>).metadata as Record<string, unknown> | undefined;
          const kind = (metadata?.kind as string | undefined) || (node as Record<string, unknown>).kind as string | undefined;
          const type = (metadata?.type as string | undefined) || (node as Record<string, unknown>).type as string | undefined;
          const color = resolveNodeColor(kind, type);
          (node as Record<string, unknown>).color = color;
          if (metadata) {
            metadata.color = color;
          }
        });
      } else {
        Object.values(themed.graph.nodes).forEach((nodeData) => {
          if (!nodeData || typeof nodeData !== 'object') return;
          const record = nodeData as Record<string, unknown>;
          const metadata = (record.metadata as Record<string, unknown>) || {};
          record.metadata = metadata;
          const kind = (metadata.kind as string | undefined) || (record.kind as string | undefined);
          const type = (metadata.type as string | undefined) || (record.type as string | undefined);
          const color = resolveNodeColor(kind, type);
          record.color = color;
          metadata.color = color;
        });
      }

      themed.graph.edges.forEach((edge) => {
        if (edge && typeof edge === 'object') {
          (edge as Record<string, unknown>).color = edgeColor;
        }
      });

      themed.metadata.background_color = palette.background;
      themed.metadata.edge_color = edgeColor;
      themed.metadata.node_label_color = labelColor;
      themed.metadata.edge_label_color = labelColor;
      themed.metadata.arrow_color = edgeColor;

      return themed;
    }

    private getThemePalette(styling?: GraphStylingOptions): {
      secondary: string;
      accent: string;
      muted: string;
      warning: string;
      error: string;
      disabled: string;
      background: string;
      font: string;
    } {
      const rootStyles = getComputedStyle(document.documentElement);
      const themeBackground = rootStyles.getPropertyValue('--c-primary').trim() || '#0a0a0a';
      return {
        secondary: rootStyles.getPropertyValue('--c-secondary').trim() || '#00ff41',
        accent: rootStyles.getPropertyValue('--c-accent').trim() || '#00d4ff',
        muted: rootStyles.getPropertyValue('--c-font-muted').trim() || '#00aa2a',
        warning: rootStyles.getPropertyValue('--c-warning').trim() || '#ffcc00',
        error: rootStyles.getPropertyValue('--c-error').trim() || '#ff3333',
        disabled: rootStyles.getPropertyValue('--c-disabled').trim() || '#333333',
        font: rootStyles.getPropertyValue('--c-font').trim() || '#00ff41',
        background: (styling?.backgroundColor && styling.backgroundColor !== 'transparent')
          ? styling.backgroundColor
          : themeBackground,
      };
    }

    private cloneGraphData(graphData: GraphData): GraphData {
      if (typeof structuredClone === 'function') {
        return structuredClone(graphData);
      }
      return JSON.parse(JSON.stringify(graphData)) as GraphData;
    }

  /**
   * Fetch the registered language extensions and store in state.
   * Non-fatal: called on startup; failure is silently ignored.
   */
  async initializeLanguages(): Promise<void> {
    try {
      const langs = await PlotService.fetchLanguages(this.stateController.api.parse);
      if (langs) this.stateController.update({ availableLanguages: langs });
    } catch {
      // non-fatal — backend may not be running yet
    }
  }

  /**
   * Load and display demo visualization
   */
  async loadDemo(): Promise<void> {
    this.stateController.clear();
    try {
      const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
      const data = await PlotService.loadDemo(
        this.stateController.api.plotter,
        layout
      );
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to load demo:', error);
      throw error;
    }
  }

  /**
   * Plot a single uploaded file via /parse/unified
   */
  async plotUploadedFile(file: RawFile): Promise<void> {
    this.stateController.clear();
    try {
      const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
      const opts   = this.stateController.state.parserOptions;
      const exts   = opts.fileExtensions.length > 0 ? opts.fileExtensions : null;
      const dir    = new Directory(new RepoInfo(), 1, new RawFolder('upload', file.size, [file]));
      const data   = await PlotService.plotUnified(
        this.stateController.api.parse, dir, 2, exts, layout
      );
      if (!data) throw new Error('No data returned from parse/unified');
      this.stateController.update({ parseDirectory: dir });
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to plot uploaded file:', error);
      throw error;
    }
  }
}

/**
 * Recursively merge an expanded folder into the directory tree at the given path.
 */
function mergeFolderAtPath(
  root: RawFolder,
  pathParts: string[],
  expanded: RawFolder
): RawFolder {
  if (pathParts.length === 0) return expanded;
  const [head, ...rest] = pathParts;
  return new RawFolder(
    root.name,
    root.size,
    root.files,
    root.folders.map(f =>
      f.name === head ? mergeFolderAtPath(f, rest, expanded) : f
    )
  );
}

/**
 * Repository Actions - handles GitHub repository operations
 */
export class RepoActions {
  constructor(private stateController: StateController) {}

  /**
   * Fetch and load a GitHub repository
   */
  async fetchRepository(url: string): Promise<void> {
    // TODO: This line prevents stream post call from firing. 
    //       Commenting out for now to get init parsing working. 
    //       Need to investigate intent with the below line.
    //this.stateController.clear();
    try {
      const data = await RepoService.getGithubRepo(url, this.stateController.api.repoReader);
      this.stateController.updateRepoContent(data);
    } catch (error) {
      console.error('Failed to fetch repository:', error);
      throw error;
    }
  }

  /**
   * Lazily expand a stub folder in the current repo tree.
   * Fetches one level of content for the given path and merges it into the tree.
   */
  async expandPath(repoUrl: string, path: string): Promise<void> {
    const current = this.stateController.repo.content;
    if (!current) return;
    try {
      const folder = await RepoService.getSubtree(
        repoUrl,
        path,
        this.stateController.api.repoReader
      );
      const pathParts = path.split('/').filter(p => p.length > 0);
      const newRoot = mergeFolderAtPath(current.root, pathParts, folder);
      this.stateController.setRepoContent({ ...current, root: newRoot });
    } catch (error) {
      console.error('Failed to expand path:', path, error);
      throw error;
    }
  }

  /**
   * Expand all stub folders in the current repo tree to the given depth.
   * Replaces the entire directory with a fully-expanded version (no file content).
   */
  async expandAll(repoUrl: string, maxDepth = 3): Promise<void> {
    try {
      const result = await RepoService.expandAllTree(
        repoUrl,
        this.stateController.api.repoReader,
        maxDepth
      );
      if (result) {
        this.stateController.updateRepoContent(result);
      }
    } catch (error) {
      console.error('Failed to expand all folders:', error);
      throw error;
    }
  }

}

/**
 * Upload Actions - handles local file upload operations
 */
export class UploadActions {
  constructor(private stateController: StateController) {}
}

/**
 * Combined actions interface for easy access
 */
export interface AppActions {
  plot: PlotActions;
  repo: RepoActions;
  upload: UploadActions;
}

/**
 * Create all action handlers for the application
 */
export function createActions(stateController: StateController): AppActions {
  return {
    plot: new PlotActions(stateController),
    repo: new RepoActions(stateController),
    upload: new UploadActions(stateController),
  };
}
