/**
 * Interactions Panel — who did what at the harness, and through which way in.
 *
 * Controls, not a canvas, and read-only. It shows what `/harness/interactions`
 * returned: which harness answered, a table of names by act and way in, a
 * lane per act and way in counted over time, and the interactions newest
 * first. A row that names nobody says so; no element here answers a question
 * or starts anything.
 *
 * The reading is asked again on an interval while the panel is in the page,
 * and cleared when the panel leaves.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { heldBack, whenShown } from '../../features/estate/run_state';
import {
  actShown, answersShown, cellLevel, instanceShown, moreNamesShown, mostInACell, undatedShown, whoShown,
} from '../../features/estate/interactions';
import type { Interaction, Lane, WhoRow } from '../../features/estate/interactions';
import '../../features/estate/estate.css';
import './interactions_panel.css';

/** How often the harness is read while the panel is open. */
export const POLL_MS = 15000;

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

/** A name, and beside it the field of the harness's row it was read from. */
function named(who: string | null, from: string | null): m.Children {
  return [whoShown(who), from ? [' — ', m('code', from)] : null];
}

function whoRow(found: WhoRow): m.Children {
  return m('div.estate__row.interactions__who', {
    'data-who': found.who ?? '',
    'data-named': found.who ? 'yes' : 'no',
    'data-act': found.act,
    'data-way': found.way ?? '',
  }, [
    m('span.estate__dot'),
    m('span.estate__name', named(found.who, found.who_from)),
    m('span.estate__actions', m('span.estate-view__rung.interactions__count', String(found.count))),
    m('p.estate__role', actShown(found.act, found.way)),
    found.last ? m('p.estate__where', `newest ${whenShown(found.last)}`) : null,
  ]);
}

function laneRow(lane: Lane, most: number): m.Children {
  return m('div.interactions__lane', { 'data-act': lane.act, 'data-way': lane.way ?? '' }, [
    m('span.interactions__lane-name', actShown(lane.act, lane.way)),
    m('span.interactions__cells', { role: 'img', 'aria-label': `${actShown(lane.act, lane.way)}: ${lane.count}` },
      lane.cells.map((count) =>
        m('span.interactions__cell', { 'data-level': String(cellLevel(count, most)), 'data-count': String(count) }))),
    m('span.interactions__lane-count', String(lane.count)),
  ]);
}

function interactionRow(found: Interaction): m.Children {
  const through = [
    found.session ? `session ${text(found.session)}` : '',
    found.chat ? `chat ${text(found.chat)}` : '',
    found.turn ? `turn ${text(found.turn)}` : '',
  ].filter((part) => part !== '');
  return m('div.estate__row.interactions__row', {
    'data-act': found.act,
    'data-way': found.way ?? '',
    'data-ref': text(found.ref),
    'data-named': found.who ? 'yes' : 'no',
  }, [
    m('span.estate__dot'),
    m('span.estate__name', text(found.what)),
    m('span.estate__actions', m('span.estate-view__rung', actShown(found.act, found.way))),
    m('p.estate__detail.interactions__by', named(found.who, found.who_from)),
    m('p.estate__role', [
      m('code', text(found.ref)),
      found.project ? ` — ${found.project}` : '',
    ]),
    through.length ? m('p.estate__role.interactions__through', through.join(' · ')) : null,
    m('p.estate__where', found.at ? whenShown(found.at) : 'no time recorded'),
  ]);
}

