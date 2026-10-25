/**
 * Cargo Panel — a Rust workspace's crates, targets and dependencies, and what
 * the last recorded build said about them.
 *
 * Controls, not a canvas: the graph draws in the Graph panel through the path
 * every plot takes. This panel names a workspace, says which engine the server
 * read it with and which recorded documents it found, and offers to draw it.
 *
 * THE WINDOW NEVER RUNS CARGO. It reads manifests and the documents
 * `codecarto cargo record` writes under `target/codecarto/`; a document that
 * is absent or older than the source says so here, beside what it would have
 * added, rather than being quietly left out of the picture.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance, caveatShown } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import type { Draw } from '../../features/cartography/cartography_actions';
import '../../features/estate/estate.css';

export function createCargoPanel(ctx: LayoutContext): m.Component {
  const plot = ctx.actions.plot.cartography;
  let draft = ctx.appState.state.cargoPath;
  let features = false;
  let transitive = false;

  const read = () => {
    if (!draft.trim()) return;
    void plot.loadCargoReading(draft.trim());
  };
  // Remembered for a relayout as it was asked for; the canvas comes forward
  // only when a graph reached it, never to show a cleared one over the problem.
  const draw = (action: Draw) => {
    void ctx.plotWith(action).then((drawn) => { if (drawn) ctx.focusDockPanel('graph'); });
  };

  return {
    view: () => {
      const state = ctx.appState.state;
      const reading = state.cargoReading;
      const problem = state.cargoProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;
      const members = reading?.packages.filter((p) => p.member) ?? [];

      return m('div.gl-panel.gl-panel--controls.gl-panel--cargo', [
        m('div.estate-view__section', [
          m('h4.estate-view__heading', 'Workspace'),
          m('input.cartography__input[type=text]', {
            placeholder: 'a directory holding Cargo.toml',
            value: draft,
            oninput: (e: Event) => { draft = (e.target as HTMLInputElement).value; },
            onkeydown: (e: KeyboardEvent) => { if (e.key === 'Enter') read(); },
          }),
          m('button.estate-view__draw', { onclick: read }, 'read'),
        ]),

        problem
          ? m(ProblemView, {
              problem,
              prefix: 'cargo',
              // Repeats what failed: the read, or the draw as it was asked for.
              onRetry: () => {
                const again = plot.cargoRetry();
                ctx.appState.update({ cargoProblem: null });
                if (again?.op === 'draw') draw(again.run);
                else if (again) void again.run();
                else read();
              },
            })
          : null,

        m(Provenance, { metadata, prefix: 'cargo', kind: 'cargo' }),

        reading
          ? m('div.estate-view__section', [
              m('h4.estate-view__heading', `Read from ${reading.engine}`),
              m('div.estate__rows', members.map((pkg) =>
                m('div.estate__row.is-live', { 'data-crate': pkg.name }, [
                  m('span.estate__dot'),
                  m('span.estate__name', `${pkg.name} ${pkg.version}`),
                  m('span.estate__actions', [
                    pkg.no_std ? m('span.estate-view__rung', pkg.no_std === 'yes' ? 'no_std' : 'no_std (cfg)') : null,
                    pkg.links ? m('span.estate-view__rung', `links ${pkg.links}`) : null,
                  ]),
                  m('p.estate__role', pkg.targets.map((t) => `${t.kinds[0]} ${t.name}`).join(' · ')),
                  m('p.estate__where', `${pkg.dependencies.length} dependencies — ${pkg.manifest}`),
                ]))),
              m('div.estate__rows', reading.documents.map((doc) =>
                m(`div.estate__row.${doc.used && !doc.stale ? 'is-live' : 'is-down'}`, [
                  m('span.estate__dot'),
                  m('span.estate__name', doc.name),
                  m('span.estate__actions', m('span.estate-view__rung',
                    !doc.present ? 'absent' : doc.used ? (doc.stale ? 'used, stale' : 'used') : 'not used')),
                  doc.generated_at ? m('p.estate__where', `written ${doc.generated_at}`) : null,
                  doc.problem ? m('p.estate__detail', doc.problem) : null,
                ]))),
              reading.firmware.build_targets.length
                ? m('p.estate__where', [
                    'builds for ', m('code', reading.firmware.build_targets.join(', ')),
                    ...Object.entries(reading.firmware.runners).map(([triple, runner]) =>
                      m('span', ['; runner for ', triple, ': ', m('code', runner), ' (shown, never run)'])),
                  ])
                : null,
              reading.notes.map((note) => m('p.estate-view__hint', note)),
              caveatShown(metadata, 'cargo') ? null : m('p.estate-view__hint', reading.caveat),
              m('label.cartography__options', [
                m('input[type=checkbox]', {
                  checked: features,
                  onchange: (e: Event) => { features = (e.target as HTMLInputElement).checked; },
                }),
                'features',
                m('input[type=checkbox]', {
                  checked: transitive,
                  onchange: (e: Event) => { transitive = (e.target as HTMLInputElement).checked; },
                }),
                'locked dependencies of dependencies',
              ]),
              m('button.estate-view__draw', {
                onclick: () => draw(plot.cargoDraw({ features, transitive })),
              }, 'draw the workspace'),
            ])
          : !problem
            ? m('p.estate-view__hint',
                'Name a workspace and read it. Run `codecarto cargo record <path>` there first '
                + 'to add cargo’s own resolution and the last check’s diagnostics.')
            : null,
      ]);
    },
  };
}
