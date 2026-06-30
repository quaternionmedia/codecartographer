/**
 * Repo Panel
 *
 * Single-domain GL panel: GitHub URL fetch, recent/cached graphs, example
 * chips, and a compact loaded-repo status line. Browsing the fetched
 * repository tree lives in file_tree_panel.ts (the "Files" panel) — this
 * panel does not duplicate that tree.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { ControlPanel } from '../../components/codecarto/control_panel';

export function createRepoPanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const panelState = { ...ctx.panelState, isOpen: true };

      return m('div.gl-panel.gl-panel--controls.gl-panel--controls-repo', [
        ControlPanel(
          panelState,
          ctx.panelCallbacks,
          (updates) => ctx.updatePanelState(updates),
          ctx.getControlPanelContent(),
          { mode: 'repo' },
        ),
      ]);
    },
  };
}
