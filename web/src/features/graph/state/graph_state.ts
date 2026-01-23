/**
 * Graph Feature State Management
 */
import m from 'mithril';

export interface GraphState {
  /** Current graph content (vnodes for rendering) */
  content: m.Vnode[];
  /** Whether graph is currently being rendered */
  isRendering: boolean;
  /** Current visualization options */
  options: {
    layout: string;
    type: 'd3' | 'three' | 'vis';
    nodeSize: number;
    edgeWidth: number;
    showLabels: boolean;
  };
  /** Graph metadata from backend */
  metadata: {
    nodeCount: number;
    edgeCount: number;
    layout: string;
    type: string;
  } | null;
}

export const DEFAULT_GRAPH_STATE: GraphState = {
  content: [],
  isRendering: false,
  options: {
    layout: 'Spectral',
    type: 'd3',
    nodeSize: 1.0,
    edgeWidth: 1.0,
    showLabels: true,
  },
  metadata: null,
};
