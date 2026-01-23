/**
 * Graph Feature Actions
 *
 * Handles graph visualization state updates
 */
import { GraphState } from './graph_state';

export const graphActions = {
  /**
   * Update graph options (layout, type, etc.)
   */
  setOptions: (options: Partial<GraphState['options']>) => (state: GraphState): GraphState => ({
    ...state,
    options: { ...state.options, ...options },
  }),

  /**
   * Set rendering state
   */
  setRendering: (isRendering: boolean) => (state: GraphState): GraphState => ({
    ...state,
    isRendering,
  }),

  /**
   * Update graph metadata
   */
  setMetadata: (metadata: GraphState['metadata']) => (state: GraphState): GraphState => ({
    ...state,
    metadata,
  }),

  /**
   * Clear graph content
   */
  clear: () => (state: GraphState): GraphState => ({
    ...state,
    content: [],
    metadata: null,
    isRendering: false,
  }),
};
