import m from 'mithril';
import { Directory, RawFile, RawFolder } from '../components/models/source';

/**
 * Core application state types for Code Cartographer
 * These types define the shape of state throughout the application
 */

/** Configuration state */
export interface ConfigState {
  backendUrl: string;
  theme: 'terminal' | 'light' | 'cyberpunk' | 'ocean' | 'sunset' | 'forest' | 'noir' | 'candy';
}

/** Debug/development state */
export interface DebugState {
  isDebugMode: boolean;
  showTracer: boolean;
}

/** UI state for panels, loading, and errors */
export interface UIState {
  isLoading: boolean;
  loadingMessage: string | null;
  error: string | null;
  controlPanelOpen: boolean;
  controlPanelTab: 'demo' | 'repo' | 'upload' | 'settings';
  /** @deprecated Use controlPanelOpen instead */
  leftNavOpen: boolean;
  /** @deprecated Use controlPanelOpen instead */
  rightNavOpen: boolean;
}

/** GitHub repository state */
export interface RepoState {
  url: string;
  directory: Directory | null;
  selectedFile: RawFile | null;
  selectedFolder: RawFolder | null;
  isMenuOpen: boolean;
  component: m.Vnode[] | null;
}

/** Local file upload state */
export interface LocalState {
  files: RawFile[];
  directory: Directory | null;
  selectedFile: RawFile | null;
  selectedFolder: RawFolder | null;
  isMenuOpen: boolean;
  component: m.Vnode[] | null;
}

/** Parser configuration options */
export interface ParserOptions {
  fileExtensions: string[];    // File extensions to parse (e.g., ['.py', '.js'])
  // Stamp Lexicon abstraction-layer data onto real parsed nodes whose
  // language has one (see lexicon_bridge.py) - opt-in, off by default.
  annotateLexicon: boolean;
}

/** Edge line style */
export type EdgeStyle = 'solid' | 'dashed' | 'dotted';

/** Graph styling options */
export interface GraphStylingOptions {
  // Layout Algorithm
  layout: string;

  // Physics Simulation
  enablePhysics: boolean;
  chargeStrength: number;      // in pixels (repulsion force)
  linkDistance: number;         // in pixels (target edge length)

  // Node Appearance
  nodeSize: number;            // in pixels (radius)
  nodeOpacity: number;         // 0.0 to 1.0
  nodeBorderWidth: number;     // in pixels
  nodeColorOverride?: string;  // Optional override for automatic node coloring

  // Edge Appearance
  edgeWidth: number;           // in pixels
  edgeOpacity: number;         // 0.0 to 1.0
  edgeColor?: string;          // Edge line color (default: theme-based)
  edgeStyle?: EdgeStyle;       // Edge line style (solid, dashed, dotted)

  // Label Appearance
  showNodeLabels: boolean;
  showEdgeLabels: boolean;
  labelSize: number;           // in pixels (font size)
  labelColor: string;          // hex color

  // Canvas Appearance
  backgroundColor?: string;    // Graph canvas background color

  // Interactions
  interactionProfile: string;  // Profile ID (default, cad, gaming, touch)

  // System renderer — selects which SystemDefinition to render
  systemId?: string;           // e.g. 'pam' (default)

  // Per-depth label visibility — overrides showNodeLabels per depth level when present.
  // depth 0 = dir, 1 = file, 2 = symbol, 3 = sub-symbol.
  // Absence of a key means "follow the global showNodeLabels setting."
  showLabelsByDepth?: Partial<Record<number, boolean>>;

  // Compound layout — show translucent bounding circles per dir/file group
  showCompoundGroups?: boolean;

  // Allow dynamic properties for extensibility
  [key: string]: unknown;
}

/** Graph renderer type */
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'system';

/** Graph visualization state */
export interface GraphState {
  content: m.Vnode[];
  isRendering: boolean;
  styling: GraphStylingOptions;
  parserOptions: ParserOptions;
  selectedRenderer: GraphRendererType;
  /**
   * The Directory object used for the most recent unified parse.
   * Stored so that subsequent expand-node calls can reuse the same
   * directory context without requiring the user to re-submit it.
   */
  parseDirectory: Directory | null;
}

/** Complete application state */
export interface AppState {
  config: ConfigState;
  debug: DebugState;
  ui: UIState;
  repo: RepoState;
  local: LocalState;
  graph: GraphState;
}

/** Default state values */
export const DEFAULT_UI_STATE: UIState = {
  isLoading: false,
  loadingMessage: null,
  error: null,
  controlPanelOpen: false,
  controlPanelTab: 'demo',
  leftNavOpen: false,
  rightNavOpen: false,
};

export const DEFAULT_REPO_STATE: RepoState = {
  url: '',
  directory: null,
  selectedFile: null,
  selectedFolder: null,
  isMenuOpen: false,
  component: null,
};

export const DEFAULT_LOCAL_STATE: LocalState = {
  files: [],
  directory: null,
  selectedFile: null,
  selectedFolder: null,
  isMenuOpen: false,
  component: null,
};

export const DEFAULT_GRAPH_STATE: GraphState = {
  content: [],
  isRendering: false,
  parseDirectory: null,
  styling: {
    layout: 'spring_layout',
    enablePhysics: true,
    chargeStrength: -150,
    linkDistance: 75,
    nodeSize: 6,
    nodeOpacity: 0.9,
    nodeBorderWidth: 2.0,
    edgeWidth: 1.5,
    edgeOpacity: 0.7,
    showNodeLabels: false,
    showEdgeLabels: false,
    labelSize: 11,
    labelColor: '#00ff41',
    interactionProfile: 'default',
    showCompoundGroups: true,
  },
  parserOptions: {
    fileExtensions: [],
  },
  selectedRenderer: 'd3',
};
