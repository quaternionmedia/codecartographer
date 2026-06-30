/**
 * Actions Panel (Plotbar)
 *
 * Docked GL panel containing the Plot button, Cancel/e-stop, and streaming
 * status + progress. Authoritative location for plot/cancel actions — the
 * floating e-stop overlay in graph_panel and the Plot button in source_panel
 * have been removed in favour of this panel.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { animations } from '../../core/animations';

export function createActionsPanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const state = ctx.panelState;
      const content = ctx.getControlPanelContent();
      const hasRepo = !!(content.repoDirectory && content.repoDirectory.size > 0);
      const hasUploads = content.uploadedFiles.length > 0;
      const hasRepoUrl = state.codeSourceMode === 'repo' && !!state.repoUrl;
      const hasSource = hasRepo || hasUploads || hasRepoUrl;

      const progress = state.progress;
      const progressPct = progress && progress.total > 0
        ? Math.round((progress.loaded / progress.total) * 100)
        : 0;

      return m('div.gl-panel.gl-actions-panel', [

        // ── Plot button ───────────────────────────────────────────────────
        hasSource && !state.isLoading
          ? m('button.gl-actions-panel__plot', {
              onclick: (e: MouseEvent) => {
                animations.buttonPress(e.currentTarget as Element);
                if (hasRepo) ctx.panelCallbacks.onPlotWholeRepo();
                else ctx.panelCallbacks.onPlotAllUploads();
              },
            }, [m('span', '▶'), m('span', 'Plot')])
          : null,

        // ── Cancel button ─────────────────────────────────────────────────
        state.isLoading
          ? m('button.gl-actions-panel__cancel', {
              onclick: () => ctx.cancel(),
              title: 'Cancel stream',
            }, [m('span', '⏹'), m('span', 'Cancel')])
          : null,

        // ── Status + progress ─────────────────────────────────────────────
        m('div.gl-actions-panel__status', [
          state.isLoading && progress
            ? m('div.gl-actions-panel__progress-bar-wrap', [
                m('div.gl-actions-panel__progress-bar', {
                  style: {
                    width: progress.total > 0 ? `${progressPct}%` : '0%',
                  },
                }),
              ])
            : state.isLoading
              ? m('div.gl-actions-panel__progress-bar-wrap', [
                  m('div.gl-actions-panel__progress-bar.gl-actions-panel__progress-bar--indeterminate'),
                ])
              : null,

          m('span.gl-actions-panel__status-text', [
            m('span.gl-actions-panel__status-dot', {
              class: state.isLoading ? 'gl-actions-panel__status-dot--active' : '',
            }),
            state.isLoading && progress && progress.phase === 'streaming'
              ? `Streaming ${progress.loaded}/${progress.total} nodes`
              : state.isLoading && progress
                ? `${progress.phase.charAt(0).toUpperCase() + progress.phase.slice(1)}\u2026`
                : state.isLoading
                  ? state.statusMessage
                  : state.statusMessage || 'Ready',
          ]),
        ]),
      ]);
    },
  };
}
