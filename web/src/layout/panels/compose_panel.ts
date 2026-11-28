/**
 * Compose Panel — a design of collaboration, composed here and saved to the harness.
 *
 * Controls, not a canvas. A person chooses a kind, names the design, fills
 * the form the harness's own schema for that kind gives, and ticks the saved
 * components it uses and the saved designs it is composed of. *save design*
 * sends it once through this window's API; the harness validates and saves
 * it, and the panel prints the harness's row with its verdict, or its
 * refusal with each message beside the field it is about.
 *
 * Each reference ticked is drawn at once: the Graph panel shows the draft
 * joined to what it references, with every saved design and its own
 * references around it, through the path every other plot takes.
 *
 * Below the form, every saved design of the project is listed with what the
 * harness says of it, and links: to the harness's own row for it, to its
 * kind in the Designer panel, and into the draft as something composed.
 *
 * Saving is offered only where this window relays it: to a person at the
 * machine the harness runs on. Anywhere else the panel says so and offers
 * the reading alone. Nothing here changes, deletes or runs a design.
 */

import m from 'mithril';

import type { LayoutContext } from '../layout_context';
import { ProblemView } from '../../features/estate/problem_view';
import { Provenance } from '../../features/estate/provenance';
import type { EstateMetadata } from '../../features/estate/provenance';
import { EstateService } from '../../features/estate/estate_service';
import { isProblem } from '../../features/estate/seam_client';
import type { SeamProblem } from '../../features/estate/seam_client';
import {
  compositionQuery, configOf, designLink, errorsElsewhere, errorsFor, fieldsOf, initialValues, referencesOf, savable,
  ticked, toggled, verdictShown,
} from '../../features/estate/compose';
import type { Draft, Field, SaveOutcome, Values } from '../../features/estate/compose';
import '../../features/estate/estate.css';
import './compose_panel.css';

interface Held {
  project: string | null;
  designs: Array<Record<string, unknown>>;
  components: Array<Record<string, unknown>>;
  components_read: { read: boolean; problem: string; remedy: string; where: string };
  saving: { available: boolean; problem: string; remedy: string };
  where: string;
}

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

