/**
 * Centralized styling schema for graph visualization controls.
 * This schema defines all available styling options with their metadata,
 * enabling auto-generation of UI controls and consistent defaults.
 */

export type StyleOptionType = 'number' | 'color' | 'boolean' | 'select' | 'range';
export type StyleCategory = 'node' | 'edge' | 'label' | 'physics' | 'canvas';

export interface SelectOption {
  value: string;
  label: string;
}

export interface StyleOption {
  /** Unique key matching GraphStylingOptions property */
  key: string;
  /** Display label for UI */
  label: string;
  /** Control type */
  type: StyleOptionType;
  /** Category for grouping in UI */
  category: StyleCategory;
  /** Default value */
  default: unknown;
  /** Minimum value (for range/number) */
  min?: number;
  /** Maximum value (for range/number) */
  max?: number;
  /** Step increment (for range/number) */
  step?: number;
  /** Options for select type */
  options?: SelectOption[];
  /** Whether this option requires a re-render (vs just style update) */
  requiresRender?: boolean;
  /** Help text / tooltip */
  description?: string;
}

/**
 * Complete styling schema - single source of truth for all graph styling options.
 * To add a new control:
 * 1. Add entry here
 * 2. Add property to GraphStylingOptions interface in types.ts
 * 3. Apply the style in graph_renderer.ts
 */
export const STYLING_SCHEMA: StyleOption[] = [
  // === NODE OPTIONS ===
  {
    key: 'nodeSize',
    label: 'Node Size',
    type: 'range',
    category: 'node',
    default: 5,
    min: 1,
    max: 30,
    step: 1,
    description: 'Base size of nodes in pixels',
  },
  {
    key: 'nodeOpacity',
    label: 'Node Opacity',
    type: 'range',
    category: 'node',
    default: 1.0,
    min: 0.1,
    max: 1,
    step: 0.1,
    description: 'Transparency of node fill',
  },
  {
    key: 'nodeBorderWidth',
    label: 'Border Width',
    type: 'range',
    category: 'node',
    default: 1.5,
    min: 0,
    max: 5,
    step: 0.5,
    description: 'Width of node border stroke',
  },
  {
    key: 'nodeColorOverride',
    label: 'Color Override',
    type: 'color',
    category: 'node',
    default: null,
    description: 'Override automatic node coloring (leave empty for auto)',
  },
  {
    key: 'colorBy',
    label: 'Color By',
    type: 'select',
    category: 'node',
    default: 'auto',
    options: [
      { value: 'auto', label: 'Auto (depth/kind)' },
      { value: 'layer', label: 'Abstraction Layer' },
    ],
    description: 'Layer mode colors nodes by Lexicon abstraction layer where present, falling back to auto for nodes without one',
  },

  // === EDGE OPTIONS ===
  {
    key: 'edgeWidth',
    label: 'Edge Width',
    type: 'range',
    category: 'edge',
    default: 1.0,
    min: 0.5,
    max: 5,
    step: 0.5,
    description: 'Width of edge lines',
  },
  {
    key: 'edgeOpacity',
    label: 'Edge Opacity',
    type: 'range',
    category: 'edge',
    default: 1.0,
    min: 0.1,
    max: 1,
    step: 0.1,
    description: 'Transparency of edge lines',
  },
  {
    key: 'edgeColor',
    label: 'Edge Color',
    type: 'color',
    category: 'edge',
    default: '#666666',
    description: 'Color of edge lines',
  },
  {
    key: 'edgeStyle',
    label: 'Edge Style',
    type: 'select',
    category: 'edge',
    default: 'solid',
    options: [
      { value: 'solid', label: 'Solid' },
      { value: 'dashed', label: 'Dashed' },
      { value: 'dotted', label: 'Dotted' },
    ],
    description: 'Line style for edges',
  },

  // === LABEL OPTIONS ===
  {
    key: 'showNodeLabels',
    label: 'Show Node Labels',
    type: 'boolean',
    category: 'label',
    default: true,
    description: 'Display labels on nodes',
  },
  {
    key: 'showEdgeLabels',
    label: 'Show Edge Labels',
    type: 'boolean',
    category: 'label',
    default: false,
    description: 'Display labels on edges',
  },
  {
    key: 'labelSize',
    label: 'Label Size',
    type: 'range',
    category: 'label',
    default: 10,
    min: 6,
    max: 20,
    step: 1,
    description: 'Font size for labels',
  },
  {
    key: 'labelColor',
    label: 'Label Color',
    type: 'color',
    category: 'label',
    default: '#333333',
    description: 'Color of label text',
  },

  // === PHYSICS OPTIONS ===
  {
    key: 'enablePhysics',
    label: 'Enable Physics',
    type: 'boolean',
    category: 'physics',
    default: true,
    requiresRender: true,
    description: 'Enable force-directed simulation',
  },
  {
    key: 'chargeStrength',
    label: 'Repulsion Force',
    type: 'range',
    category: 'physics',
    default: -100,
    min: -500,
    max: 0,
    step: 10,
    requiresRender: true,
    description: 'Node repulsion strength (negative values push apart)',
  },
  {
    key: 'linkDistance',
    label: 'Link Distance',
    type: 'range',
    category: 'physics',
    default: 55,
    min: 20,
    max: 200,
    step: 5,
    requiresRender: true,
    description: 'Target distance between connected nodes',
  },

  // === CANVAS OPTIONS ===
  {
    key: 'backgroundColor',
    label: 'Background',
    type: 'color',
    category: 'canvas',
    default: 'transparent',
    description: 'Background color of the graph canvas',
  },
];

/**
 * Get styling options by category
 */
export function getOptionsByCategory(category: StyleCategory): StyleOption[] {
  return STYLING_SCHEMA.filter(opt => opt.category === category);
}

/**
 * Get all category names in display order
 */
export function getCategories(): StyleCategory[] {
  return ['node', 'edge', 'label', 'physics', 'canvas'];
}

/**
 * Get category display name
 */
export function getCategoryLabel(category: StyleCategory): string {
  const labels: Record<StyleCategory, string> = {
    node: 'Nodes',
    edge: 'Edges',
    label: 'Labels',
    physics: 'Physics',
    canvas: 'Canvas',
  };
  return labels[category];
}

/**
 * Get default values as an object
 */
export function getDefaultStyling(): Record<string, unknown> {
  const defaults: Record<string, unknown> = {};
  for (const opt of STYLING_SCHEMA) {
    defaults[opt.key] = opt.default;
  }
  return defaults;
}
