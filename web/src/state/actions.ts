import m from 'mithril';
import { StateController } from '../state/state_controller';
import { PlotService } from '../services/plot_service';
import { RepoService } from '../features/repository';
import { handleDemoData as getDemoData } from '../services/demo_service';
import { GraphData } from '../features/graph';
import { GraphRendererRegistry } from '../features/graph/services/renderers';
import { Directory, RawFile } from '../components/models/source';
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
   * Create graph vnode from stored graph data
   * This can be called when graph data changes OR when styling changes
   */
  public createGraphVnode(): void {
    const graphData = this.stateController.state.graphData;
    if (!graphData) {
      logger.warn('createGraphVnode called but no graph data in state');
      return;
    }

    // Render function that can be called on create and update
    const renderGraph = (element: HTMLElement) => {
      // Get fresh styling options from state
      const stylingOptions = this.stateController.state.graphStyling;
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
        const selectedRenderer = this.stateController.state.selectedRenderer;

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
    // Use styling + renderer as key to force re-render when they change
    const renderKey = JSON.stringify({
      styling: this.stateController.state.graphStyling,
      renderer: this.stateController.state.selectedRenderer
    });

    const container = m('div.graph_content.graphRenderer', {
      key: renderKey,
      oncreate: (vnode: m.VnodeDOM) => {
        renderGraph(vnode.dom as HTMLElement);
      }
    });

    this.stateController.updatePlotFrame([container]);
  }

  /**
   * Load and display demo visualization
   */
  async loadDemo(): Promise<void> {
    this.stateController.clear();
    try {
      console.log('PlotActions.loadDemo - fetching demo data...');
      const data = await getDemoData();
      console.log('PlotActions.loadDemo - received data:', data);
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to load demo:', error);
      throw error;
    }
  }

  /**
   * Plot a single file from URL
   */
  async plotUrlFile(url: string): Promise<void> {
    this.stateController.clear();
    try {
      console.log('PlotActions.plotUrlFile - plotting URL:', url);
      const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
      const data = await PlotService.plotUrlFile(url, this.stateController.api.plotter, layout);
      console.log('PlotActions.plotUrlFile - received data:', data);
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to plot URL file:', error);
      throw error;
    }
  }

  /**
   * Plot entire repository structure
   */
  async plotWholeRepo(content: Directory): Promise<void> {
    this.stateController.clear();
    try {
      console.log('PlotActions.plotWholeRepo - plotting repo:', content);
      const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
      const parseMode = this.stateController.state.parserOptions.mode;
      console.log('PlotActions.plotWholeRepo - using parser mode:', parseMode);
      const data = await PlotService.plotRepoWhole(content, this.stateController.api.plotter, layout, parseMode);
      console.log('PlotActions.plotWholeRepo - received data:', data);
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to plot repository:', error);
      throw error;
    }
  }

  /**
   * Plot repository with dependencies
   */
  async plotRepoDeps(content: Directory): Promise<void> {
    this.stateController.clear();
    try {
      console.log('PlotActions.plotRepoDeps - plotting deps for:', content);
      const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
      const parseMode = this.stateController.state.parserOptions.mode;
      console.log('PlotActions.plotRepoDeps - using parser mode:', parseMode);
      const data = await PlotService.plotRepoWholeDeps(content, this.stateController.api.plotter, layout, parseMode);
      console.log('PlotActions.plotRepoDeps - received data:', data);
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to plot repository dependencies:', error);
      throw error;
    }
  }

  /**
   * Plot a single uploaded file
   */
  async plotUploadedFile(file: RawFile): Promise<void> {
    this.stateController.clear();
    try {
      console.log('PlotActions.plotUploadedFile - plotting file:', file);
      const layout = convertLayoutToBackend(this.stateController.state.graphStyling.layout);
      const parseMode = this.stateController.state.parserOptions.mode;
      console.log('PlotActions.plotUploadedFile - using parser mode:', parseMode);
      const data = await PlotService.plotFile(file, this.stateController.api.plotter, layout, parseMode);
      console.log('PlotActions.plotUploadedFile - received data:', data);
      this.handlePlotData(data);
    } catch (error) {
      console.error('Failed to plot uploaded file:', error);
      throw error;
    }
  }
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
    this.stateController.clear();
    try {
      const data = await RepoService.getGithubRepo(url, this.stateController.api.repoReader);
      this.stateController.updateRepoContent(data);
    } catch (error) {
      console.error('Failed to fetch repository:', error);
      throw error;
    }
  }

  /**
   * Select a file in the repository tree
   */
  selectFile(file: RawFile): void {
    this.stateController.setSelectedRepoFile(file);
  }

  /**
   * Clear repository data
   */
  clearRepository(): void {
    this.stateController.clearRepoData();
  }
}

/**
 * Upload Actions - handles local file upload operations
 */
export class UploadActions {
  constructor(private stateController: StateController) {}

  /**
   * Select an uploaded file
   */
  selectFile(file: RawFile): void {
    this.stateController.setSelectedLocalFile(file);
  }

  /**
   * Clear uploaded files
   */
  clearUploads(): void {
    this.stateController.clearLocalData();
  }
}

/**
 * UI Actions - handles UI state changes
 */
export class UIActions {
  constructor(private stateController: StateController) {}

  /**
   * Toggle the control panel visibility
   */
  toggleControlPanel(): void {
    // Would need to add this to state controller
  }

  /**
   * Set the active control panel tab
   */
  setActiveTab(tab: 'demo' | 'repo' | 'upload' | 'settings'): void {
    // Would need to add this to state controller
  }

  /**
   * Clear any error state
   */
  clearError(): void {
    // Would need to add this to state controller
  }
}

/**
 * Combined actions interface for easy access
 */
export interface AppActions {
  plot: PlotActions;
  repo: RepoActions;
  upload: UploadActions;
  ui: UIActions;
}

/**
 * Create all action handlers for the application
 */
export function createActions(stateController: StateController): AppActions {
  return {
    plot: new PlotActions(stateController),
    repo: new RepoActions(stateController),
    upload: new UploadActions(stateController),
    ui: new UIActions(stateController),
  };
}