export function createComposePanel(ctx: LayoutContext): m.Component {
  const draft: Draft = { name: '', kind: '', description: '', project: '' };
  let held: Held | null = null;
  let heldProblem: SeamProblem | null = null;
  let fields: Field[] = [];
  let values: Values = {};
  let schemaProblem: SeamProblem | null = null;
  let schemaFor = '';
  let saving = false;
  let outcome: SaveOutcome | null = null;

  const url = () => ctx.appState.api.designer;

  const readHeld = (): Promise<void> =>
    EstateService.composeDesigns(url(), draft.project).then((found) => {
      if (isProblem(found)) {
        held = null;
        heldProblem = found.problem;
      } else {
        held = found.document as unknown as Held;
        heldProblem = null;
      }
      m.redraw();
    });

  const drawNow = (withDraft: boolean) => {
    void ctx
      .plotWith(() => ctx.actions.plot.drawComposition(compositionQuery(withDraft ? draft : null, values)))
      .then((drew) => { if (drew) ctx.focusDockPanel('graph'); })
      .catch(() => undefined);
  };

  const choose = (kind: string) => {
    draft.kind = kind;
    outcome = null;
    if (!kind) {
      fields = [];
      values = {};
      schemaFor = '';
      return;
    }
    void EstateService.designSchema(url(), kind).then((found) => {
      if (draft.kind !== kind) return;
      if (isProblem(found)) {
        fields = [];
        values = {};
        schemaProblem = found.problem;
      } else {
        fields = fieldsOf(found.document.json_schema);
        values = initialValues(fields);
        schemaProblem = null;
      }
      schemaFor = kind;
      m.redraw();
    });
  };

  /** A kind another panel asked this one to start from, taken once. */
  const takeAsked = () => {
    const asked = ctx.appState.state.composeKind;
    if (!asked) return;
    ctx.appState.update({ composeKind: '' });
    choose(asked);
  };

  const save = (event: Event) => {
    event.preventDefault();
    if (!savable(draft, saving)) return;
    saving = true;
    outcome = null;
    void EstateService.saveDesign(url(), {
      name: draft.name.trim(), topology_type: draft.kind, description: draft.description.trim(),
      project: draft.project.trim(), config: configOf(fields, values),
    }).then((found) => {
      saving = false;
      outcome = found;
      if (found.kind === 'saved') {
        draft.name = '';
        draft.description = '';
        values = initialValues(fields);
        void readHeld().then(() => drawNow(false));
      }
      m.redraw();
    });
  };

  const tick = (name: string, reference: string, on: boolean) => {
    values = toggled(values, name, reference, on);
    // The line is drawn as the reference is added, before anything is saved.
    drawNow(true);
  };

  const errors = () => (outcome && outcome.kind !== 'saved' ? outcome.errors : []);

  const said = (field: string): m.Children =>
    errorsFor(errors(), field).map((message) => m('p.compose__error', { 'data-field': field }, message));

  const control = (field: Field): m.Children => {
    const value = values[field.name];
    const set = (next: unknown) => { values = { ...values, [field.name]: next }; };
    const id = `compose-${field.name}`;
    if (field.kind === 'unoffered') {
      return m('p.estate-view__hint.compose__unoffered', { 'data-field': field.name },
        [m('code', field.name), ' is not offered here; the harness fills its default']);
    }
    if (field.kind === 'components' || field.kind === 'compose') {
      const offered = field.kind === 'components' ? held?.components ?? [] : held?.designs ?? [];
      const what = field.kind === 'components' ? 'component' : 'design';
      return m('fieldset.compose__references', { 'data-field': field.name }, [
        m('legend', field.kind === 'components' ? 'Uses these components' : 'Is composed of these designs'),
        offered.length === 0
          ? m('p.estate-view__hint.compose__none', `the harness holds no saved ${what} in this project`)
          : offered.map((row) => {
              const name = text(row.name);
              return m('label.compose__reference', { 'data-reference': name }, [
                m('input', {
                  type: 'checkbox',
                  checked: ticked(values, field.name).includes(name),
                  onchange: (event: Event) => tick(field.name, name, (event.target as HTMLInputElement).checked),
                }),
                ` ${name}`,
                row.topology_type ? m('span.estate-view__rung', text(row.topology_type)) : null,
              ]);
            }),
        said(`config.${field.name}`),
      ]);
    }
    const input = field.kind === 'boolean'
      ? m('input', {
          id, type: 'checkbox', checked: value === true,
          onchange: (event: Event) => set((event.target as HTMLInputElement).checked),
        })
      : field.kind === 'choice'
        ? m('select', {
            id, value: text(value),
            onchange: (event: Event) => set((event.target as HTMLSelectElement).value),
          }, [
            field.nullable || field.fallback === undefined ? m('option', { value: '' }, '') : null,
            field.choices.map((choice) => m('option', { value: choice }, choice)),
          ])
        : m('input', {
            id,
            type: field.kind === 'integer' || field.kind === 'number' ? 'number' : 'text',
            min: field.minimum, max: field.maximum,
            value: text(value),
            placeholder: field.kind === 'strings' ? 'separated by commas' : '',
            oninput: (event: Event) => set((event.target as HTMLInputElement).value),
          });
    return m('div.compose__field', { 'data-field': field.name, 'data-kind': field.kind }, [
      m('label', { for: id }, field.title),
      input,
      said(`config.${field.name}`),
    ]);
  };

  const designRow = (row: Record<string, unknown>): m.Children => {
    const name = text(row.name);
    const references = referencesOf(row);
    const composes = fields.some((field) => field.kind === 'compose');
    return m('div.estate__row.compose__design', { 'data-design': name }, [
      m('span.estate__dot'),
      m('span.estate__name', name),
      m('span.estate__actions', [
        m('span.estate-view__rung', text(row.topology_type)),
      ]),
      row.description ? m('p.estate__detail', text(row.description)) : null,
      verdictShown(row).map((sentence) => m('p.estate__role.compose__verdict', sentence)),
      references.components.length
        ? m('p.estate__role.compose__uses', `uses ${references.components.join(', ')}`)
        : null,
      references.compose.length
        ? m('p.estate__role.compose__composes', `composes ${references.compose.join(', ')}`)
        : null,
      m('p.estate__where.compose__links', [
        m('a.compose__link', { href: designLink(held?.where ?? '', name), target: '_blank', rel: 'noopener' },
          'the harness\'s row'),
        ' · ',
        m('button.compose__link.compose__to-kind', {
          type: 'button',
          onclick: () => ctx.openPanel('designer-panel'),
        }, `what ${text(row.topology_type)} needs`),
        composes
          ? [' · ', m('button.compose__link.compose__add', {
              type: 'button',
              disabled: ticked(values, 'compose').includes(name),
              onclick: () => tick('compose', name, true),
            }, 'compose the draft of this')]
          : null,
      ]),
    ]);
  };

  return {
    oninit: () => {
      void readHeld();
      if (!ctx.appState.state.designerReading) void ctx.actions.plot.loadDesignerReading();
      takeAsked();
    },
    onbeforeupdate: () => { takeAsked(); },

    view: () => {
      const state = ctx.appState.state;
      const kinds = (state.designerReading?.shapes ?? []).map((shape) => shape.name);
      const drawProblem = state.composeProblem;
      const metadata = state.graphData?.metadata as EstateMetadata | undefined;
      const able = held?.saving.available === true;
      const shownFields = ['name', 'topology_type', 'description', 'project',
        ...fields.filter((field) => field.kind !== 'unoffered').map((field) => `config.${field.name}`)];

      return m('div.gl-panel.gl-panel--controls.gl-panel--compose', [
        heldProblem
          ? m(ProblemView, {
              problem: heldProblem,
              prefix: 'compose',
              note: 'Nothing is listed. An empty list would look like a harness that holds no design.',
              onRetry: () => { heldProblem = null; void readHeld(); },
            })
          : null,
        drawProblem
          ? m(ProblemView, { problem: drawProblem, prefix: 'compose-draw' })
          : null,
        held === null && !heldProblem ? m('p.estate-view__pending', 'asking the harness…') : null,

        m(Provenance, { metadata, prefix: 'compose-graph', kind: 'composition' }),

        held
          ? [
              // `novalidate`: a value out of the schema's range is sent, and the harness says so.
              m('form.estate-view__section.compose__form', { 'data-compose': 'form', novalidate: true, onsubmit: save }, [
                m('h4.estate-view__heading', 'A design'),
                able
                  ? null
                  : m('p.estate__problem.compose__away', [
                      held.saving.problem, held.saving.remedy ? ` — ${held.saving.remedy}` : '',
                    ]),
                m('div.compose__field', { 'data-field': 'topology_type' }, [
                  m('label', { for: 'compose-kind' }, 'Kind'),
                  m('select.compose__kind', {
                    id: 'compose-kind', value: draft.kind,
                    onchange: (event: Event) => choose((event.target as HTMLSelectElement).value),
                  }, [
                    m('option', { value: '' }, 'choose a kind'),
                    // A kind another panel asked for is offered even before the list of kinds is read.
                    [...new Set([...kinds, draft.kind].filter((kind) => kind))]
                      .map((kind) => m('option', { value: kind }, kind)),
                  ]),
                  m('button.compose__link.compose__kinds', {
                    type: 'button', onclick: () => ctx.openPanel('designer-panel'),
                  }, 'what each kind needs'),
                  said('topology_type'),
                ]),
                m('div.compose__field', { 'data-field': 'name' }, [
                  m('label', { for: 'compose-name' }, 'Name'),
                  m('input.compose__name', {
                    id: 'compose-name', type: 'text', value: draft.name,
                    placeholder: 'lowercase, with hyphens; the name is its address',
                    oninput: (event: Event) => { draft.name = (event.target as HTMLInputElement).value; },
                  }),
                  said('name'),
                ]),
                m('div.compose__field', { 'data-field': 'description' }, [
                  m('label', { for: 'compose-description' }, 'Description'),
                  m('input.compose__description', {
                    id: 'compose-description', type: 'text', value: draft.description,
                    oninput: (event: Event) => { draft.description = (event.target as HTMLInputElement).value; },
                  }),
                  said('description'),
                ]),
                schemaProblem && schemaFor === draft.kind
                  ? m('p.estate__problem.compose__schema-problem',
                      [schemaProblem.problem, schemaProblem.remedy ? ` — ${schemaProblem.remedy}` : ''])
                  : null,
                fields.map(control),
                m('div.compose__actions', [
                  m('button.estate-view__draw.compose__save',
                    { type: 'submit', disabled: !able || !savable(draft, saving) },
                    saving ? 'saving…' : 'save design'),
                  m('button.estate__refresh.compose__draw', { type: 'button', onclick: () => drawNow(draft.kind !== '') },
                    'draw the composition'),
                ]),
                outcome
                  ? m('div.compose__outcome', { 'data-kind': outcome.kind },
                      outcome.kind === 'saved'
                        ? [
                            m('p.compose__saved', `the harness saved ${text(outcome.design.name)}. Nothing ran.`),
                            verdictShown(outcome.design).map((sentence) => m('p.compose__verdict', sentence)),
                          ]
                        : [
                            m('p.compose__refused', [outcome.problem, outcome.remedy ? ` — ${outcome.remedy}` : '']),
                            errorsElsewhere(outcome.errors, shownFields)
                              .map((message) => m('p.compose__error.compose__error--elsewhere', message)),
                          ])
                  : null,
              ]),

              m('div.estate-view__section', { 'data-compose': 'designs' }, [
                m('h4.estate-view__heading', `Saved designs${held.project ? ` of ${held.project}` : ''}`),
                held.designs.length === 0
                  ? m('p.estate-view__hint.compose__no-designs', 'the harness holds no saved design in this project')
                  : m('div.estate__rows', held.designs.map(designRow)),
                held.components_read.read
                  ? null
                  : m('p.estate__problem.compose__components-unread',
                      `the saved components were not read: ${held.components_read.problem}`),
                m('p.estate__where', ['read from ', m('a.compose__link', {
                  href: held.where, target: '_blank', rel: 'noopener',
                }, held.where)]),
              ]),
            ]
          : null,
      ]);
    },
  };
}
