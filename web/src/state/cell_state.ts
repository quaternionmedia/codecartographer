import m from 'mithril';

import { MeiosisCell } from 'meiosis-setup/types';
import { DirectoryNavController } from '../components/codecarto/directory/directory_nav';
import { ConfigManager, DebugManager } from './config_manager';
import { GraphStylingOptions, ParserOptions, GraphRendererType } from './types';
import { GraphData } from '../features/graph';
import type { TopologyChoices, TopologyProblem } from '../services/topology_service';
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
  /**
   * What the harness offers, or null before anybody asked. **Null and empty
   * are different**: null is "not looked yet", an empty list is "the harness
   * answered and has none".
   */
  topologyChoices: TopologyChoices | null;
  /**
   * Why the topology could not be drawn, or null when it could. Held rather
   * than thrown, because a harness that is not running is the ordinary case
   * and the panel has a sentence to show for it.
   */
  topologyProblem: TopologyProblem | null;
  /** The topology currently drawn, so the panel can mark it. */
  topologyKind: string;
  /** The project the archive was read for, when a subject was asked about. */
  topologySubject: string;
  parserOptions: ParserOptions;
  selectedRenderer: GraphRendererType;
  availableLanguages: Record<string, string[]> | null;
  availableLexiconLanguages: string[];
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
  public topologyChoices: TopologyChoices | null = null;
  public topologyProblem: TopologyProblem | null = null;
  public topologyKind: string = 'delegation';
  public topologySubject: string = '';
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
    annotateLexicon: false,
  };
  public selectedRenderer: GraphRendererType = 'd3';
  public availableLanguages: Record<string, string[]> | null = null;
  public availableLexiconLanguages: string[] = [];
  public inputRepoUrl: string = '';
  public prompt: string = '';
  public redraw: () => void = () => {
    m.redraw();
  };
}
