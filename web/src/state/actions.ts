import m from 'mithril';
import { StateController } from '../state/state_controller';
import { PlotService } from '../services/plot_service';
import { RepoService } from '../features/repository';
import { handleDemoData as getDemoData } from '../services/demo_service';
import { GraphRenderer, GraphData } from '../features/graph';
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
   * Handles both new JSON graph format and legacy HTML iframe format
   */
  handlePlotData(data: unknown): void {
    logger.debug('PlotActions.handlePlotData - raw data:', data);

    if (!data) {
      logger.error('PlotActions.handlePlotData - data is null');
      return;
    }

    // Check if this is new JSON format (graph + metadata)
    if (typeof data === 'object' && !Array.isArray(data) && 'graph' in data && 'metadata' in data) {
      logger.info('PlotActions.handlePlotData - detected new JSON format');
      this.renderGraphData(data as GraphData);
      return;
    }

    // Legacy HTML format - render in iframe
    logger.info('PlotActions.handlePlotData - using legacy HTML format');

    // Convert to array if needed
    let dataArray: unknown[];
    if (!Array.isArray(data)) {
      logger.error('PlotActions.handlePlotData - invalid data format, not an array:', typeof data);
      // Try wrapping in array if it's an object with text/html
      if (typeof data === 'object' && data !== null && 'text/html' in data) {
        dataArray = [data];
      } else {
        return;
      }
    } else {
      dataArray = data;
    }

    const frames: m.Vnode[] = dataArray
      .filter((output: unknown): output is Record<string, unknown> => {
        if (typeof output !== 'object' || output === null) return false;
        const hasHtml = 'text/html' in output;
        logger.debug('PlotActions.handlePlotData - checking output:', output ? Object.keys(output) : null, 'hasHtml:', !!hasHtml);
        return hasHtml;
      })
      .map((output: Record<string, unknown>) =>
        m('iframe.graph_content.nbFrame', {
          srcdoc: output['text/html'] as string,
        })
      );

    logger.debug('PlotActions.handlePlotData - created frames:', frames.length);
    this.stateController.updatePlotFrame(frames);
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

      // Render based on visualization type
      try {
        switch (graphData.metadata.type) {
          case 'd3':
            GraphRenderer.renderD3(element, graphData, stylingOptions);
            break;
          case 'three':
            GraphRenderer.renderThree(element, graphData);
            break;
          case 'vis':
            GraphRenderer.renderVis(element, graphData);
            break;
          default:
            logger.warn('Unknown renderer type:', graphData.metadata.type, 'defaulting to d3');
            GraphRenderer.renderD3(element, graphData, stylingOptions);
        }
      } catch (error) {
        logger.error('Error rendering graph:', error);
        element.innerHTML = '<div style="padding: 20px; color: red;">Error rendering graph. Check console for details.</div>';
      }
    };

    // Create container element for D3 rendering
    // Use styling options as key to force re-render when they change
    const stylingKey = JSON.stringify(this.stateController.state.graphStyling);

    const container = m('div.graph_content.graphRenderer', {
      key: stylingKey,
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
