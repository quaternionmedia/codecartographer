/**
 * Show Panel — every family and project the corpus names, as showgraphs.
 *
 * Controls, not a canvas: the graph draws in the Graph panel through the same
 * path every other plot takes. This panel lists what the server read from the
 * corpus -- each top-level family with the families directly within it, their
 * hues, and each public project -- and opens each one. A project opens three ways: its place in the estate,
 * its code map, and its system diagram where it declares one.
 *
 * THE VOCABULARY IS THE CORPUS'S. Family names, what each drives, which sits
 * within which, and the hues are the server's reading of `families.json` and
 * `ci/palette.py`; nothing here names a family.
 *
 * A VIEW THAT CANNOT BE DRAWN IS OFFERED DISABLED, WITH ITS REASON. A project
 * with no clone beside this one has no system view here, and the button says
 * so rather than disappearing or drawing something else.
 *
 * Every row goes through `ctx.openShow`, which also writes the page's address,
 * so the location bar can be copied to reopen exactly what is drawn. Opened
 * with nothing on the canvas and nothing being drawn, the panel draws every
 * family at once: the default showgraph is the whole estate, and a family or a
 * project is a step into it.
 *
 * **WHERE YOU ARE COMES FIRST.** The panel opens on what is drawn: the trail
 * from every family down to it, each step a link back, a project's three
 * views beside it, and the key to the edges. What the drawing can and cannot
 * say follows, folded, and the lists of everything else after that. The
 * caveat once led, and the controls a reader came for sat below the fold.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import type { ShowAddress, ShowView } from '../../features/show/show_address';
import { VIEWS, VIEW_NAMES, crumbLabel, formatShow, trail } from '../../features/show/show_address';
import type { ShowFamilyRow, ShowProjectRow } from '../../features/show/show_service';
import { pressable } from '../../components/codecarto/control_panel/pressable';
import '../../features/estate/estate.css';
import './show_panel.css';

const VIEW_LABEL: Record<ShowView, string> = {
  estate: VIEW_NAMES.project.estate.label,
  code: VIEW_NAMES.project.code.label,
  system: VIEW_NAMES.project.system.label,
};

function same(a: ShowAddress | null, kind: string, name: string): boolean {
  return !!a && a.kind === kind && a.name === name;
}

/** The folded caveat's one line: what the drawing could not settle, counted. */
function aboutSummary(metadata: Record<string, unknown>): string {
  const count = (key: string) => (Array.isArray(metadata[key]) ? (metadata[key] as unknown[]).length : 0);
  const undeclared = count('undeclared');
  const unread = count('unread');
  const parts = [
    undeclared ? `${undeclared} seam${undeclared === 1 ? '' : 's'} nobody has declared` : '',
    unread ? `${unread} member${unread === 1 ? '' : 's'} not measured` : '',
  ].filter(Boolean);
  return parts.length ? `What this drawing can say — ${parts.join(', ')}` : 'What this drawing can say';
}

