/**
 * Graph Panel
 *
 * Mounts the D3 / vis-network graph visualisation into a Golden Layout panel.
 * Accepts a `LayoutContext` for shared state access, and returns a Mithril
 * component suitable for `m.mount(element, component)`.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { PlotComponent } from '../../components/codecarto/plot/plot';

export function createGraphPanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const state = ctx.appState.state;

      return m('div.gl-panel.gl-panel--graph', [
        // Main plot area
        m(PlotComponent, { graphs: state.graphContent }),
        // A copy of the graph in a tab of its own, moved and zoomed apart.
        m('button.gl-graph__duplicate', {
          type: 'button',
          disabled: !state.graphData,
          title: state.graphData
            ? 'Duplicate this graph into a window of its own, moved and zoomed apart from this one'
            : 'Nothing is drawn to duplicate',
          'aria-label': 'Duplicate the graph into a window of its own',
          onclick: () => ctx.duplicateGraph(),
        }, '⧉'),
      ]);
    },
  };
}
