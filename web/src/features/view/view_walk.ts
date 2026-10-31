/**
 * Where a reader goes in the page without a server, and what each step's
 * address is.
 *
 * `view.html` is walked as well as handed documents. Its own address opens the
 * corpus's index, every family; from any drawing a reader steps down into a
 * family or a project, up its trail, across to another of its views, and back
 * with the browser's Back. Each step is a page address a reader can copy:
 *
 *   view.html                              every family, from the corpus's show folder
 *   view.html?show=<address>[&view=<v>]    a subject's view, the window's own grammar (`show_address.ts`)
 *   view.html?show=...&docs=<folder>       the same, from another show folder
 *   view.html?doc=<url>[&view=<v>]         a document by URL
 *
 * A subject's document is `<folder>/index/show.json`, `<folder>/family/<name>/show.json`
 * or `<folder>/project/<name>/show.json`, as `codecarto show export` writes
 * them. The trail is the window's (`trail`), told what nests in what by the
 * documents read so far: the index names every family and its members, a
 * family its subfamilies and projects, a project its families.
 *
 * PURE ON PURPOSE: no DOM and no network. `web/tests/pure/view-walk.test.mjs`
 * walks the corpus's real documents under node.
 */

import {
  VIEW_NAMES, formatShow, fromNode, parameters, parseShow,
  type ShowAddress, type ShowKind, type TrailSubjects,
} from '../show/show_address.js';
import { readDocument, type GraphDocument, type Refusal } from './view_document.js';

/**
 * The corpus's published show folder, relative to the page: GitHub Pages serves
 * this repository's site and the corpus's (`quaternionmedia/qm`) from one
 * origin, at `/codecartographer/` and `/qm/`.
 */
export const CORPUS_SHOW = '../qm/show/';

/** The window, served by `codecarto serve` on this machine at its default port (`codecarto.cli.DEFAULT_PORT`). */
export const WINDOW_APP = 'http://localhost:2718/app';

/** What a page address asks for: a subject's view from a show folder, or a document by URL. */
export type PageAddress =
  | { show: ShowAddress; docs: string | null }
  | { doc: string; view: string | null };

export type PageReading = { address: PageAddress; bare: boolean } | { refused: Refusal };

const INDEX: ShowAddress = { kind: 'index', name: '', view: 'estate' };

/** What a query string asks the page for. A bare page asks for every family. */
export function readPage(search: string): PageReading {
  const params = parameters(search);
  const doc = params.get('doc');
  if (doc) return { address: { doc, view: params.get('view') || null }, bare: false };
  const docs = params.get('docs') || null;
  if (!params.has('show')) return { address: { show: INDEX, docs }, bare: true };
  const show = parseShow(search);
  if (!show) {
    return { refused: {
      problem: `?show=${params.get('show')} names no subject`,
      remedy: 'name index, family:<name> or project:<name>, as ?show=project:carlos',
    } };
  }
  return { address: { show, docs }, bare: false };
}

/** The query string a page address is written as. */
export function formatPage(address: PageAddress): string {
  if ('doc' in address) {
    return `?doc=${encodeURIComponent(address.doc)}${address.view ? `&view=${encodeURIComponent(address.view)}` : ''}`;
  }
  return formatShow(address.show) + (address.docs ? `&docs=${encodeURIComponent(address.docs)}` : '');
}

/** The same page address, at another of its document's views. */
export function atView(address: PageAddress, view: string): PageAddress {
  if ('doc' in address) return { doc: address.doc, view };
  return { show: { ...address.show, view: view as ShowAddress['view'] }, docs: address.docs };
}

/** Where a subject's show document is, relative to the page unless `docs` is absolute. */
export function documentUrl(docs: string | null, show: ShowAddress): string {
  const folder = docs ? (docs.endsWith('/') ? docs : `${docs}/`) : CORPUS_SHOW;
  return `${folder}${show.kind === 'index' ? 'index' : `${show.kind}/${show.name}`}/show.json`;
}

/** The window's address for a `?show=` query string. */
export function windowLink(show: string): string {
  return `${WINDOW_APP}${show}`;
}

type Json = Record<string, unknown>;

const isObject = (value: unknown): value is Json =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const text = (value: unknown): string | null =>
  typeof value === 'string' && value.trim() ? value : null;

/** One of a show document's views, as the page offers it: drawn, or refused with why. */
export interface ViewChoice {
  view: string;
  label: string;
  title: string;
  refused: Refusal | null;
}

/**
 * The views a show document holds, in the order the window offers them and
 * named as it names them, each with its refusal when this page cannot draw it.
 * Empty for a document that is not a show document.
 */