export function createShowPanel(ctx: LayoutContext): m.Component {
  let asked = false;
  let filter = '';

  const ask = () => {
    asked = true;
    void ctx.actions.plot.loadShowSubjects().then(() => {
      // THE DEFAULT IS EVERY FAMILY AT ONCE. A panel opened onto an empty
      // canvas draws the whole estate; one opened over a graph somebody drew
      // leaves it, and **draw every family** is the first thing it offers.
      // A graph still being drawn is one: a stream records its graph only
      // when it ends, and the index was drawn over it.
      const state = ctx.appState.state;
      if (state.showSubjects && !state.showAddress && !state.graphData && !ctx.panelState.isLoading) {
        void ctx.openShow({ kind: 'index', name: '', view: 'estate' }, 'replace');
      }
    }).catch(() => {
      asked = false;
    });
  };

  const open = (address: ShowAddress) => void ctx.openShow(address);

  /**
   * A family row, and a project's name, are pressed as a button is: a place
   * in the tab order, the button role, and Enter and Space (`pressable`, as
   * the Files panel's rows are). They were a `div` and a `span` with only a
   * click handler, reached by a pointer and never from the keyboard. Neither
   * can be a `<button>`: a row holds paragraphs, which a button may not.
   */
  const pressed = (address: ShowAddress) => {
    const press = () => open(address);
    return { ...pressable(press), onclick: press };
  };

  const familyRow = (family: ShowFamilyRow, depth: number, current: ShowAddress | null) =>
    m('div.estate__row.is-live.show__family', {
      'data-family': family.name,
      class: same(current, 'family', family.name) ? 'is-current' : '',
      style: { '--show-hue': family.hue ?? 'var(--c-font-muted, #888)', '--show-indent': `${depth}` },
      ...pressed({ kind: 'family', name: family.name, view: 'estate' }),
      title: `draw the ${family.name} family`,
    }, [
      m('span.estate__dot.show__hue'),
      m('span.estate__name', family.name),
      m('span.estate__actions', m('span.estate-view__rung',
        family.all_members === family.members
          ? `${family.members}`
          : `${family.members} own · ${family.all_members} in all`)),
      m('p.estate__role', family.drives),
    ]);

  const projectRow = (project: ShowProjectRow, current: ShowAddress | null, hueOf: (f: string) => string | null) => {
    const selected = same(current, 'project', project.name);
    return m('div.estate__row.is-live.show__project', {
      'data-project': project.name,
      class: selected ? 'is-current' : '',
      style: { '--show-hue': hueOf(project.families[0] ?? '') ?? 'var(--c-font-muted, #888)' },
    }, [
      m('span.estate__dot.show__hue'),
      m('span.estate__name', {
        ...pressed({ kind: 'project', name: project.name, view: 'estate' }),
        title: `draw ${project.name}'s place in the estate`,
      }, project.name),
      m('span.estate__actions', m('span.estate-view__rung',
        project.governed === null ? 'governance unknown' : project.governed ? 'governed' : 'not adopted')),
      m('p.estate__role', [
        project.families.length ? project.families.join(' · ') : m('i', 'family unstated'),
        project.phase ? ` — ${project.phase}` : '',
      ]),
      project.description ? m('p.estate__detail', project.description) : null,
    ]);
  };

  /** A project's three views, each disabled with its reason when it cannot be drawn here. */
  const viewSwitch = (current: ShowAddress) => {
    const views = ctx.appState.state.showViews;
    return [
      m('div.show__views', VIEWS.map((view) => {
        const state = views ? views[view] : null;
        const disabled = !state || !state.available;
        return m('button.estate-view__draw.show__view', {
          'data-view': view,
          disabled,
          class: current.view === view ? 'is-current' : '',
          // Which of the three is drawn, said as well as shown.
          'aria-pressed': current.view === view ? 'true' : 'false',
          title: disabled ? (state?.problem ?? 'asking which views can be drawn…') : VIEW_NAMES.project[view].title,
          onclick: () => open({ kind: 'project', name: current.name, view }),
        }, VIEW_LABEL[view]);
      })),
      views
        ? VIEWS.filter((v) => !views[v].available && views[v].problem)
            .map((v) => m('p.estate__where', `${VIEW_LABEL[v]}: ${views[v].problem}`))
        : null,
    ];
  };

  /** Every family alone, or with each project's code in it: the whole corpus, named or not. */
  const indexViews = VIEW_NAMES.index;
  const indexSwitch = (current: ShowAddress) =>
    m('div.show__views', (['estate', 'code', 'full', 'imports'] as const).map((view) =>
      m('button.estate-view__draw.show__view', {
        'data-view': view,
        class: current.view === view ? 'is-current' : '',
        'aria-pressed': current.view === view ? 'true' : 'false',
        title: indexViews[view].title,
        onclick: () => open({ kind: 'index', name: '', view }),
      }, indexViews[view].label)));

  /** A family alone, with each of its projects' code in it, or with what they import in common. */
  const familyViews = VIEW_NAMES.family;
  const familySwitch = (current: ShowAddress) =>
    m('div.show__views', (['estate', 'code', 'imports'] as const).map((view) =>
      m('button.estate-view__draw.show__view', {
        'data-view': view,
        class: current.view === view ? 'is-current' : '',
        'aria-pressed': current.view === view ? 'true' : 'false',
        title: familyViews[view].title,
        onclick: () => open({ kind: 'family', name: current.name, view }),
      }, familyViews[view].label)));

  /** The way from every family to what is drawn, each step a link back to it. */
  const trailView = (current: ShowAddress, subjects: Parameters<typeof trail>[1]) => {
    const levels = trail(current, subjects);
    return m('nav.show__trail', { 'aria-label': 'where this drawing is' }, levels.map((level, i) => [
      i ? m('span.show__sep', '›') : null,
      level.map((step, j) => [
        j ? m('span.show__sep', '·') : null,
        i === levels.length - 1
          ? m('span.show__crumb.is-current', { 'aria-current': 'page' }, crumbLabel(step))
          : m('a.show__crumb', {
              href: formatShow(step),
              onclick: (e: MouseEvent) => {
                // A plain click opens it here; a modified one is the browser's.
                if (e.button || e.ctrlKey || e.metaKey || e.shiftKey) return;
                e.preventDefault();
                open(step);
              },
            }, crumbLabel(step)),
      ]),
    ]));
  };

  return {
    oninit: () => {
      if (!asked) ask();
    },

    view: () => {
      const state = ctx.appState.state;
      const subjects = state.showSubjects;
      const problem = state.showProblem;
      const current = state.showAddress;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;
      const bases = (metadata?.kind === 'show' ? metadata.bases : null) as
        Record<string, { style: string; color: string }> | null;

      const byName = new Map((subjects?.families ?? []).map((f) => [f.name, f]));
      const hueOf = (name: string) => byName.get(name)?.hue ?? null;
      const top = (subjects?.families ?? []).filter((f) => !f.within || !byName.has(f.within));
      const needle = filter.trim().toLowerCase();
      const projects = (subjects?.projects ?? []).filter((p) =>
        !needle || p.name.toLowerCase().includes(needle)
        || p.families.some((f) => f.includes(needle)));

      return m('div.gl-panel.gl-panel--controls.gl-panel--show', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'show',
              onRetry: () => {
                ctx.appState.update({ showProblem: null });
                if (!subjects) ask();
                else if (current) void ctx.openShow(current);
              },
            })
          : null,

        current
          ? m('div.show__now', { 'data-show': formatShow(current) }, [
              trailView(current, subjects),
              current.kind === 'project' ? viewSwitch(current)
                : current.kind === 'index' ? indexSwitch(current) : familySwitch(current),
              bases
                ? m('div.show__legend', Object.entries(bases).map(([basis, look]) =>
                    m('span.show__basis', { 'data-basis': basis }, [
                      m('span.show__stroke', { style: { borderTopColor: look.color, borderTopStyle: look.style } }),
                      basis,
                    ])))
                : null,
              current.view === 'estate'
                ? m('p.estate-view__hint.show__how',
                    'Double-click a family or a project to open it; Back returns.')
                : null,
            ])
          : null,

        metadata?.kind === 'show'
          ? m('details.show__about', [
              m('summary', aboutSummary(metadata as unknown as Record<string, unknown>)),
              m(Provenance, { metadata, prefix: 'show', kind: 'show' }),
            ])
          : m(Provenance, { metadata, prefix: 'show', kind: 'show' }),

        subjects === null && !problem
          ? m('p.estate-view__pending', 'reading the corpus…')
          : null,

        subjects
          ? [
              m('div.estate-view__section', [
                m('h4.estate-view__heading', 'The estate'),
                m('p.estate__where', [
                  `corpus ${subjects.provenance.commit ?? 'at an unknown commit'}`,
                  `, schema ${subjects.provenance.schema}`,
                  subjects.provenance.overridden ? ', read from CODECARTO_CORPUS rather than the pin' : ', the governance pin',
                ]),
                m('button.estate-view__draw', {
                  class: current?.kind === 'index' ? 'is-current' : '',
                  onclick: () => open({ kind: 'index', name: '', view: 'estate' }),
                }, 'draw every family'),
                subjects.unstated
                  ? m('p.estate-view__hint', `${subjects.unstated} rostered repositor${subjects.unstated === 1 ? 'y claims' : 'ies claim'} no family. That is unstated, not none.`)
                  : null,
              ]),

              m('div.estate-view__section', [
                m('h4.estate-view__heading', 'Families'),
                m('div.estate__rows', top.flatMap((family) => [
                  familyRow(family, 0, current),
                  ...family.subfamilies
                    .map((name) => byName.get(name))
                    .filter((f): f is ShowFamilyRow => !!f)
                    .map((sub) => familyRow(sub, 1, current)),
                ])),
              ]),

              m('div.estate-view__section', [
                m('h4.estate-view__heading', 'Projects'),
                m('input.show__filter', {
                  type: 'search',
                  // A placeholder goes as the reader types, and is no label.
                  'aria-label': 'filter projects by name or family',
                  placeholder: 'filter by name or family',
                  value: filter,
                  oninput: (e: Event) => { filter = (e.target as HTMLInputElement).value; },
                }),
                m('div.estate__rows', projects.map((p) => projectRow(p, current, hueOf))),
                subjects.private
                  ? m('p.estate-view__hint', `${subjects.private} private member${subjects.private === 1 ? ' is' : 's are'} counted in the families and not listed.`)
                  : null,
              ]),

              subjects.notes.length
                ? m('div.estate-view__section', subjects.notes.map((note) => m('p.estate__where', note)))
                : null,
            ]
          : null,
      ]);
    },
  };
}
