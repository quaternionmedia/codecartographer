/**
 * Graph Settings Panel
 *
 * Mounts the graph-settings portion of the old control panel into a dedicated
 * Golden Layout panel.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { ControlPanel } from '../../components/codecarto/control_panel';

export function createGraphSettingsPanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const panelState = { ...ctx.panelState, isOpen: true };

      return m('div.gl-panel.gl-panel--controls.gl-panel--controls-graph-settings', [
        ControlPanel(
          panelState,
          ctx.panelCallbacks,
          (updates) => ctx.updatePanelState(updates),
          ctx.getControlPanelContent(),
          { mode: 'graph' },
        ),
      ]);
    },
  };
}