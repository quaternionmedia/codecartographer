/**
 * What the Compose panel offers for a design, and what it says the harness did.
 *
 * The harness gives the schema of a kind's configuration, and the form is
 * built from it: `fieldsOf` reads each property and says how it is offered. A
 * property this window has no control for is listed as not offered and is
 * left out of what is sent, so the harness fills its own default. Two
 * properties are references: `components` names saved components and
 * `compose` names saved designs.
 *
 * `configOf` turns what was filled in into the configuration sent, and
 * `saveOutcome` tells apart the four things that can come back from a save,
 * as `instructOutcome` does for an instruction. The harness's refusal keeps
 * each message beside the field it is about.
 *
 * Pure: no DOM and no request, so `web/tests/pure/compose.test.mjs` runs
 * every branch under node.
 */

/**
 * A query string from the defined entries only. `seam_client.query` is the
 * same rule; a module compiled for node cannot import it at run time.
 */
function query(params: Record<string, string | undefined>): string {
  const parts = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export type FieldKind =
  | 'boolean' | 'integer' | 'number' | 'string' | 'choice' | 'strings'
  | 'components' | 'compose' | 'unoffered';

export interface Field {
  name: string;
  /** The harness's title for it, or its name. */
  title: string;
  kind: FieldKind;
  /** The values a `choice` may take. */
  choices: string[];
  /** The harness's default, or undefined when it states none. */
  fallback: unknown;
  minimum?: number;
  maximum?: number;
  /** Whether the harness also takes no value at all. */
  nullable: boolean;
}

export type Values = Record<string, unknown>;

type Schema = Record<string, unknown>;

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));
const record = (value: unknown): Schema =>
  (value !== null && typeof value === 'object' && !Array.isArray(value) ? (value as Schema) : {});

/** A property with a `$ref` replaced by what it points at, keeping its own default. */
function resolved(property: Schema, defs: Schema): Schema {
  const ref = text(property.$ref);
  if (!ref) return property;
  const target = record(defs[ref.split('/').pop() ?? '']);
  return { ...target, ...property, $ref: undefined };
}

/** Every property of a configuration schema, in the harness's order, with how it is offered. */
export function fieldsOf(schema: unknown): Field[] {
  const root = record(schema);
  const defs = record(root.$defs);
  return Object.entries(record(root.properties)).map(([name, raw]) => {
    let property = resolved(record(raw), defs);
    let nullable = false;
    if (Array.isArray(property.anyOf)) {
      const options = (property.anyOf as unknown[]).map((option) => resolved(record(option), defs));
      const real = options.filter((option) => option.type !== 'null');
      nullable = real.length < options.length;
      if (real.length === 1) property = { ...property, ...real[0], anyOf: undefined };
    }
    const field: Field = {
      name,
      title: text(property.title) || name,
      kind: 'unoffered',
      choices: [],
      fallback: property.default,
      nullable,
    };
    if (typeof property.minimum === 'number') field.minimum = property.minimum;
    if (typeof property.maximum === 'number') field.maximum = property.maximum;

    const items = resolved(record(property.items), defs);
    if (name === 'components' && property.type === 'array') field.kind = 'components';
    else if (name === 'compose' && property.type === 'array') field.kind = 'compose';
    else if (Array.isArray(property.enum)) {
      field.kind = 'choice';
      field.choices = (property.enum as unknown[]).map(text);
    } else if (property.type === 'boolean' || property.type === 'integer'
      || property.type === 'number' || property.type === 'string') field.kind = property.type;
    else if (property.type === 'array' && items.type === 'string') field.kind = 'strings';
    return field;
  });
}

const REFERENCES: FieldKind[] = ['components', 'compose'];

/** What each offered field starts at: the harness's default, shown as the control holds it. */
export function initialValues(fields: Field[]): Values {
  const values: Values = {};
  for (const field of fields) {
    if (field.kind === 'unoffered') continue;
    if (REFERENCES.includes(field.kind)) values[field.name] = [];
    else if (field.kind === 'boolean') values[field.name] = field.fallback === true;
    else if (field.kind === 'strings') {
      values[field.name] = Array.isArray(field.fallback) ? field.fallback.map(text).join(', ') : '';
    } else values[field.name] = text(field.fallback);
  }
  return values;
}

const listed = (value: unknown): string[] =>
  text(value).split(',').map((part) => part.trim()).filter((part) => part !== '');

/**
 * The configuration sent for what was filled in.
 *
 * A field left blank is left out, so the harness fills its default or says
 * the field is required. A field not offered is never sent.
 */
export function configOf(fields: Field[], values: Values): Record<string, unknown> {
  const config: Record<string, unknown> = {};
  for (const field of fields) {
    const value = values[field.name];
    if (field.kind === 'unoffered' || value === undefined) continue;
    if (field.kind === 'boolean') config[field.name] = value === true;
    else if (field.kind === 'components') {
      const names = (value as unknown[]).map(text);
      if (names.length) config[field.name] = names.map((name) => ({ name }));
    } else if (field.kind === 'compose') {
      const names = (value as unknown[]).map(text);
      if (names.length) config[field.name] = names;
    } else if (field.kind === 'strings') {
      if (listed(value).length) config[field.name] = listed(value);
    } else if (field.kind === 'integer' || field.kind === 'number') {
      const typed = text(value).trim();
      if (typed !== '' && Number.isFinite(Number(typed))) config[field.name] = Number(typed);
      else if (typed !== '') config[field.name] = typed;
    } else if (text(value).trim() !== '') config[field.name] = text(value);
  }
  return config;
}

