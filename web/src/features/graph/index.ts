/**
 * Graph Visualization Feature Module
 *
 * Handles all graph rendering and visualization logic
 */

// Components
export { Plot } from './components/Plot';

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

// State
export { graphActions } from './state/graph_actions';
export type { GraphState } from './state/graph_state';
