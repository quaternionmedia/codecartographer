/**
 * What the Designer panel says about a shape the harness declares.
 *
 * `/designer/data` sets two of the harness's documents side by side by shape
 * name: the plane's entry (`declared`) and the harness's account of whether
 * the shape could run now (`could_run`). The wording here reads those fields
 * as given. A status, a need key and a drift list's name are the harness's and
 * are shown as written; there is no list of them in this file. A mark is
 * shown only when its field is exactly `true`, and a field that is absent
 * says nothing.
 *
 * Pure: no DOM and no request, so `web/tests/pure/designer.test.mjs` runs
 * every branch under node.
 */

import type { Instance } from './interactions';

/** One need, as either document states it. */
export interface Need {
  key?: unknown;
  because?: unknown;
  supplied_by?: unknown;
}

/** A shape's entry in the plane, as given. */
export interface Declared {
  topology?: unknown;
  status?: unknown;
  can_run?: unknown;
  spends?: unknown;
  writes?: unknown;
  decides?: unknown;
  why?: unknown;
  needs?: Need[];
  [key: string]: unknown;
}

/** A shape's entry in the harness's account of what could run, as given. */
export interface CouldRun {
  status?: unknown;
  runnable?: unknown;
  unmet?: Need[];
  [key: string]: unknown;
}

/** A shape under one named setting. */
export interface OptionRow {
  setting: unknown;
  value: unknown;
  declared: Declared;
}

export interface ShapeRow {
  name: string;
  declared: Declared | null;
  could_run: CouldRun | null;
  options: OptionRow[];
  /** Which document does not name the shape, or empty. */
  missing: string;
}

export interface DesignerDocument {
  instance: Instance;
  where: string;
  shapes: ShapeRow[];
  /** Whether the account of what could run was read, and why not. */
  could_run: { read: boolean; problem: string; remedy: string; where: string };
  have: Record<string, unknown> | null;
  never_supplied: Need | null;
  statuses: unknown[];
  needs: unknown[];
  attested: unknown[];
  drift: Record<string, unknown>;
  reading: Record<string, unknown>;
}

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

/** The three marks the plane states for a shape. */
export const MARKS = ['spends', 'writes', 'decides'] as const;

/** The marks a shape carries: each one whose field is exactly `true`. */
export function marksShown(declared: Declared | null): string[] {
  if (!declared) return [];
  return MARKS.filter((mark) => declared[mark] === true);
}

/** A shape's status as written, from the plane first; empty when neither states one. */
export function statusShown(row: ShapeRow): string {
  return text(row.declared?.status) || text(row.could_run?.status);
}

/** What the plane declares about running, or empty when it states nothing. */
export function declaredRunShown(declared: Declared | null): string {
  if (declared?.can_run === true) return 'declared able to run';
  if (declared?.can_run === false) return 'declared not able to run';
  return '';
}

/** The keys of a list of needs, as written. */
export function needKeys(needs: Need[] | undefined): string[] {
  return (needs ?? []).map((need) => text(need.key)).filter((key) => key !== '');
}

/**
 * Whether the harness says a shape could run now, as one sentence.
 *
 * `read` is whether that account was read at all; when it was not, nothing is
 * said for any shape. A shape the account does not name says nothing here:
 * the row's `missing` says it.
 */
export function couldRunShown(row: ShapeRow, read: boolean): string {
  if (!read || !row.could_run) return '';
  if (row.could_run.runnable === true) return 'could run now';
  if (row.could_run.runnable !== false) return '';
  const unmet = needKeys(row.could_run.unmet);
  return unmet.length ? `could not run now: ${unmet.join(', ')} unmet` : 'could not run now';
}

/** `yes`, `no` or empty for a row's `data-runnable`. */
export function runnableAttr(row: ShapeRow, read: boolean): string {
  if (!read || !row.could_run) return '';
  if (row.could_run.runnable === true) return 'yes';
  return row.could_run.runnable === false ? 'no' : '';
}

/** One value the harness gave, as written; a value it left null is said to be unstated. */
export function valueShown(value: unknown): string {
  if (value === null || value === undefined) return 'not stated';
  return typeof value === 'object' ? JSON.stringify(value) : String(value);
}

/** What the harness has, one entry per field it gave, in its order. */
export function haveShown(have: Record<string, unknown> | null): string {
  if (!have) return '';
  return Object.entries(have).map(([name, value]) => `${name} ${valueShown(value)}`).join(' · ');
}

export interface DriftList {
  name: string;
  items: string[];
}

/** Each list of `drift` under the harness's name for it; a value that is no list is left out. */
export function driftShown(drift: Record<string, unknown>): DriftList[] {
  return Object.entries(drift)
    .filter(([, items]) => Array.isArray(items))
    .map(([name, items]) => ({ name, items: (items as unknown[]).map(text) }));
}

/** The harness's caveats, each sentence as written, in its order. */
export function readingShown(reading: Record<string, unknown>): string[] {
  return Object.values(reading).map(text).filter((said) => said !== '');
}

/** An option's setting and value, as the plane names them. */
export function optionShown(option: OptionRow): string {
  return `${text(option.setting)} = ${valueShown(option.value)}`;
}
