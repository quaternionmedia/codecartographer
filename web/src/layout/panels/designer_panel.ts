/**
 * Designer Panel — every shape of work the harness declares, and which could run.
 *
 * Controls, not a canvas, and read-only. It shows what `/designer/data`
 * returned: which harness answered, what the harness has, and one row per
 * shape with its status, the marks the plane states, why, each need, whether
 * the harness says it could run now, and its options. Below the rows: where
 * the harness's declarations and registrations differ, the acts that are a
 * person's, and the vocabulary the harness uses. No element here composes,
 * saves or runs a shape. Each declared shape's row links to its drawing in
 * the Graph panel and to the Compose panel started from that kind, and the
 * address the declarations were read from is a link to the harness.
 *
 * A status and a need key are the harness's words and are shown as written.
 * A mark is shown only when the plane states it.
 *
 * Its button draws the shapes against the needs they state in the Graph
 * panel, through the path every other plot takes.
 *
 * The reading is asked for once when the panel opens and again on its
 * button. A declaration does not change while a harness runs, so nothing
 * here asks on an interval.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import { whenShown } from '../../features/estate/run_state';
import { instanceShown } from '../../features/estate/interactions';
import {
  couldRunShown, declaredRunShown, driftShown, haveShown, marksShown, optionShown, readingShown, runnableAttr,
  statusShown,
} from '../../features/estate/designer';
import type { Declared, Need, OptionRow, ShapeRow } from '../../features/estate/designer';
import '../../features/estate/estate.css';
import './designer_panel.css';

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

function needShown(need: Need, unmet: boolean): m.Children {
  return m('li.designer__need', { 'data-need': text(need.key), 'data-unmet': unmet ? 'yes' : 'no' }, [
    m('code.designer__need-key', text(need.key)),
    unmet ? m('span.designer__need-unmet', ' unmet') : null,
    need.because ? m('span.designer__need-because', ` — ${text(need.because)}`) : null,
    need.supplied_by
      ? m('span.designer__need-supplied', [' Supplied by: ', text(need.supplied_by)])
      : null,
  ]);
}

/** What the plane states for a shape or for one of its options. */
function declaredShown(declared: Declared, unmet: Set<string>): m.Children {
  const marks = marksShown(declared);
  return [
    marks.length
      ? m('p.estate__role.designer__marks', marks.map((mark) =>
          m('span.estate-view__rung.designer__mark', { 'data-mark': mark }, mark)))
      : null,
    declaredRunShown(declared)
      ? m('p.estate__role.designer__declared-run', declaredRunShown(declared))
      : null,
    declared.why ? m('p.estate__detail.designer__why', text(declared.why)) : null,
    (declared.needs ?? []).length
      ? m('ul.designer__needs', (declared.needs ?? []).map((need) => needShown(need, unmet.has(text(need.key)))))
      : m('p.estate__role.designer__no-needs', 'states no need'),
  ];
}

function optionRow(option: OptionRow): m.Children {
  return m('div.designer__option', { 'data-setting': text(option.setting) }, [
    m('p.designer__option-name', [
      m('code', optionShown(option)),
      option.declared.status
        ? m('span.estate-view__rung.designer__status', { 'data-status': text(option.declared.status) },
            text(option.declared.status))
        : null,
    ]),
    declaredShown(option.declared, new Set()),
  ]);
}

/** Where a shape's row leads: its drawing, and a design of that kind. */
function shapeLinks(ctx: LayoutContext, name: string): m.Children {
  const drawIt = () => {
    ctx.appState.update({ topologyKind: name, topologySubject: '' });
    void ctx
      .plotWith(() => ctx.actions.plot.loadTopology({ kind: name }))
      // A shape the harness will not draw says why in the Topology panel.
      .then((drew) => { if (drew) ctx.focusDockPanel('graph'); else ctx.openPanel('topology-panel'); })
      .catch(() => undefined);
  };
  const composeIt = () => {
    ctx.appState.update({ composeKind: name });
    ctx.openPanel('compose-panel');
  };
  return m('p.estate__where.designer__links', [
    m('button.designer__link.designer__to-drawing', { type: 'button', onclick: drawIt }, 'draw this shape'),
    ' · ',
    m('button.designer__link.designer__to-compose', { type: 'button', onclick: composeIt }, 'compose one'),
  ]);
}

function shapeRow(ctx: LayoutContext, row: ShapeRow, read: boolean): m.Children {
  const status = statusShown(row);
  const could = couldRunShown(row, read);
  const unmet = new Set(read ? (row.could_run?.unmet ?? []).map((need) => text(need.key)) : []);
  return m('div.estate__row.designer__shape', {
    'data-shape': row.name,
    'data-status': status,
    'data-runnable': runnableAttr(row, read),
  }, [
    m('span.estate__dot'),
    m('span.estate__name', row.name),
    m('span.estate__actions',
      status ? m('span.estate-view__rung.designer__status', { 'data-status': status }, status) : null),
    could ? m('p.estate__role.designer__could-run', could) : null,
    row.missing ? m('p.estate__problem.designer__missing', row.missing) : null,
    row.declared ? declaredShown(row.declared, unmet) : null,
    row.declared ? shapeLinks(ctx, row.name) : null,
    row.options.length
      ? m('div.designer__options', [
          m('p.estate__role.designer__options-heading', 'under a setting'),
          row.options.map(optionRow),
        ])
      : null,
  ]);
}

