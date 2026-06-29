/**
 * Control Panel (GL wrapper)
 *
 * Mounts the source-loader + graph-settings control panel into a Golden Layout
 * panel. The panel is kept permanently open (no collapse toggle needed — GL
 * handles resize by dragging the splitter).
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { ControlPanel } from '../../components/codecarto/control_panel';

export function createControlPanelWrapper(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      // Always open — GL handles sizing; override the collapse behaviour.
      const panelState = { ...ctx.panelState, isOpen: true };

      return m('div.gl-panel.gl-panel--controls', [
        ControlPanel(
          panelState,
          ctx.panelCallbacks,
          (updates) => ctx.updatePanelState(updates),
          ctx.getControlPanelContent(),
        ),
      ]);
    },
  };
}
