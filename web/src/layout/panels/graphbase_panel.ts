/**
 * Graphbase Panel
 *
 * Durable named-graph bookmarks backed by MongoDB via /db/bookmarks.
 * Only functional when MONGODB_URI is set on the backend — shows a clear
 * "unavailable" state otherwise so users understand it's a config choice,
 * not a bug.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';

let _saveInput = '';

export function createGraphbasePanel(ctx: LayoutContext): m.Component {
  return {
    oncreate: () => ctx.refreshGraphbase(),

    view: () => {
      const available = ctx.graphbaseAvailable;
      const bookmarks = ctx.graphbaseBookmarks;
      const hasUrl = !!ctx.panelState.repoUrl;

      return m('div.gl-panel.gl-graphbase-panel', [

        m('div.gl-graphbase-panel__header', [
          m('span.gl-graphbase-panel__title', '◈ Graphbase'),
          m('span.gl-graphbase-panel__status', {
            class: available
              ? 'gl-graphbase-panel__status--ok'
              : 'gl-graphbase-panel__status--off',
          }, available ? 'connected' : 'unavailable'),
        ]),

        !available
          ? m('p.gl-graphbase-panel__hint',
              'Set MONGODB_URI on the backend to enable durable graph bookmarks.')
          : null,

        // ── Save current repo as a bookmark ─────────────────────────────────
        available && hasUrl
          ? m('div.gl-graphbase-panel__save', [
              m('input.gl-graphbase-panel__name-input[type=text]', {
                placeholder: 'Bookmark name…',
                value: _saveInput,
                oninput: (e: Event) => { _saveInput = (e.target as HTMLInputElement).value; },
                onkeydown: (e: KeyboardEvent) => {
                  if (e.key === 'Enter' && _saveInput.trim()) {
                    ctx.saveGraphbaseBookmark(_saveInput);
                    _saveInput = '';
                  }
                },
              }),
              m('button.gl-graphbase-panel__save-btn', {
                disabled: !_saveInput.trim(),
                onclick: () => { ctx.saveGraphbaseBookmark(_saveInput); _saveInput = ''; },
              }, 'Save'),
            ])
          : available && !hasUrl
            ? m('p.gl-graphbase-panel__hint', 'Load a repo first to save a bookmark.')
            : null,

        // ── Saved bookmarks list ─────────────────────────────────────────────
        available && bookmarks.length > 0
          ? m('div.gl-graphbase-panel__list', [
              m('span.gl-graphbase-panel__section-label', 'Saved'),
              bookmarks.map(bk =>
                m('div.gl-graphbase-panel__entry', { key: bk.name }, [
                  m('div.gl-graphbase-panel__entry-info', [
                    m('span.gl-graphbase-panel__entry-name', bk.name),
                    m('span.gl-graphbase-panel__entry-url',
                      bk.url.replace('https://github.com/', '')),
                  ]),
                  m('div.gl-graphbase-panel__entry-actions', [
                    m('button.gl-graphbase-panel__load-btn', {
                      onclick: () => ctx.loadGraphbaseBookmark(bk),
                      title: `Stream ${bk.url}`,
                    }, '▶'),
                    m('button.gl-graphbase-panel__delete-btn', {
                      onclick: () => ctx.deleteGraphbaseBookmark(bk.name),
                      title: 'Delete bookmark',
                    }, '✕'),
                  ]),
                ])
              ),
            ])
          : available
            ? m('p.gl-graphbase-panel__hint', 'No bookmarks yet.')
            : null,
      ]);
    },
  };
}
