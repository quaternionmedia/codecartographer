/**
 * Open Panel
 *
 * Where a graph starts: a GitHub URL or a local path, local files, the demo
 * and the lexicons, and the examples, and the recent graphs; the parse
 * options; and the one Plot / Cancel bar. Browsing what was opened is the Files
 * panel's (file_tree_panel.ts).
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { ControlPanel } from '../../components/codecarto/control_panel';

export function createOpenPanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      return m('div.gl-panel.gl-panel--controls.gl-panel--open', [
        ControlPanel(
          ctx.panelState,
          ctx.panelCallbacks,
          (updates) => ctx.updatePanelState(updates),
          ctx.getControlPanelContent(),
          { mode: 'open' },
        ),
      ]);
    },
  };
}
