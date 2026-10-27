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
    // The window's ⧉ sits in its stack's header, out of this panel; it is
    // disabled with nothing drawn, so it follows each redraw.
    oncreate: () => { setTimeout(() => ctx.syncDuplicateControl(), 0); },
    onupdate: () => ctx.syncDuplicateControl(),
    view: () => {
      const state = ctx.appState.state;

      return m('div.gl-panel.gl-panel--graph', [
        // Main plot area
        m(PlotComponent, { graphs: state.graphContent }),
      ]);
    },
  };
}
