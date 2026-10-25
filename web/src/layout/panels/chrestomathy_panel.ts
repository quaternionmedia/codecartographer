/**
 * Chrestomathy Panel — one construct, set beside itself across languages.
 *
 * A printed chrestomathy taught a language by placing passages side by side;
 * this one places a construct — a record, a sum type, an interrupt handler, a
 * volatile access — in each language the server reads it in: C, Rust, Python,
 * assembly and the linker script, every language `constructs.yaml` lists —
 * with the tokens each spells it with, the parser kinds that realise it and
 * the abstraction layer each token sits on.
 *
 * THE ROW WITH NOTHING IN IT IS THE LESSON. Rust has no `volatile`; C has no
 * method. A language with no spelling is sent as a row with its note, or with
 * one saying the vocabulary records none, and stays one: `chrestomathy_rows.ts`
 * drops no row it is sent, under test against the server's own rows.
 *
 * Controls, not a canvas: "draw" puts the construct on the one canvas with its
 * tokens coloured by layer, and the legend names the layers.
 *
 * **WHATEVER IS ON THE CANVAS IS READ HERE.** A code map, a crate graph, a
 * linker script -- any graph a panel or a parse draws -- is read as the
 * constructs its nodes are and the languages that write them ("On the
 * canvas"), each a way into the table below and back onto the graph. Read
 * again whenever a new graph is drawn, so the chrestomathy is never of a
 * picture that has gone.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance, caveatShown } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import { censusGaps, censusLines, chrestomathyRows, shownSentence } from '../../features/cartography/chrestomathy_rows';
import { vocabularyShown } from '../../features/cartography/cartography_actions';
import type { Draw } from '../../features/cartography/cartography_actions';
import '../../features/estate/estate.css';

export function createChrestomathyPanel(ctx: LayoutContext): m.Component {
  const plot = ctx.actions.plot.cartography;
  let asked = false;
  let readGraph: unknown;
  let shown = '';

  const ask = () => {
    asked = true;
    void Promise.all([
      plot.loadConstructIndex(),
      plot.loadChrestomathy(ctx.appState.state.constructChosen),
    ]).catch(() => { asked = false; });
  };
  // Remembered for a relayout as it was asked for; the canvas comes forward
  // only when a graph reached it, never to show a cleared one over the problem.
  const draw = (action: Draw) => {
    void ctx.plotWith(action).then((drawn) => { if (drawn) ctx.focusDockPanel('graph'); });
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

      // A new graph on the canvas is read again; the construct's own drawing
      // is the vocabulary, not code, and is not read -- and either way the
      // census of the graph before it is gone (`readCanvas`).
      if (state.graphData !== readGraph) {
        readGraph = state.graphData;
        shown = '';
        void plot.readCanvas(state.graphData, () => ctx.canvasNodes());
      }
      const census = ctx.appState.state.chrestomathyCensus;
      const lines = census ? censusLines(census) : [];
      const drawingTheVocabulary = metadata?.kind === 'chrestomathy';

      return m('div.gl-panel.gl-panel--controls.gl-panel--chrestomathy', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'chrestomathy',
              // Repeats what failed: the reading, or the draw as it was asked for.
              onRetry: () => {
                const again = plot.chrestomathyRetry();
                ctx.appState.update({ chrestomathyProblem: null });
                if (again?.op === 'draw') draw(again.run);
                else if (again) void again.run();
                else ask();
              },
            })
          : null,

        m(Provenance, { metadata, prefix: 'chrestomathy', kind: 'chrestomathy' }),

        m('div.estate-view__section.chrestomathy__canvas', [
          m('h4.estate-view__heading', 'On the canvas'),
          census
            ? [
                lines.length
                  ? m('table.cartography__table.cartography__census', [
                      m('thead', m('tr', [m('th', 'is'), m('th', 'written in'), m('th', 'nodes'), m('th', '')])),
                      m('tbody', lines.map((line) =>
                        m('tr', {
                          'data-construct': line.id,
                          class: [line.shared ? 'is-shared' : '', line.facet ? 'is-facet' : '',
                                  line.id === state.constructChosen ? 'is-chosen' : ''].join(' '),
                        }, [
                          m('td', m('button.cartography__link', {
                            title: 'set it beside every language that writes it',
                            onclick: () => void plot.loadChrestomathy(line.id),
                          }, line.name)),
                          m('td', line.spread),
                          m('td', String(line.count)),
                          m('td', m('button.cartography__show', {
                            title: 'frame these nodes, and select them for the radial menu',
                            onclick: () => {
                              shown = shownSentence(ctx.showOnCanvas(line.ids), line);
                            },
                          }, 'show')),
                        ]))),
                    ])
                  : m('p.estate-view__hint', 'nothing on the canvas is a construct the vocabulary names'),
                shown ? m('p.estate-view__hint.chrestomathy__shown', shown) : null,
                censusGaps(census).map((gap) => m('p.estate-view__hint.chrestomathy__gap', gap)),
                m('p.estate-view__hint', census.caveat),
              ]
            : state.censusProblem
              ? m('p.estate-view__hint', `${state.censusProblem.problem} — ${state.censusProblem.remedy}`)
              : drawingTheVocabulary
                ? m('p.estate-view__hint', 'the canvas shows a construct drawn from the vocabulary, not code; '
                    + 'draw a code map, a crate graph or a linker script, and it is read here')
                : m('p.estate-view__pending', state.graphData
                    ? 'reading the canvas…'
                    : 'draw a code map, a crate graph or a linker script, and it is read here as the constructs it holds'),
        ]),

        m('div.estate-view__section', [
          m('h4.estate-view__heading', 'Construct'),
          vocabularyShown(state) === 'list' && index
            ? m('select.cartography__select', {
                value: state.constructChosen,
                onchange: (e: Event) =>
                  void plot.loadChrestomathy((e.target as HTMLSelectElement).value),
              }, [
                m('optgroup', { label: 'what a thing is' },
                  constructs.map((c) => m('option', { value: c.id }, `${c.name} — ${c.id}`))),
                m('optgroup', { label: 'what a thing can also be' },
                  facets.map((c) => m('option', { value: c.id }, `${c.name} — ${c.id}`))),
              ])
            : vocabularyShown(state) === 'problem' && state.constructIndexProblem
              ? m(ProblemView, {
                  problem: state.constructIndexProblem,
                  prefix: 'chrestomathy',
                  note: 'No construct to choose until the vocabulary is read.',
                  onRetry: () => void plot.loadConstructIndex(),
                })
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
              caveatShown(metadata, 'chrestomathy', reading.caveat) ? null : m('p.estate-view__hint', reading.caveat),
              m('button.estate-view__draw', {
                onclick: () => {
                  const action = plot.chrestomathyDraw();
                  if (action) draw(action);
                },
              }, 'draw the construct'),
            ])
          : null,
      ]);
    },
  };
}