export function createInteractionsPanel(ctx: LayoutContext): m.Component {
  let timer: ReturnType<typeof setInterval> | null = null;
  let root: Element | null = null;
  /** When the reading on screen arrived, by this window's clock. */
  let readAt: Date | null = null;

  const leave = () => {
    if (timer !== null) clearInterval(timer);
    timer = null;
    ctx.appState.update({ interactionsReading: null, interactionsProblem: null });
  };

  const ask = () => {
    // A panel closed in the dock is taken out of the page without this
    // component being told, so the interval checks for itself.
    if (root && !root.isConnected) {
      leave();
      return;
    }
    void ctx.actions.plot
      .loadHarnessInteractions()
      .then(() => {
        if (ctx.appState.state.interactionsReading) readAt = new Date();
        m.redraw();
      })
      .catch(() => undefined);
  };

  return {
    oninit: ask,
    oncreate: (vnode) => {
      root = vnode.dom;
      timer = setInterval(ask, POLL_MS);
    },
    onremove: leave,

    view: () => {
      const state = ctx.appState.state;
      const reading = state.interactionsReading;
      const problem = state.interactionsProblem;
      const most = reading ? mostInACell(reading.over_time.lanes) : 0;

      return m('div.gl-panel.gl-panel--controls.gl-panel--interactions', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'interactions',
              note: 'Nothing is listed. An empty list would look like a harness nobody used.',
              onRetry: () => {
                ctx.appState.update({ interactionsProblem: null });
                ask();
              },
            })
          : null,

        reading === null && !problem
          ? m('p.estate-view__pending', 'asking the harness…')
          : null,

        reading
          ? [
              m('p.estate-view__hint.interactions__read',
                `read ${readAt ? readAt.toLocaleTimeString() : 'just now'}, and again every ${POLL_MS / 1000} s while this panel is open`),

              m('div.estate-view__section', { 'data-interactions': 'instance' }, [
                m('h4.estate-view__heading', 'Which harness'),
                m('div.estate__rows',
                  m('div.estate__row.interactions__instance', {
                    class: reading.instance.identified ? 'is-live' : 'is-down',
                    'data-identified': reading.instance.identified ? 'yes' : 'no',
                  }, [
                    m('span.estate__dot'),
                    m('span.estate__name', m('code', reading.instance.where)),
                    reading.instance.identified
                      ? m('p.estate__detail', instanceShown(reading.instance, whenShown))
                      : m('p.estate__problem', [
                          reading.instance.problem,
                          reading.instance.remedy ? ` — ${reading.instance.remedy}` : '',
                        ]),
                  ])),
              ]),

              m('div.estate-view__section', { 'data-interactions': 'who' }, [
                m('h4.estate-view__heading', 'Who, and which way in'),
                reading.who.rows.length === 0
                  ? m('p.estate-view__hint', 'the harness holds no instruction, question, answer or tool run')
                  : null,
                m('div.estate__rows', reading.who.rows.map(whoRow)),
                moreNamesShown(reading.who.more)
                  ? m('p.estate-view__hint.interactions__more-names', moreNamesShown(reading.who.more))
                  : null,
              ]),

              m('div.estate-view__section', { 'data-interactions': 'over-time' }, [
                m('h4.estate-view__heading', 'Over time'),
                reading.over_time.lanes.length
                  ? [
                      m('div.interactions__lanes', reading.over_time.lanes.map((lane) => laneRow(lane, most))),
                      m('p.estate-view__hint.interactions__span',
                        `from ${whenShown(reading.over_time.from)} to ${whenShown(reading.over_time.to)}, in ${reading.over_time.cells} equal spans`),
                    ]
                  : m('p.estate-view__hint', 'no interaction read carries a time'),
                undatedShown(reading.over_time.undated)
                  ? m('p.estate-view__hint.interactions__undated', undatedShown(reading.over_time.undated))
                  : null,
              ]),

              m('div.estate-view__section', { 'data-interactions': 'rows' }, [
                m('h4.estate-view__heading', 'Newest first'),
                m('div.estate__rows', reading.interactions.rows.map(interactionRow)),
                heldBack(reading.interactions)
                  ? m('p.estate-view__hint.interactions__more', heldBack(reading.interactions))
                  : null,
                answersShown(reading.answers)
                  ? m('p.estate-view__hint.interactions__answers', answersShown(reading.answers))
                  : null,
                reading.unread_lists.map((found) =>
                  m('p.estate-view__hint.interactions__unread-list',
                    [`${found.what} not read: ${found.problem}`, found.remedy ? ` — ${found.remedy}` : ''])),
              ]),

              m('p.estate-view__hint.interactions__caveat', reading.caveat),
            ]
          : null,
      ]);
    },
  };
}
