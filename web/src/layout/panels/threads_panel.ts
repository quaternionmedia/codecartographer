/**
 * Threads Panel — a conversation from the harness's archive, its turns as a graph.
 *
 * Controls, not a canvas, and read-only. It shows what `/harness/threads`
 * returned: the conversations the archive lists, in the archive's order, cut
 * to the first the server lists, with what the archive says of itself. A
 * source and a text narrow the list. No element here imports, indexes or
 * changes a conversation.
 *
 * A row's control draws that conversation's turns in the Graph panel, through
 * the path every other plot takes, and the panel then shows its counts and
 * its newest turns from `/harness/thread`. A conversation the archive lists
 * and the harness does not serve is the harness's sentence in the panel.
 *
 * While a conversation is chosen it is read again on an interval. While
 * *follow the conversation* is ticked and the canvas holds its graph, a
 * reading whose turns differ draws the graph again as it was asked for, with
 * the old one kept until the new one arrives. The reading stops when the
 * panel leaves the page.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { EstateService } from '../../features/estate/estate_service';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import { isProblem } from '../../features/estate/seam_client';
import type { SeamProblem } from '../../features/estate/seam_client';
import { READING_ORDER } from '../../features/estate/interactions';
import {
  chosenOf, drawnIs, drawnShown, followDue, followShown, moreShown, readingShown, rolesShown, titleShown,
  turnsShown,
} from '../../features/estate/threads';
import type { Chosen, ThreadDocument, ThreadRow, ThreadsDocument, TurnRow } from '../../features/estate/threads';
import '../../features/estate/estate.css';
import './threads_panel.css';

/** How often a chosen conversation is read while the panel is open. */
export const POLL_MS = 15000;

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

function turnRow(turn: TurnRow): m.Children {
  return m('div.estate__row.threads__turn', { 'data-turn': String(turn.index), 'data-role': turn.role }, [
    m('span.estate__dot'),
    m('span.estate__name', `${turn.index} · ${turn.role}`),
    m('p.estate__detail.threads__said', [turn.text, turn.cut ? m('span.threads__cut', ' (cut short)') : null]),
    turn.at ? m('p.estate__where', text(turn.at)) : null,
  ]);
}