/** The names ticked for one of the two reference fields. */
export function ticked(values: Values, name: string): string[] {
  return Array.isArray(values[name]) ? (values[name] as unknown[]).map(text) : [];
}

/** `values` with one reference ticked or unticked; the others untouched. */
export function toggled(values: Values, name: string, reference: string, on: boolean): Values {
  const held = ticked(values, name).filter((entry) => entry !== reference);
  return { ...values, [name]: on ? [...held, reference] : held };
}

export interface Draft {
  name: string;
  kind: string;
  description: string;
  project: string;
}

/** The query that draws the saved designs with the draft and what it references so far. */
export function compositionQuery(draft: Draft | null, values: Values, layout?: string, paletteId?: string): string {
  return query({
    project: draft?.project.trim(),
    draft: draft ? 'true' : undefined,
    name: draft?.name.trim(),
    kind: draft?.kind,
    components: draft ? ticked(values, 'components').join(',') : undefined,
    compose: draft ? ticked(values, 'compose').join(',') : undefined,
    layout,
    palette_id: paletteId,
  });
}

/** Whether a press would send: a kind and a name are given, and no save is under way. */
export function savable(draft: Draft, saving: boolean): boolean {
  return !saving && draft.kind.trim() !== '' && draft.name.trim() !== '';
}

export interface FieldError {
  /** The field's location joined by dots, or empty for the design as a whole. */
  field: string;
  message: string;
}

export interface SaveProblem {
  kind: 'api-down' | 'unreachable' | 'refused';
  problem: string;
  remedy: string;
  where: string;
  errors: FieldError[];
}

export type SaveOutcome = SaveProblem | { kind: 'saved'; design: Record<string, unknown>; where: string };

/** Decide what the API's answer to a posted design was. */
export function saveOutcome(found: unknown, url: string): SaveOutcome {
  if (found === null || found === undefined || typeof found !== 'object') {
    return {
      kind: 'api-down', problem: 'the front end could not reach its own API',
      remedy: 'check that the codecarto server is running', where: url, errors: [],
    };
  }
  const doc = found as Record<string, unknown>;
  const design = doc.design;
  if (doc.saved === true && design !== null && typeof design === 'object') {
    return { kind: 'saved', design: design as Record<string, unknown>, where: text(doc.where) || url };
  }
  const errors = (Array.isArray(doc.errors) ? doc.errors : [])
    .map((error) => record(error))
    .map((error) => ({ field: text(error.field), message: text(error.message) }))
    .filter((error) => error.message !== '');
  return {
    kind: doc.unreachable === true ? 'unreachable' : 'refused',
    problem: text(doc.problem) || 'the design was not saved, and the answer did not say why',
    remedy: text(doc.remedy),
    where: text(doc.where) || url,
    errors,
  };
}

/** The messages about one field: its own, and those about anything inside it. */
export function errorsFor(errors: FieldError[], field: string): string[] {
  return errors
    .filter((error) => error.field === field || error.field.startsWith(`${field}.`))
    .map((error) => error.message);
}

/** The messages no control on the form stands for. */
export function errorsElsewhere(errors: FieldError[], shown: string[]): string[] {
  return errors
    .filter((error) => !shown.some((field) => error.field === field || error.field.startsWith(`${field}.`)))
    .map((error) => (error.field ? `${error.field}: ${error.message}` : error.message));
}

/** What a saved design's configuration references, by name. */
export function referencesOf(design: Record<string, unknown>): { components: string[]; compose: string[] } {
  const config = record(design.config);
  const names = (value: unknown): string[] =>
    (Array.isArray(value) ? value : [])
      .map((entry) => (typeof entry === 'string' ? entry : text(record(entry).name)))
      .filter((name) => name !== '');
  return { components: names(config.components), compose: names(config.compose) };
}

/**
 * What the harness said of a saved design, one sentence each, as given.
 *
 * Its status, its refusal and the sentence that it was kept anyway, and its
 * address or why it has none. A part the harness did not state is left out.
 */
export function verdictShown(design: Record<string, unknown>): string[] {
  const capability = record(design.capability);
  const said: string[] = [];
  if (capability.status) said.push(`status ${text(capability.status)}`);
  if (capability.refusal) said.push(`refused to run: ${text(capability.refusal)}`);
  if (capability.saved_anyway) said.push(text(capability.saved_anyway));
  if (design.address) said.push(`address ${text(design.address)}`);
  else if (design.address_unknown) said.push(`no address: ${text(design.address_unknown)}`);
  return said;
}

/** The harness's own page for one saved design, from the address its list was read at. */
export function designLink(where: string, name: string): string {
  const [base, asked] = where.split('?');
  return `${base}/${encodeURIComponent(name)}${asked ? `?${asked}` : ''}`;
}
