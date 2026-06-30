/**
 * Graphbase Panel — unified Graph Library
 *
 * Shows both storage tiers in one view so users never need to look in two
 * places:
 *   • Saved    — durable named bookmarks (MongoDB /db/bookmarks)
 *   • Recent   — TTL'd filesystem cache entries (same as the "Recent" section
 *               in the repo panel, but here with a one-click "Save" action
 *               that promotes a cache entry to a durable bookmark)
 *
 * Degrades gracefully: the Saved section is gated by graphbaseAvailable;
 * the Recent section renders from the filesystem cache regardless of MongoDB.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';

let _saveInput = '';

function _ageStr(age_seconds: number): string {
  const m = Math.round(age_seconds / 60);
  return m < 60 ? `${m}m ago` : `${Math.round(m / 60)}h ago`;
}

export function createGraphbasePanel(ctx: LayoutContext): m.Component {
  return {
    oncreate: () => ctx.refreshGraphbase(),

    view: () => {
      const available  = ctx.graphbaseAvailable;
      const bookmarks  = ctx.graphbaseBookmarks;
      const recent     = ctx.cachedGraphs ?? [];
      const hasUrl     = !!ctx.panelState.repoUrl;
      const isLoading  = ctx.panelState.isLoading;

      // Names already saved — used to mark "promote" button as redundant
      const savedUrls = new Set(bookmarks.map(b => b.url));

      return m('div.gl-graphbase-panel', [

        // ── Header ───────────────────────────────────────────────────────────
        m('div.gl-graphbase-panel__header', [
          m('span.gl-graphbase-panel__title', '◈ Graph Library'),
          m('span.gl-graphbase-panel__status', {
            class: available
              ? 'gl-graphbase-panel__status--ok'
              : 'gl-graphbase-panel__status--off',
          }, available ? 'graphbase connected' : 'graphbase unavailable'),
        ]),

        !available
          ? m('p.gl-graphbase-panel__hint',
              'Set MONGODB_URI to enable durable bookmarks. Recent graphs are always shown below.')
          : null,

        // ── Save current repo ─────────────────────────────────────────────────
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
                title: `Save current repo as a named bookmark`,
              }, 'Save'),
            ])
          : available
            ? m('p.gl-graphbase-panel__hint', 'Fetch a repo to save it as a bookmark.')
            : null,

        // ── Saved bookmarks ───────────────────────────────────────────────────
        available
          ? m('div.gl-graphbase-panel__section', [
              m('span.gl-graphbase-panel__section-label', `Saved (${bookmarks.length})`),
              bookmarks.length > 0
                ? bookmarks.map(bk =>
                    m('div.gl-graphbase-panel__entry', { key: bk.name }, [
                      m('div.gl-graphbase-panel__entry-info', [
                        m('span.gl-graphbase-panel__entry-name', bk.name),
                        m('span.gl-graphbase-panel__entry-url',
                          bk.url.replace('https://github.com/', '')),
                      ]),
                      m('div.gl-graphbase-panel__entry-actions', [
                        m('button.gl-graphbase-panel__load-btn', {
                          onclick: () => ctx.loadGraphbaseBookmark(bk),
                          disabled: isLoading,
                          title: `Stream ${bk.url}`,
                        }, '▶'),
                        m('button.gl-graphbase-panel__delete-btn', {
                          onclick: () => ctx.deleteGraphbaseBookmark(bk.name),
                          title: 'Delete bookmark',
                        }, '✕'),
                      ]),
                    ])
                  )
                : m('p.gl-graphbase-panel__hint', 'No bookmarks yet. Save a recent graph below.'),
            ])
          : null,

        // ── Recent (filesystem cache) ─────────────────────────────────────────
        m('div.gl-graphbase-panel__section', [
          m('span.gl-graphbase-panel__section-label', `Recent (${recent.length})`),
          recent.length > 0
            ? recent.slice(0, 8).map(entry =>
                m('div.gl-graphbase-panel__entry', { key: entry.key }, [
                  m('div.gl-graphbase-panel__entry-info', [
                    m('span.gl-graphbase-panel__entry-name',
                      entry.label || entry.url.replace('https://github.com/', '')),
                    m('span.gl-graphbase-panel__entry-url', _ageStr(entry.age_seconds)),
                  ]),
                  m('div.gl-graphbase-panel__entry-actions', [
                    m('button.gl-graphbase-panel__load-btn', {
                      onclick: () => ctx.panelCallbacks.onLoadFromCache?.(entry.key),
                      disabled: isLoading,
                      title: `Replay ${entry.url}`,
                    }, '▶'),
                    // Promote to durable bookmark — only shown when graphbase is available
                    // and this URL isn't already saved
                    available && !savedUrls.has(entry.url)
                      ? m('button.gl-graphbase-panel__promote-btn', {
                          onclick: () => {
                            const name = entry.label
                              || entry.url.replace('https://github.com/', '');
                            ctx.saveGraphbaseBookmark(name);
                          },
                          title: 'Save as a durable bookmark',
                        }, '☆')
                      : available
                        ? m('span.gl-graphbase-panel__saved-badge', { title: 'Already saved' }, '★')
                        : null,
                    m('button.gl-graphbase-panel__delete-btn', {
                      onclick: () => ctx.panelCallbacks.onEvictCache?.(entry.key),
                      title: 'Remove from cache',
                    }, '✕'),
                  ]),
                ])
              )
            : m('p.gl-graphbase-panel__hint', 'No recent graphs — fetch a repo to get started.'),
        ]),
      ]);
    },
  };
}
