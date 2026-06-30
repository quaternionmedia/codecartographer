import m from 'mithril';

import { MeiosisCell } from 'meiosis-setup/types';
import { DirectoryNavController } from '../components/codecarto/directory/directory_nav';
import { ConfigManager, DebugManager } from './config_manager';
import { GraphStylingOptions, ParserOptions, GraphRendererType } from './types';
import { GraphData } from '../features/graph';
import { Directory } from '../components/models/source';

export interface ICell extends MeiosisCell<ICellState> {}

export interface ICellState {
  debug: DebugManager;
  config: ConfigManager;
  repo: DirectoryNavController;
  local: DirectoryNavController;
  graphContent: m.Vnode[];
  graphData: GraphData | null;
  /**
   * The Directory object used for the most recent unified parse.
   * Stored so that expand-node calls can reuse the same directory context.
   */
  parseDirectory: Directory | null;
  graphStyling: GraphStylingOptions;
  parserOptions: ParserOptions;
  selectedRenderer: GraphRendererType;
  availableLanguages: Record<string, string[]> | null;
  inputRepoUrl: string;
  prompt: string;
  redraw: () => void;
}

// Used for initial app state
export class CellState implements ICellState {
  public debug = new DebugManager();
  public config = new ConfigManager();
  public repo = new DirectoryNavController(false);
  public local = new DirectoryNavController(true);
  public graphContent: m.Vnode[] = [];
  public graphData: GraphData | null = null;
  public parseDirectory: Directory | null = null;
  public graphStyling: GraphStylingOptions = {
    layout: 'spring_layout',
    enablePhysics: true,
    chargeStrength: -350,
    linkDistance: 120,
    nodeSize: 4,
    nodeOpacity: 0.75,
    nodeBorderWidth: 0,
    nodeColorOverride: undefined,
    edgeWidth: 1.5,
    edgeOpacity: 0.7,
    edgeColor: '#666666',
    edgeStyle: 'solid',
    showNodeLabels: false,
    showEdgeLabels: false,
    labelSize: 9,
    labelColor: '#00ff41',
    backgroundColor: 'transparent',
    interactionProfile: 'default',
  };
  public parserOptions: ParserOptions = {
    fileExtensions: [],
  };
  public selectedRenderer: GraphRendererType = 'd3';
  public availableLanguages: Record<string, string[]> | null = null;
  public inputRepoUrl: string = '';
  public prompt: string = '';
  public redraw: () => void = () => {
    m.redraw();
  };
}
