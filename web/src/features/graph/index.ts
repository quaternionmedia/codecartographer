/**
 * Graph Visualization Feature Module
 *
 * The types every graph is made of, and the interaction profiles. The
 * component, state and action slices that used to be exported here were a
 * migration begun and not finished: nothing outside this barrel imported them,
 * and the application runs on `state/cell_state.ts` and `layout/`.
 */

// Services
export type { GraphData, GraphNode, GraphEdge } from './services/graph_types';
export type { GraphStylingOptions } from '../../state/types';

// Configuration
export {
  DEFAULT_PROFILE,
  CAD_PROFILE,
  GAMING_PROFILE,
  TOUCH_PROFILE,
  INTERACTION_PROFILES,
  getProfile,
  getProfileOptions,
} from './config/interaction_profiles';
export type {
  InteractionProfile,
  KeyboardBinding,
  MouseBinding,
  TouchBinding,
} from './config/interaction_profiles';
