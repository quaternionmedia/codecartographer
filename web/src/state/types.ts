/**
 * The option shapes the application's state carries.
 *
 * **THE LIVE STATE IS `cell_state.ts`.** This file once also declared a nested
 * `AppState` with defaults for every slice; nothing imported it -- the
 * application runs on the flat `ICellState` and `LayoutContext` -- so it was a
 * second description of the state that could drift from the first. What is
 * left here is what the renderers, the control panel and the cell state
 * actually share: the styling options, the parser options and the renderer id.
 */

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
  // 'auto' (default depth/kind heuristic) | 'layer' (Lexicon Option B
  // abstraction layer, when present on a node) | 'type' | 'degree' | ...
  colorBy?: string;

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
