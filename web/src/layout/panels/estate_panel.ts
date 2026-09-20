/**
 * Estate Panel — what is up, before anything is drawn.
 *
 * Every seam this window reads, one row each: identified, or the sentence that
 * would change that. It is the panel to open on a fresh workstation, because
 * the other estate panels each say only when *their* seam is missing and a
 * reader had to open all of them to learn that nothing was running.
 *
 * A LIVE ROW LEADS SOMEWHERE. Each row names the panel that draws its seam and
 * offers to open it. A seam with routes and no panel is shown with that button
 * disabled and a reason — the gap between served and drawn is one of the more
 * useful things this table can show, and a row that only appeared once a panel
 * existed would hide it.
 *
 * THE ROWS COME FROM THE SERVER. The probes run there, once per request, and
 * this panel adds no judgement of its own: `ok` is the server's word, and the
 * caveat above the rows is the server's sentence.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import type { DockPanelId } from '../panel_registry';
import { PanelRegistry } from '../panel_registry';
import { ProblemView } from '../../features/estate/problem_view';
import type { SeamRow } from '../../features/estate/estate_service';
import '../../features/estate/estate.css';

export function createEstatePanel(ctx: LayoutContext): m.Component {
  /** Per panel and cleared by a failure, for the reason the topology panel's
   *  flag is: a module-level flag made a down estate unretryable. */
  let asked = false;

  const ask = () => {
    asked = true;
    void ctx.actions.plot.loadSeams().catch(() => {
      asked = false;
    });
  };

  const row = (seam: SeamRow) => {
    const panel = seam.panel ? PanelRegistry.get(seam.panel as DockPanelId) : undefined;
    return m('div.estate__row', { class: seam.ok ? 'is-live' : 'is-down', 'data-seam': seam.name }, [
      m('span.estate__dot'),
      m('span.estate__name', seam.name),
      m('span.estate__actions', [
        m('button.estate__open', {
          disabled: !panel,
          title: panel ? `open the ${panel.menuLabel} panel` : 'nothing draws this seam yet',
          onclick: () => panel && ctx.restoreDockPanel(panel.id),
        }, panel ? `open ${panel.menuLabel.toLowerCase()}` : 'no panel yet'),
      ]),
      m('p.estate__role', seam.role),
      seam.ok
        ? [
            seam.detail ? m('p.estate__detail', seam.detail) : null,
            m('p.estate__where', ['identified at ', m('code', seam.where),
              seam.schema !== null ? `, schema ${seam.schema}` : '']),
          ]
        : [
            m('p.estate__problem', seam.problem),
            seam.remedy ? m('p.estate__remedy', seam.remedy) : null,
            m('p.estate__where', ['tried ', m('code', seam.where)]),
          ],
      seam.routes.length
        ? m('p.estate__routes', seam.routes.join(' · '))
        : null,
    ]);
  };

  return {
    oninit: () => {
      if (!asked) ask();
    },

    view: () => {
      const state = ctx.appState.state;
      const seams = state.estateSeams;
      const problem = state.estateProblem;

      return m('div.gl-panel.gl-panel--controls.gl-panel--estate', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'estate',
              note: 'The table could not be read. This is this window\'s own server, not a seam.',
              onRetry: () => {
                ctx.appState.update({ estateProblem: null });
                ask();
              },
            })
          : null,

        seams?.caveat
          ? m('p.seam-caveat.estate__caveat',
              { class: seams.live === seams.seams.length ? 'is-complete' : 'is-partial' },
              seams.caveat)
          : null,

        m('div.estate-view__section', [
          m('h4.estate-view__heading', 'Seams'),
          seams === null && !problem
            ? m('p.estate__pending', 'asking each seam what it is…')
            : null,
          seams ? m('div.estate__rows', seams.seams.map(row)) : null,
          m('div.estate__actions', [
            m('button.estate__refresh', { onclick: () => ask() }, 'ask again'),
            m('p.estate__hint',
              'A row is live when the far side answered with the shape this window expects — not when a port answered.'),
          ]),
        ]),
      ]);
    },
  };
}