function listed(values: unknown[], empty: string, name: string): m.Children {
  return values.length
    ? m(`div.estate-view__rungs.designer__${name}`, values.map((value) =>
        m('span.estate-view__rung', { [`data-${name}`]: text(value) }, text(value))))
    : m('p.estate-view__hint', empty);
}

export function createDesignerPanel(ctx: LayoutContext): m.Component {
  /** When the reading on screen arrived, by this window's clock. */
  let readAt: Date | null = null;

  const ask = () => {
    void ctx.actions.plot
      .loadDesignerReading()
      .then(() => {
        if (ctx.appState.state.designerReading) readAt = new Date();
        m.redraw();
      })
      .catch(() => undefined);
  };

  const draw = () => {
    void ctx.plotWith(() => ctx.actions.plot.drawDesigner())
      .then((drew) => { if (drew) ctx.focusDockPanel('graph'); });
  };

  return {
    oninit: ask,

    view: () => {
      const state = ctx.appState.state;
      const reading = state.designerReading;
      const problem = state.designerProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;

      return m('div.gl-panel.gl-panel--controls.gl-panel--designer', [
        problem
          ? m(ProblemView, {
              problem,
              prefix: 'designer',
              note: 'Nothing is listed. An empty list would look like a harness that declares no shape.',
              onRetry: () => {
                ctx.appState.update({ designerProblem: null });
                ask();
              },
            })
          : null,

        reading === null && !problem
          ? m('p.estate-view__pending', 'asking the harness…')
          : null,

        // Only when the canvas holds this seam's graph.
        m(Provenance, { metadata, prefix: 'designer-graph', kind: 'designer' }),

        reading
          ? [
              m('div.estate-view__section', { 'data-designer': 'graph' }, [
                m('button.estate-view__draw.designer__draw', { onclick: draw }, 'draw shapes against needs'),
                m('button.estate__refresh.designer__again', { onclick: ask }, 'read again'),
                m('p.estate-view__hint.designer__read',
                  `read ${readAt ? readAt.toLocaleTimeString() : 'just now'}; a declaration is read again only when asked`),
              ]),

              readingShown(reading.reading).map((said) => m('p.estate-view__hint.designer__caveat', said)),

              m('div.estate-view__section', { 'data-designer': 'instance' }, [
                m('h4.estate-view__heading', 'Which harness'),
                m('div.estate__rows',
                  m('div.estate__row.designer__instance', {
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

              m('div.estate-view__section', { 'data-designer': 'have' }, [
                m('h4.estate-view__heading', 'What the harness has'),
                reading.could_run.read
                  ? m('p.estate-view__hint.designer__have', haveShown(reading.have) || 'the harness states nothing it has')
                  : m('p.estate__problem.designer__could-run-unread', [
                      `which shapes could run was not read: ${reading.could_run.problem}`,
                      reading.could_run.remedy ? ` — ${reading.could_run.remedy}` : '',
                    ]),
                reading.never_supplied?.key
                  ? m('p.estate-view__hint.designer__never', [
                      m('code', text(reading.never_supplied.key)),
                      ` is never supplied: ${text(reading.never_supplied.because)}`,
                    ])
                  : null,
              ]),

              m('div.estate-view__section', { 'data-designer': 'shapes' }, [
                m('h4.estate-view__heading', 'Shapes'),
                reading.shapes.length === 0
                  ? m('p.estate-view__hint', 'the harness declares no shape')
                  : null,
                m('p.estate__where.designer__where', ['read from ', m('a.designer__link', {
                  href: reading.where, target: '_blank', rel: 'noopener',
                }, reading.where)]),
                m('div.estate__rows', reading.shapes.map((row) => shapeRow(ctx, row, reading.could_run.read))),
              ]),

              m('div.estate-view__section', { 'data-designer': 'drift' }, [
                m('h4.estate-view__heading', 'Declared and registered'),
                driftShown(reading.drift).length === 0
                  ? m('p.estate-view__hint', 'the harness states no comparison of the two')
                  : null,
                driftShown(reading.drift).map((found) =>
                  m('div.designer__drift', { 'data-drift': found.name }, [
                    m('p.estate__role', m('code', found.name)),
                    listed(found.items, 'empty', 'drift-item'),
                  ])),
              ]),

              m('div.estate-view__section', { 'data-designer': 'attested' }, [
                m('h4.estate-view__heading', 'A person\'s acts'),
                reading.attested.length
                  ? m('ul.designer__attested', reading.attested.map((act) => m('li', text(act))))
                  : m('p.estate-view__hint', 'the harness names none'),
              ]),

              m('div.estate-view__section', { 'data-designer': 'vocabulary' }, [
                m('h4.estate-view__heading', 'The harness\'s words'),
                m('p.estate__role', 'statuses'),
                listed(reading.statuses, 'none stated', 'status-word'),
                m('p.estate__role', 'needs'),
                listed(reading.needs, 'none stated', 'need-word'),
              ]),
            ]
          : null,
      ]);
    },
  };
}