export function viewsOf(data: unknown): ViewChoice[] {
  if (!isObject(data) || !isObject(data.views) || !isObject(data.subject)) return [];
  const kind = data.subject.kind as ShowKind;
  const names: Partial<Record<string, { label: string; title: string }>> = VIEW_NAMES[kind] ?? {};
  const held = Object.keys(data.views);
  const order = [...Object.keys(names).filter((view) => held.includes(view)),
                 ...held.filter((view) => !(view in names))];
  return order.map((view) => {
    const reading = readDocument(data, view);
    return {
      view,
      label: names[view]?.label ?? view,
      title: names[view]?.title ?? `draw the ${view} view`,
      refused: 'refused' in reading ? reading.refused : null,
    };
  });
}

/** A family or a project a drawing lets the reader open, by its own name. */
export interface Openable {
  address: ShowAddress;
  label: string;
}

const nodesOf = (graph: GraphDocument['graph']): [string, Json][] =>
  (Array.isArray(graph.nodes)
    ? graph.nodes.map((node, i): [string, unknown] => [isObject(node) && text(node.id) ? String(node.id) : String(i), node])
    : isObject(graph.nodes) ? Object.entries(graph.nodes) : []
  ).filter((entry): entry is [string, Json] => isObject(entry[1]));

/** The address a node opens, from its `show` attribute (`family:core`), on it or in its metadata. */
function shownBy(node: Json): ShowAddress | null {
  return fromNode(node.show ?? (isObject(node.metadata) ? node.metadata.show : undefined));
}

/**
 * Every family and project a drawing names, but `except`: what a double-click
 * on it opens, listed so it can be opened without one. Families first, then
 * projects, each by name.
 */
export function openables(document: GraphDocument, except: string | null): Openable[] {
  const seen = new Map<string, Openable>();
  for (const [, node] of nodesOf(document.graph)) {
    const address = shownBy(node);
    if (!address || address.kind === 'index') continue;
    const key = `${address.kind}:${address.name}`;
    if (key === except || seen.has(key)) continue;
    seen.set(key, { address, label: text(node.label) ?? address.name });
  }
  const rank = (o: Openable) => (o.address.kind === 'family' ? 0 : 1);
  return [...seen.values()].sort((a, b) =>
    rank(a) - rank(b) || a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));
}

/** What nests in what, as far as the documents read so far say. */
export interface Nesting {
  families: Map<string, string | null>;
  claims: Map<string, Set<string>>;
}

export const nesting = (): Nesting => ({ families: new Map(), claims: new Map() });

/**
 * Learn what a drawing says nests in what: a family containing a family is
 * its subfamily, a family containing a project claims it, and so does a
 * project's `member_of` edge to a family.
 */
export function learn(known: Nesting, document: GraphDocument): void {
  const byId = new Map(nodesOf(document.graph).map(([id, node]) => [id, shownBy(node)]));
  for (const address of byId.values()) {
    if (address?.kind === 'family' && !known.families.has(address.name)) known.families.set(address.name, null);
  }
  const claim = (project: string, family: string) => {
    if (!known.claims.has(project)) known.claims.set(project, new Set());
    known.claims.get(project)!.add(family);
  };
  for (const edge of Array.isArray(document.graph.edges) ? document.graph.edges : []) {
    if (!isObject(edge)) continue;
    const from = byId.get(String(edge.source));
    const to = byId.get(String(edge.target));
    const kind = isObject(edge.metadata) ? edge.metadata.kind : edge.kind;
    if (!from || !to) continue;
    if (kind === 'contains' && from.kind === 'family' && to.kind === 'family') known.families.set(to.name, from.name);
    else if (kind === 'contains' && from.kind === 'family' && to.kind === 'project') claim(to.name, from.name);
    else if (kind === 'member_of' && from.kind === 'project' && to.kind === 'family') claim(from.name, to.name);
  }
}

/** Learn what a show document's estate view says nests in what; anything else says nothing. */
export function learnFrom(known: Nesting, data: unknown): void {
  const estate = isObject(data) && isObject(data.views) ? data.views.estate : null;
  if (isObject(estate) && isObject(estate.graph)) learn(known, estate as unknown as GraphDocument);
}

/** The nesting as the window's trail reads it. */
export function trailSubjects(known: Nesting): TrailSubjects {
  return {
    families: [...known.families].map(([name, within]) => ({ name, within })),
    projects: [...known.claims].map(([name, families]) => ({ name, families: [...families].sort() })),
  };
}
