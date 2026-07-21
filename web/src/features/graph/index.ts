/**
 * Graph Visualization Feature Module
 *
 * Handles all graph rendering and visualization logic
 */

// Components
export { Plot } from './components/Plot';

// Services
export { GraphRenderer } from './services/graph_renderer';
export type { GraphData } from './services/graph_renderer';
export type { GraphStylingOptions } from '../../state/types';
export { InteractionManager } from './services/interaction_manager';
export type { InteractionManagerCallbacks, InteractionManagerOptions } from './services/interaction_manager';

// Components (new)
export { RadialMenu, getContextMenuItems } from './components/radial_menu';
export type { RadialMenuItem, RadialMenuContext, RadialMenuOptions } from './components/radial_menu';

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
