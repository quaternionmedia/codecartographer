import m from 'mithril';

import { MeiosisCell } from 'meiosis-setup/types';
import { DirectoryNavController } from '../components/codecarto/directory/directory_nav';
import { ConfigManager, DebugManager } from './config_manager';
import { GraphStylingOptions, ParserOptions, GraphRendererType } from './types';
import { GraphData } from '../features/graph';

export interface ICell extends MeiosisCell<ICellState> {}

export interface ICellState {
  debug: DebugManager;
  config: ConfigManager;
  repo: DirectoryNavController;
  local: DirectoryNavController;
  graphContent: m.Vnode[];
  graphData: GraphData | null;
  graphStyling: GraphStylingOptions;
  parserOptions: ParserOptions;
  selectedRenderer: GraphRendererType;
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
  public graphStyling: GraphStylingOptions = {
    layout: 'spring_layout',
    enablePhysics: true,
    chargeStrength: -150,
    linkDistance: 75,
    nodeSize: 6,
    nodeOpacity: 0.9,
    nodeBorderWidth: 2.0,
    nodeColorOverride: undefined,
    edgeWidth: 1.5,
    edgeOpacity: 0.7,
    edgeColor: '#666666',
    edgeStyle: 'solid',
    showNodeLabels: false,
    showEdgeLabels: false,
    labelSize: 11,
    labelColor: '#00ff41',
    backgroundColor: 'transparent',
    interactionProfile: 'default',
  };
  public parserOptions: ParserOptions = {
    mode: 'ast',
    fileExtensions: ['.py'],
  };
  public selectedRenderer: GraphRendererType = 'd3';
  public inputRepoUrl: string = '';
  public prompt: string = '';
  public redraw: () => void = () => {
    m.redraw();
  };
}
