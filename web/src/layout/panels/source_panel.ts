/**
 * Source Panel
 *
 * Mounts the source-loader portion of the control panel into a dedicated
 * Golden Layout panel.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { ControlPanel } from '../../components/codecarto/control_panel';

export function createSourcePanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const panelState = { ...ctx.panelState, isOpen: true };

      return m('div.gl-panel.gl-panel--controls.gl-panel--controls-source', [
        ControlPanel(
          panelState,
          ctx.panelCallbacks,
          (updates) => ctx.updatePanelState(updates),
          ctx.getControlPanelContent(),
          { mode: 'source' },
        ),
      ]);
    },
  };
}