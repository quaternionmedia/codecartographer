/**
 * What the page without a server reads: a graph document, whatever brought it.
 *
 * `view.html` draws what it is handed -- a document named by URL, a file
 * dropped on it or opened, a paste -- and every way in reads the document
 * here, once, so each is checked the same way. Two shapes are drawn:
 *
 *   - a show document (`show.json`, what `codecarto show export` writes) and
 *     one of its views, `estate` unless another is asked for;
 *   - a gJGF document, `{ graph: { nodes, edges }, metadata }`, as a
 *     `/.../gjgf` route answers it.
 *
 * Anything else is refused with a problem and a remedy, and so is a view its
 * document holds as a pointer rather than as a graph: a family's code view
 * points at each project's, which codecarto packs again (`show_layout.pack`).
 *
 * IT CALCULATES NO LAYOUT. A node arrives placed, or the canvas places it on
 * its depth ring, as it places any node with no position. The reading counts
 * how many arrived with none, so the page can say so.
 *
 * PURE ON PURPOSE: no DOM and no network. `web/tests/pure/view-document.test.mjs`
 * reads every shape and every refusal under node.
 */

import { SHOWCASE_LAYOUT } from '../graph/services/showcase.js';

/** The schema of show document this page reads (`show_export.SCHEMA`). */
export const SHOW_SCHEMA = 1;

/** A document the canvas is handed: gJGF's shape. */
export interface GraphDocument {
  graph: { nodes: Record<string, unknown> | unknown[]; edges: unknown[]; [key: string]: unknown };
  metadata: Record<string, unknown>;
}

export interface Drawing {
  document: GraphDocument;
  /** The layout the window draws this view in, as the styling names it. */
  layout: string;
  /** `project:carlos`, `family:core`, `index`; null when the document names none. */
  subject: string | null;
  /** The show document's view drawn; null for a gJGF document. */
  view: string | null;
  /** The producer's caveat, verbatim. */
  caveat: string | null;
  /** When the document was drawn, by what, and from which commit. */
  drawn: string | null;
  nodes: number;
  edges: number;
  /** Nodes with no position, which the canvas places on their depth ring. */
  unplaced: number;
}

export interface Refusal {
  problem: string;
  remedy: string;
}

export type Reading = { drawing: Drawing } | { refused: Refusal };

const SHAPES = 'hand it a show document (show.json, as codecarto show export writes it) '
  + 'or a gJGF graph ({ "graph": { "nodes", "edges" }, "metadata" }), as a codecarto /gjgf route answers';

type Json = Record<string, unknown>;

const isObject = (value: unknown): value is Json =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const text = (value: unknown): string | null =>
  typeof value === 'string' && value.trim() ? value : null;

const refuse = (problem: string, remedy: string): Reading => ({ refused: { problem, remedy } });

/** A document, read: drawn, or refused with what to do instead. `view` names a show document's view. */
export function readDocument(data: unknown, view?: string | null): Reading {
  if (!isObject(data)) return refuse('it is not a JSON object', SHAPES);
  if ('views' in data) return readShow(data, view ?? null);
  if ('graph' in data) return readGraph(data, null, null, null, null);
  return refuse('it is neither a show document nor a gJGF graph: it has no "views" and no "graph"', SHAPES);
}

/** The address a show document's subject is opened at in codecarto. */
function address(subject: string, view: string): string {
  return `?show=${subject}${view === 'estate' ? '' : `&view=${view}`}`;
}

function subjectOf(data: Json): string | null {
  const subject = data.subject;
  if (!isObject(subject)) return null;
  if (subject.kind === 'index') return 'index';
  const kind = text(subject.kind);
  const name = text(subject.name);
  return kind && name ? `${kind}:${name}` : null;
}

function drawnOf(data: Json): string | null {
  const provenance = data.provenance;
  if (!isObject(provenance)) return null;
  const parts: string[] = [];
  const at = text(provenance.drawn_at);
  if (at) parts.push(`drawn ${at}`);
  const by = isObject(provenance.drawn_by) ? text(provenance.drawn_by.graph) : null;
  if (by) parts.push(`by ${by}`);
  const source = isObject(provenance.source) ? provenance.source : isObject(provenance.claims) ? provenance.claims : null;
  const repo = source ? text(source.repo) : null;
  const commit = source ? text(source.commit) : null;
  if (repo) parts.push(`from ${repo}${commit ? ` at ${commit.slice(0, 7)}` : ''}`);
  return parts.length ? parts.join(', ') : null;
}

