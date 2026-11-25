/**
 * Harness Panel — what the harness is running and what it is asking.
 *
 * Controls, not a canvas, and read-only: it lists the harness's tool runs, the
 * questions it holds for a person and its instructions, as `/harness/data`
 * returned them, and says under each list how many rows were held back. No
 * element here answers a question or starts anything.
 *
 * The run states it lists are drawn on the canvas by `RunStateExtension`. A
 * state whose project no drawn box names is listed here with that said, so a
 * reader sees every state the harness gave whether or not a box shows it.
 *
 * The reading is asked again on an interval while the panel is in the page.
 * When the panel leaves, the reading is cleared and the boxes lose their
 * marks: a state nobody is refreshing is not shown.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { heldBack, joinStates, unplacedShown, whenShown } from '../../features/estate/run_state';
import type { HarnessListing, RunState } from '../../features/estate/run_state';
import '../../features/estate/estate.css';
import './harness_panel.css';

/** How often the harness is read while the panel is open. */
export const POLL_MS = 5000;

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

function listed(
  title: string,
  name: string,
  listing: HarnessListing,
  row: (found: Record<string, unknown>) => m.Children,
  empty: string,
  after: m.Children = null,
): m.Children {
  const more = heldBack(listing);
  return m('div.estate-view__section', { 'data-harness-list': name }, [
    m('h4.estate-view__heading', title),
    listing.problem
      ? m('p.estate-view__hint.harness__list-problem',
          [listing.problem, listing.remedy ? ` — ${listing.remedy}` : ''])
      : null,
    !listing.problem && listing.rows.length === 0 ? m('p.estate-view__hint', empty) : null,
    m('div.estate__rows', listing.rows.map(row)),
    more ? m('p.estate-view__hint.harness__more', more) : null,
    after,
  ]);
}

export function createHarnessPanel(ctx: LayoutContext): m.Component {
  let timer: ReturnType<typeof setInterval> | null = null;
  let root: Element | null = null;
  /** When the reading on screen arrived, by this window's clock. */
  let readAt: Date | null = null;

  const leave = () => {
    if (timer !== null) clearInterval(timer);
    timer = null;
    ctx.appState.update({ harnessReading: null, harnessProblem: null });
    ctx.applyRunState();
  };

  const ask = () => {
    // A panel closed in the dock is taken out of the page without this
    // component being told, so the interval checks for itself.
    if (root && !root.isConnected) {
      leave();
      return;
    }
    void ctx.actions.plot
      .loadHarnessReading()
      .then(() => {
        if (ctx.appState.state.harnessReading) readAt = new Date();
        ctx.applyRunState();
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
      const reading = state.harnessReading;
      const problem = state.harnessProblem;
      const joined = reading ? joinStates(reading.states, ctx.canvasNodes()) : null;
      const unmatched = new Set((joined?.unmatched ?? []).map((s: RunState) => s.project));

      return m('div.gl-panel.gl-panel--controls.gl-panel--harness', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'harness',
              note: 'Nothing is listed. An empty list would look like an idle harness.',
              onRetry: () => {
                ctx.appState.update({ harnessProblem: null });
                ask();
              },
            })
          : null,

        reading === null && !problem
          ? m('p.estate-view__pending', 'asking the harness…')
          : null,

        reading
          ? [
              m('p.estate-view__hint.harness__read',
                `read ${readAt ? readAt.toLocaleTimeString() : 'just now'}, and again every ${POLL_MS / 1000} s while this panel is open`),
              m('div.estate-view__section', { 'data-harness-list': 'states' }, [
                m('h4.estate-view__heading', 'On the canvas'),
                reading.states.length === 0
                  ? m('p.estate-view__hint', 'no instruction acted on and no question waiting names a project')
                  : null,
                m('div.estate__rows', reading.states.map((found) =>
                  m('div.estate__row.harness__state', {
                    'data-project': found.project,
                    'data-run-state': found.state,
                    'data-on-canvas': unmatched.has(found.project) ? 'no' : 'yes',
                  }, [
                    m('span.estate__dot'),
                    m('span.estate__name', found.project),
                    m('span.estate__actions', m('span.estate-view__rung', found.state)),
                    m('p.estate__detail', found.because),
                    unmatched.has(found.project)
                      ? m('p.estate__where.harness__unmatched', 'no box drawn names this project')
                      : null,
                  ]))),
                reading.unplaced.map((found) =>
                  m('p.estate-view__hint.harness__unplaced', unplacedShown(found))),
                m('p.estate-view__hint', reading.caveat),
              ]),

              listed('Questions for a person', 'queue', reading.queue, (found) =>
                m('div.estate__row', { 'data-ask': text(found.id), class: found.status === 'pending' ? 'is-live' : '' }, [
                  m('span.estate__dot'),
                  m('span.estate__name', text(found.prompt)),
                  m('span.estate__actions', m('span.estate-view__rung', text(found.status))),
                  m('p.estate__role', [
                    m('code', text(found.id)),
                    found.project ? ` — ${text(found.project)}` : '',
                  ]),
                  Array.isArray(found.options) && found.options.length
                    ? m('p.estate__detail', `options: ${found.options.map(text).join(', ')}`)
                    : null,
                  found.expires_at ? m('p.estate__where', `expires ${whenShown(found.expires_at)}`) : null,
                ]), 'the harness holds no questions',
                m('p.estate-view__hint.harness__answer-where', [
                  'Answered in a terminal: ',
                  m('code', 'qmcp human respond <id> <option>'),
                  '. Nothing in this panel answers.',
                ])),

              listed('Instructions', 'instructions', reading.instructions, (found) =>
                m('div.estate__row', { 'data-instruction': text(found.id) }, [
                  m('span.estate__dot'),
                  m('span.estate__name', text(found.text)),
                  m('span.estate__actions', m('span.estate-view__rung', text(found.status))),
                  m('p.estate__role', [
                    m('code', text(found.id)),
                    found.project ? ` — ${text(found.project)}` : ' — no project resolved',
                  ]),
                  found.outcome_text ? m('p.estate__detail', text(found.outcome_text)) : null,
                  m('p.estate__where', `updated ${whenShown(found.updated_at)}`),
                ]), 'the harness holds no instructions'),

              listed('Tool runs', 'runs', reading.runs, (found) =>
                m('div.estate__row', { 'data-run': text(found.id) }, [
                  m('span.estate__dot'),
                  m('span.estate__name', text(found.tool_name)),
                  m('span.estate__actions', m('span.estate-view__rung', text(found.status))),
                  found.error ? m('p.estate__detail', text(found.error)) : null,
                  m('p.estate__where', whenShown(found.created_at)),
                ]), 'the harness recorded no tool runs'),
            ]
          : null,
      ]);
    },
  };
}
