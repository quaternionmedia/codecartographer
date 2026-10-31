/**
 * The styling a canvas is drawn with before a reader changes any of it.
 *
 * One object for both pages: the window starts its state from it
 * (`cell_state.ts`), and `view.html`, which has no state and no settings
 * panel, draws every document with it. Two copies would let the page draw a
 * graph unlike the window that exported it.
 */

import { GraphStylingOptions } from './types';
import { THEME_LABEL_COLOR } from '../features/graph/services/label_color';

export const DEFAULT_GRAPH_STYLING: Readonly<GraphStylingOptions> = {
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
  labelColor: THEME_LABEL_COLOR,
  backgroundColor: 'transparent',
  interactionProfile: 'default',
};
