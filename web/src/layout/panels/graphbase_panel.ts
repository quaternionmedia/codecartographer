/**
 * Graphbase Panel — unified Graph Library
 *
 * Three tiers in one view:
 *   • Snapshots — full node/edge data, instant replay (MongoDB /db/snapshots)
 *   • Saved     — durable URL bookmarks, re-streams on load (/db/bookmarks)
 *   • Recent    — TTL'd filesystem cache entries; ☆ promotes to bookmark
 *
 * Snapshots and Saved sections are gated by graphbaseAvailable.
 * Recent always renders from the filesystem cache regardless of MongoDB.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';

let _snapInput = '';
let _bookmarkInput = '';

function _ageStr(age_seconds: number): string {
  const mins = Math.round(age_seconds / 60);
  return mins < 60 ? `${mins}m ago` : `${Math.round(mins / 60)}h ago`;
}

export function createGraphbasePanel(ctx: LayoutContext): m.Component {
  return {
    oncreate: () => ctx.refreshGraphbase(),

    view: () => {
      const available = ctx.graphbaseAvailable;
      const snapshots = ctx.graphbaseSnapshots;
      const bookmarks = ctx.graphbaseBookmarks;
      const recent    = ctx.cachedGraphs ?? [];
      const hasGraph  = !!(ctx.appState.state.graphData);
      const hasUrl    = !!ctx.panelState.repoUrl;
      const loading   = ctx.panelState.isLoading;
      const savedUrls = new Set(bookmarks.map(b => b.url));

      return m('div.gl-graphbase-panel', [

        // ── Header ───────────────────────────────────────────────────────────
        m('div.gl-graphbase-panel__header', [
          m('span.gl-graphbase-panel__title', '◈ Graph Library'),
          m('span.gl-graphbase-panel__status', {
            class: available
              ? 'gl-graphbase-panel__status--ok'
              : 'gl-graphbase-panel__status--off',
          }, available ? 'connected' : 'unavailable'),
        ]),

        !available
          ? m('p.gl-graphbase-panel__hint',
              'Set MONGODB_URI and restart to enable Snapshots and Saved. Recent graphs always show below.')
          : null,

        // ── Snapshots ─────────────────────────────────────────────────────────
        available
          ? m('div.gl-graphbase-panel__section', [
              m('div.gl-graphbase-panel__section-row', [
                m('span.gl-graphbase-panel__section-label', `Snapshots (${snapshots.length})`),
                hasGraph
                  ? m('div.gl-graphbase-panel__save', [
                      m('input.gl-graphbase-panel__name-input[type=text]', {
                        placeholder: 'Snapshot name…',
                        value: _snapInput,
                        oninput: (e: Event) => { _snapInput = (e.target as HTMLInputElement).value; },
                        onkeydown: (e: KeyboardEvent) => {
                          if (e.key === 'Enter' && _snapInput.trim()) {
                            ctx.saveGraphbaseSnapshot(_snapInput);
                            _snapInput = '';
                          }
                        },
                      }),
                      m('button.gl-graphbase-panel__save-btn', {
                        disabled: !_snapInput.trim() || loading,
                        onclick: () => { ctx.saveGraphbaseSnapshot(_snapInput); _snapInput = ''; },
                        title: 'Save full graph — instant replay, no re-parse',
                      }, '📸'),
                    ])
                  : m('p.gl-graphbase-panel__hint', 'Render a graph first to save a snapshot.'),
              ]),
              snapshots.length > 0
                ? snapshots.map(s =>
                    m('div.gl-graphbase-panel__entry', { key: s.name }, [
                      m('div.gl-graphbase-panel__entry-info', [
                        m('span.gl-graphbase-panel__entry-name', s.name),
                        m('span.gl-graphbase-panel__entry-url',
                          `${s.meta?.nodeCount ?? '?'} nodes · ${_ageStr(
                            Math.round(Date.now() / 1000 - (s.saved_at ?? 0)))}`,
                        ),
                      ]),
                      m('div.gl-graphbase-panel__entry-actions', [
                        m('button.gl-graphbase-panel__load-btn', {
                          onclick: () => ctx.loadGraphbaseSnapshot(s.name),
                          disabled: loading,
                          title: 'Replay instantly (no re-parse)',
                        }, '▶'),
                        m('button.gl-graphbase-panel__delete-btn', {
                          onclick: () => ctx.deleteGraphbaseSnapshot(s.name),
                          title: 'Delete snapshot',
                        }, '✕'),
                      ]),
                    ])
                  )
                : m('p.gl-graphbase-panel__hint', 'No snapshots yet.'),
            ])
          : null,

        // ── Saved bookmarks ───────────────────────────────────────────────────
        available
          ? m('div.gl-graphbase-panel__section', [
              m('div.gl-graphbase-panel__section-row', [
                m('span.gl-graphbase-panel__section-label', `Saved (${bookmarks.length})`),
                hasUrl
                  ? m('div.gl-graphbase-panel__save', [
                      m('input.gl-graphbase-panel__name-input[type=text]', {
                        placeholder: 'Bookmark name…',
                        value: _bookmarkInput,
                        oninput: (e: Event) => { _bookmarkInput = (e.target as HTMLInputElement).value; },
                        onkeydown: (e: KeyboardEvent) => {
                          if (e.key === 'Enter' && _bookmarkInput.trim()) {
                            ctx.saveGraphbaseBookmark(_bookmarkInput);
                            _bookmarkInput = '';
                          }
                        },
                      }),
                      m('button.gl-graphbase-panel__save-btn', {
                        disabled: !_bookmarkInput.trim() || loading,
                        onclick: () => { ctx.saveGraphbaseBookmark(_bookmarkInput); _bookmarkInput = ''; },
                        title: 'Save URL bookmark — re-streams on load',
                      }, '☆'),
                    ])
                  : m('p.gl-graphbase-panel__hint', 'Fetch a repo to save a bookmark.'),
              ]),
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
                          disabled: loading,
                          title: 'Re-stream from URL',
                        }, '▶'),
                        m('button.gl-graphbase-panel__delete-btn', {
                          onclick: () => ctx.deleteGraphbaseBookmark(bk.name),
                          title: 'Delete bookmark',
                        }, '✕'),
                      ]),
                    ])
                  )
                : m('p.gl-graphbase-panel__hint', 'No bookmarks yet.'),
            ])
          : null,

        // ── Recent ────────────────────────────────────────────────────────────
        m('div.gl-graphbase-panel__section', [
          m('span.gl-graphbase-panel__section-label', `Recent (${recent.length})`),
          recent.length > 0
            ? recent.slice(0, 8).map(e =>
                m('div.gl-graphbase-panel__entry', { key: e.key }, [
                  m('div.gl-graphbase-panel__entry-info', [
                    m('span.gl-graphbase-panel__entry-name',
                      e.label || e.url.replace('https://github.com/', '')),
                    m('span.gl-graphbase-panel__entry-url', _ageStr(e.age_seconds)),
                  ]),
                  m('div.gl-graphbase-panel__entry-actions', [
                    m('button.gl-graphbase-panel__load-btn', {
                      onclick: () => ctx.panelCallbacks.onLoadFromCache?.(e.key),
                      disabled: loading,
                      title: 'Replay from cache',
                    }, '▶'),
                    available && !savedUrls.has(e.url)
                      ? m('button.gl-graphbase-panel__promote-btn', {
                          onclick: () =>
                            ctx.saveGraphbaseBookmark(
                              e.label || e.url.replace('https://github.com/', ''),
                              e.url,
                            ),
                          title: 'Save as durable bookmark',
                        }, '☆')
                      : available
                        ? m('span.gl-graphbase-panel__saved-badge', { title: 'Already saved' }, '★')
                        : null,
                    m('button.gl-graphbase-panel__delete-btn', {
                      onclick: () => ctx.panelCallbacks.onEvictCache?.(e.key),
                      title: 'Remove from cache',
                    }, '✕'),
                  ]),
                ])
              )
            : m('p.gl-graphbase-panel__hint', 'No recent graphs — fetch a repo first.'),
        ]),
      ]);
    },
  };
}