export function createThreadsPanel(ctx: LayoutContext): m.Component {
  let timer: ReturnType<typeof setInterval> | null = null;
  let root: Element | null = null;
  let listing: ThreadsDocument | null = null;
  let listProblem: SeamProblem | null = null;
  let source = '';
  let titled = '';
  let chosen: Chosen | null = null;
  let reading: ThreadDocument | null = null;
  let readProblem: SeamProblem | null = null;
  /** When the conversation on screen was read, by this window's clock. */
  let readAt: Date | null = null;
  let follow = true;
  /** Whether the graph on the canvas is in reading order, and not by a chosen algorithm. */
  let inReadingOrder = false;
  let drawing = false;
  let followedAt: Date | null = null;

  const harness = () => ctx.appState.api.harness;
  const metadata = () => ctx.appState.state.graphData?.metadata as EstateMetadata | undefined;

  const list = () => {
    void EstateService.threads(harness(), source, titled).then((found) => {
      if (isProblem(found)) {
        listProblem = found.problem;
        listing = null;
      } else {
        listProblem = null;
        listing = found.document as unknown as ThreadsDocument;
      }
      m.redraw();
    });
  };

  /**
   * Draw the chosen conversation. The first run is this panel's; a later run
   * of the same action is Graph Settings', by the algorithm chosen there.
   */
  const run = (keep: boolean): Promise<boolean> => {
    const which = chosen;
    if (!which) return Promise.resolve(false);
    let first = true;
    drawing = true;
    return ctx.plotWith(() => {
      if (!first) inReadingOrder = false;
      const layout = inReadingOrder ? READING_ORDER : undefined;
      const kept = first && keep;
      first = false;
      return ctx.actions.plot.drawThread(which, layout, kept);
    }).then((drew) => {
      drawing = false;
      return drew;
    }, () => {
      drawing = false;
      return false;
    });
  };

  const read = () => {
    // A panel closed in the dock is taken out of the page without this
    // component being told, so the interval checks for itself.
    if (root && !root.isConnected) {
      leave();
      return;
    }
    const which = chosen;
    if (!which) return;
    void EstateService.thread(harness(), which).then((found) => {
      if (which !== chosen) return;
      if (isProblem(found)) {
        readProblem = found.problem;
        reading = null;
      } else {
        readProblem = null;
        reading = found.document as unknown as ThreadDocument;
        readAt = new Date();
        const held = metadata();
        if (followDue(follow, drawnIs(held, which), held?.mark, reading.mark, drawing)) {
          void run(true).then((drew) => {
            if (drew) followedAt = new Date();
            m.redraw();
          });
        }
      }
      m.redraw();
    });
  };

  const leave = () => {
    if (timer !== null) clearInterval(timer);
    timer = null;
    ctx.appState.update({ threadProblem: null });
  };

  const choose = (row: ThreadRow) => {
    const which = chosenOf(row);
    if (!which) return;
    chosen = which;
    reading = null;
    readProblem = null;
    followedAt = null;
    inReadingOrder = true;
    ctx.appState.update({ threadProblem: null });
    read();
    void run(false).then((drew) => { if (drew) ctx.focusDockPanel('graph'); });
  };

  const threadRow = (row: ThreadRow): m.Children => {
    const which = chosenOf(row);
    const picked = which !== null && chosen !== null && which.source === chosen.source && which.id === chosen.id;
    return m('div.estate__row.threads__thread', {
      'data-source': text(row.source), 'data-thread': text(row.id), 'data-chosen': picked ? 'yes' : 'no',
    }, [
      m('span.estate__dot'),
      m('span.estate__name', titleShown(row.title)),
      m('span.estate__actions', m('span.estate-view__rung', text(row.source))),
      m('p.estate__role', [turnsShown(row.turns), row.diverged === true ? ' · diverged' : '']),
      which
        ? m('p.estate__where', m('button.threads__link.threads__draw', { type: 'button', onclick: () => choose(row) },
            'draw its turns'))
        : m('p.estate__where', 'the archive gives this row no source or no id'),
    ]);
  };

  return {
    oninit: list,
    oncreate: (vnode) => {
      root = vnode.dom;
      timer = setInterval(read, POLL_MS);
    },
    onremove: leave,

    view: () => {
      const drawProblem = ctx.appState.state.threadProblem;
      const held = metadata();
      const onCanvas = drawnIs(held, chosen);

      return m('div.gl-panel.gl-panel--controls.gl-panel--threads', [
        chosen
          ? m('div.estate-view__section', { 'data-threads': 'chosen' }, [
              m('h4.estate-view__heading', 'The conversation drawn'),
              drawProblem
                ? m(ProblemView, {
                    problem: drawProblem, prefix: 'threads',
                    onRetry: () => { void run(false); },
                  })
                : null,
              readProblem && !drawProblem
                ? m(ProblemView, { problem: readProblem, prefix: 'threads-read', note: 'Its turns are not listed.', onRetry: read })
                : null,
              reading
                ? [
                    m('div.estate__rows', m('div.estate__row.threads__chosen', {
                      'data-source': text(reading.source), 'data-thread': text(reading.id),
                    }, [
                      m('span.estate__dot'),
                      m('span.estate__name', titleShown(reading.title)),
                      m('span.estate__actions', m('span.estate-view__rung', text(reading.source))),
                      m('p.estate__role.threads__roles', rolesShown(reading.turns.roles)),
                      m('p.estate__role.threads__drawn', drawnShown(reading.drawn, reading.turns.count)),
                      reading.partial === true ? m('p.estate__problem.threads__partial', 'the harness says this conversation is partial') : null,
                      m('p.estate__where', m('a.threads__link.threads__where',
                        { href: reading.where, target: '_blank', rel: 'noopener' }, reading.where)),
                    ])),
                    m('label.threads__option', [
                      m('input.threads__follow', {
                        type: 'checkbox',
                        checked: follow,
                        onchange: (event: Event) => { follow = (event.target as HTMLInputElement).checked; },
                      }),
                      ' follow the conversation',
                    ]),
                    onCanvas && follow && followedAt
                      ? m('p.estate-view__hint.threads__followed',
                          `drawn again ${followedAt.toLocaleTimeString()}, for turns it had not held`)
                      : null,
                    m('p.estate-view__hint.threads__hint', [
                      'Read left to right: who spoke, what they said, a reply, who replied; rows run top to bottom in the order of the turns. ',
                      followShown(follow, POLL_MS / 1000),
                    ]),
                    m('p.estate-view__hint.threads__read', `read ${readAt ? readAt.toLocaleTimeString() : 'just now'}`),
                    m('h4.estate-view__heading', 'Newest turns'),
                    m('div.estate__rows', reading.turns.rows.map(turnRow)),
                    reading.turns.more > 0
                      ? m('p.estate-view__hint.threads__older', `${reading.turns.more} older turns are not listed here.`)
                      : null,
                  ]
                : null,
              !reading && !readProblem && !drawProblem ? m('p.estate-view__pending', 'asking the harness…') : null,
            ])
          : null,

        // Only when the canvas holds this seam's graph: its caveat, and where it was read.
        m(Provenance, { metadata: held, prefix: 'threads-graph', kind: 'thread' }),

        m('div.estate-view__section', { 'data-threads': 'archive' }, [
          m('h4.estate-view__heading', 'The archive'),
          m('form.threads__narrow', {
            onsubmit: (event: Event) => { event.preventDefault(); list(); },
          }, [
            m('select.threads__source', {
              'aria-label': 'source',
              value: source,
              onchange: (event: Event) => { source = (event.target as HTMLSelectElement).value; list(); },
            }, [
              m('option', { value: '' }, 'every source'),
              Object.entries(listing?.sources ?? {}).map(([name, count]) =>
                m('option', { value: name }, `${name} (${count})`)),
            ]),
            m('input.threads__titled', {
              type: 'text', 'aria-label': 'title holds', placeholder: 'title holds…', value: titled,
              oninput: (event: Event) => { titled = (event.target as HTMLInputElement).value; },
            }),
            m('button.threads__list', { type: 'submit' }, 'list'),
          ]),
          listProblem
            ? m(ProblemView, {
                problem: listProblem, prefix: 'threads-list',
                note: 'Nothing is listed. An empty list would look like an archive that holds nothing.',
                onRetry: list,
              })
            : null,
          listing === null && !listProblem ? m('p.estate-view__pending', 'asking the harness…') : null,
          listing
            ? [
                listing.threads.length === 0
                  ? m('p.estate-view__hint.threads__none', 'the archive lists no conversation that matches')
                  : null,
                m('div.estate__rows', listing.threads.map(threadRow)),
                moreShown(listing.more) ? m('p.estate-view__hint.threads__more', moreShown(listing.more)) : null,
                readingShown(listing.reading).map((said) => m('p.estate-view__hint.threads__reading', said)),
                listing.generated_at
                  ? m('p.estate-view__hint.threads__generated', `the archive's index is of ${text(listing.generated_at)}`)
                  : null,
                m('p.estate__where', m('a.threads__link.threads__list-where',
                  { href: listing.where, target: '_blank', rel: 'noopener' }, listing.where)),
              ]
            : null,
        ]),
      ]);
    },
  };
}