function readShow(data: Json, asked: string | null): Reading {
  if (data.schema !== SHOW_SCHEMA) {
    return refuse(`it is a show document of schema ${JSON.stringify(data.schema ?? null)}, and this page reads schema ${SHOW_SCHEMA}`,
      'export it again with this codecartographer, or open it in the codecartographer that wrote it');
  }
  const subject = subjectOf(data);
  if (!subject) return refuse('it is a show document that names no subject', SHAPES);
  const views = data.views;
  if (!isObject(views) || !Object.keys(views).length) return refuse(`the show document of ${subject} holds no views`, SHAPES);
  const names = Object.keys(views);
  const view = asked ?? (names.includes('estate') ? 'estate' : names[0]);
  const entry = views[view];
  if (!isObject(entry)) {
    return refuse(`the show document of ${subject} has no ${view} view`,
      `its views are ${names.join(', ')}: name one with &view=`);
  }
  if (entry.absent === true) {
    return refuse(text(entry.problem) ?? `${subject} has no ${view} view`, text(entry.remedy) ?? '');
  }
  if (typeof entry.graph === 'string') {
    return refuse(`the ${view} view of ${subject} is not a graph in its document but a pointer ("${entry.graph}"): `
      + 'codecarto composes it and lays it out again, and this page draws only positioned graphs',
      `open it in codecarto, at ${address(subject, view)}, or open each project's ${view} view here`);
  }
  if ('composed' in entry) {
    return refuse(`the ${view} view of ${subject} is a composed system, which the window's system monitor lays out, `
      + 'and this page does not carry the monitor',
      `open it in codecarto, at ${address(subject, view)}`);
  }
  // The window draws a project's code view as a Showcase, and every other
  // view as compound outlines (`layout_context.ts`, `_openShow`).
  const layout = view === 'code' && subject.startsWith('project:') ? SHOWCASE_LAYOUT : 'compound_layout';
  return readGraph(entry, subject, view, layout, drawnOf(data));
}

/** A layout as `metadata.layout` names it, as the styling names it (`layout_names.backendLayoutName`, reversed). */
function registryName(named: unknown): string {
  const name = text(named);
  if (!name) return 'spring_layout';
  if (/^showcase\b/i.test(name)) return SHOWCASE_LAYOUT;
  return `${name.trim().toLowerCase()}_layout`;
}

function placed(node: unknown): boolean {
  if (!isObject(node)) return false;
  const inner = isObject(node.metadata) ? node.metadata : {};
  const x = node.x ?? inner.x;
  const y = node.y ?? inner.y;
  return typeof x === 'number' && Number.isFinite(x) && typeof y === 'number' && Number.isFinite(y);
}

function readGraph(data: Json, subject: string | null, view: string | null,
                   layout: string | null, drawn: string | null): Reading {
  const where = subject && view ? `the ${view} view of ${subject}` : 'its graph';
  const graph = data.graph;
  if (!isObject(graph)) return refuse(`${where} is not an object`, SHAPES);
  const nodes = graph.nodes;
  const edges = graph.edges ?? [];
  if (!(isObject(nodes) || Array.isArray(nodes)) || !Array.isArray(edges)) {
    return refuse(`${where} has no "nodes" object or list, or no "edges" list`, SHAPES);
  }
  const all = Array.isArray(nodes) ? nodes : Object.values(nodes);
  if (!all.length) return refuse(`${where} holds no nodes`, 'hand it a graph with at least one node');
  const metadata = isObject(data.metadata) ? data.metadata : {};
  const named = subject ?? text(metadata.subject);
  return {
    drawing: {
      document: { graph: { ...graph, nodes, edges }, metadata },
      layout: layout ?? registryName(metadata.layout),
      subject: named,
      view,
      caveat: text(metadata.caveat),
      drawn,
      nodes: all.length,
      edges: edges.length,
      unplaced: all.filter((node) => !placed(node)).length,
    },
  };
}

/** Whether a URL the page was asked to read is one it reads: HTTP or HTTPS, nothing else. */
export function readableUrl(url: string): Refusal | null {
  return /^https?:\/\//i.test(url) ? null
    : { problem: `${url} is not an http or https address`, remedy: 'name the document with ?doc=https://...' };
}
