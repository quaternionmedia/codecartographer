/**
 * Chrestomathy Panel — one construct, set beside itself in every language.
 *
 * A printed chrestomathy taught a language by placing passages side by side;
 * this one places a construct — a record, a sum type, an interrupt handler, a
 * volatile access — in C, Rust, Python, assembly and the linker script, with
 * the tokens each spells it with and the abstraction layer each token sits on.
 *
 * THE ROW WITH NOTHING IN IT IS THE LESSON. Rust has no `volatile`; C has no
 * method. A language with no spelling is a row saying so, never a missing row
 * — `chrestomathy_rows.ts` decides that, under test.
 *
 * Controls, not a canvas: "draw" puts the construct on the one canvas with its
 * tokens coloured by layer, and the legend names the layers.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance, caveatShown } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import { chrestomathyRows } from '../../features/cartography/chrestomathy_rows';
import '../../features/estate/estate.css';

export function createChrestomathyPanel(ctx: LayoutContext): m.Component {
  let asked = false;

  const ask = () => {
    asked = true;
    const plot = ctx.actions.plot;
    void Promise.all([
      plot.loadConstructIndex(),
      plot.loadChrestomathy(ctx.appState.state.constructChosen),
    ]).catch(() => { asked = false; });
  };

  return {
    oninit: () => {
      if (!asked) ask();
    },

    view: () => {
      const state = ctx.appState.state;
      const index = state.constructIndex;
      const reading = state.chrestomathyReading;
      const problem = state.chrestomathyProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;
      const constructs = index?.constructs.filter((c) => !c.facet) ?? [];
      const facets = index?.constructs.filter((c) => c.facet) ?? [];

      return m('div.gl-panel.gl-panel--controls.gl-panel--chrestomathy', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'chrestomathy',
              onRetry: () => {
                ctx.appState.update({ chrestomathyProblem: null });
                ask();
              },
            })
          : null,

        m(Provenance, { metadata, prefix: 'chrestomathy', kind: 'chrestomathy' }),

        m('div.estate-view__section', [
          m('h4.estate-view__heading', 'Construct'),
          index
            ? m('select.cartography__select', {
                value: state.constructChosen,
                onchange: (e: Event) =>
                  void ctx.actions.plot.loadChrestomathy((e.target as HTMLSelectElement).value),
              }, [
                m('optgroup', { label: 'what a thing is' },
                  constructs.map((c) => m('option', { value: c.id }, `${c.name} — ${c.id}`))),
                m('optgroup', { label: 'what a thing can also be' },
                  facets.map((c) => m('option', { value: c.id }, `${c.name} — ${c.id}`))),
              ])
            : m('p.estate-view__pending', 'reading the vocabulary…'),
          reading ? m('p.estate__detail', reading.construct.gloss) : null,
        ]),

        reading
          ? m('div.estate-view__section', [
              m('table.cartography__table', [
                m('thead', m('tr', [m('th', 'language'), m('th', 'spelled'), m('th', 'parsed as'), m('th', 'note')])),
                m('tbody', chrestomathyRows(reading.languages).map((row) =>
                  m(`tr${row.silent ? '.is-silent' : ''}`, { 'data-language': row.language }, [
                    m('td', row.label),
                    m('td', [
                      m('code', row.spelling),
                      row.layers.map((layer) => m('span.cartography__layer', layer)),
                    ]),
                    m('td', row.parsedAs),
                    m('td', row.note),
                  ]))),
              ]),
              caveatShown(metadata, 'chrestomathy') ? null : m('p.estate-view__hint', reading.caveat),
              m('button.estate-view__draw', {
                onclick: () => void ctx
                  .plotWith(() => ctx.actions.plot.drawChrestomathy())
                  .then(() => ctx.focusDockPanel('graph')),
              }, 'draw the construct'),
            ])
          : null,
      ]);
    },
  };
}
