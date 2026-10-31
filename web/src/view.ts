/**
 * The page without a server: `view.html`, which draws the graph documents it
 * is handed and asks no codecarto route for anything.
 *
 * The window (`index.html`) is the dock of a person running codecarto: its
 * boot asks its routes and most of its panels need one. This page is the
 * window of every other reader. It draws a positioned document with the
 * window's one renderer and its key, and nothing else of the window comes
 * with it: no dock, no panel, no `RequestHandler`, no `api_base.ts`. Served
 * by any static host, from any folder of it, it names its assets relative to
 * itself (`vite.config.js`, mode `view`).
 *
 * Its ways in, each read by `readDocument` and checked the same way:
 *
 *   view.html?doc=<url>[&view=<view>]   a document by URL, and a show document's view
 *   a file dropped on the page, or opened with "open a file"
 *   a paste
 *
 * WHO HANDED IT A GRAPH IS SAID BESIDE IT. The page holds nothing a sender
 * could take and writes nothing, so the most a document can do is be drawn;
 * the page says where it came from, beside the producer's caveat, verbatim.
 * Everything a document says is set as text, never as markup.
 *
 * The decision is the draft record *One page without a server draws the
 * graphs and addresses other apps hand it*, and `docs/roadmap/a-page-without-a-server.md`
 * is the order the rest of it lands in.
 */

import './styles/index.css';
import './features/view/view.css';

import { drawCopy } from './features/graph/services/d3_renderer';
import { LegendExtension } from './features/graph/extensions/legend_extension';
import type { GraphData } from './features/graph/services/graph_types';
import { DEFAULT_GRAPH_STYLING } from './state/graph_styling';
import { readDocument, readableUrl, type Drawing, type Refusal } from './features/view/view_document';

/** Who handed the page what it shows. */
type Handed = { kind: 'url'; url: string } | { kind: 'file'; name: string } | { kind: 'paste' };

function handedBy(handed: Handed): string {
  if (handed.kind === 'url') return `read from ${handed.url}`;
  if (handed.kind === 'file') return `opened from the file ${handed.name}`;
  return 'pasted';
}

function element<K extends keyof HTMLElementTagNameMap>(tag: K, className: string, text?: string): HTMLElementTagNameMap[K] {
  const made = document.createElement(tag);
  made.className = className;
  if (text !== undefined) made.textContent = text;
  return made;
}

const root = document.getElementById('view')!;

const bar = element('header', 'view__bar');
const subject = element('strong', 'view__subject', 'Code Cartographer');
const counts = element('span', 'view__counts');
const handedLine = element('span', 'view__handed');
const open = element('button', 'view__open', 'open a file');
open.type = 'button';
const chooser = element('input', 'view__chooser');
chooser.type = 'file';
chooser.accept = '.json,application/json';
chooser.hidden = true;
bar.append(subject, counts, handedLine, open, chooser);

const caveat = element('p', 'view__caveat');
const drawnLine = element('p', 'view__drawn');
const problem = element('section', 'view__problem');
problem.setAttribute('role', 'alert');
const problemWhat = element('p', 'view__problem-what');
const problemRemedy = element('p', 'view__problem-remedy');
problem.append(problemWhat, problemRemedy);

const empty = element('section', 'view__empty');
empty.append(
  element('p', 'view__empty-lead', 'Drop a graph document here, open one, or paste it.'),
  element('p', 'view__empty-more',
    'This page draws a show document (show.json, as codecarto show export writes it) or a gJGF graph, '
    + 'with the positions it was drawn at, and asks no server for anything. '
    + 'Name one by URL with ?doc=<url>, and a show document\'s view with &view=estate, code or imports.'),
);

const canvas = element('div', 'view__canvas graph_content graphRenderer');
root.append(bar, caveat, drawnLine, problem, empty, canvas);
for (const hidden of [caveat, drawnLine, problem, canvas]) hidden.hidden = true;

/** A show document's view, for whatever document the page is handed: `estate` when none is named. */
const query = new URLSearchParams(window.location.search);
const view = query.get('view');

let legend: LegendExtension | null = null;
let drawing = 0;

function say(line: HTMLElement, value: string | null): void {
  line.textContent = value ?? '';
  line.hidden = !value;
}

/** A document not drawn: what is wrong with it and where it came from. What is drawn already stays drawn. */
function refused(refusal: Refusal, handed: Handed | null): void {
  problemWhat.textContent = `Not drawn${handed ? `, ${handedBy(handed)}` : ''}: ${refusal.problem}.`;
  say(problemRemedy, refusal.remedy ? `To draw it, ${refusal.remedy}.` : null);
  problem.hidden = false;
  document.body.dataset.refused = 'true';
}

function drawn(shown: Drawing, handed: Handed): void {
  const number = ++drawing;
  legend?.destroy();
  legend = null;
  problem.hidden = true;
  empty.hidden = true;
  canvas.hidden = false;
  delete document.body.dataset.refused;
  delete document.body.dataset.drawn;

  const title = shown.subject ? `${shown.subject}${shown.view ? ` · ${shown.view}` : ''}` : 'a graph';
  subject.textContent = title;
  document.title = `${title} · Code Cartographer`;
  counts.textContent = `${shown.nodes} nodes, ${shown.edges} edges`
    + (shown.unplaced ? `; ${shown.unplaced} arrived with no position and are placed on their depth ring` : '');
  say(handedLine, handedBy(handed));
  say(caveat, shown.caveat);
  say(drawnLine, shown.drawn);

  const styling = { ...DEFAULT_GRAPH_STYLING, layout: shown.layout };
  const renderer = drawCopy(canvas, shown.document as unknown as GraphData, styling);
  legend = new LegendExtension(() => styling.colorBy);
  legend.initialize(renderer.buildExtensionContext(new Set(), () => {}));
  // The key reads the scene once the canvas says it is drawn (`data-drawn`).
  const settled = () => {
    if (number !== drawing) return;
    if (canvas.querySelector('svg[data-drawn="true"]')) {
      legend?.apply();
      document.body.dataset.drawn = 'true';
    } else {
      requestAnimationFrame(settled);
    }
  };
  requestAnimationFrame(settled);
}

function read(text: string, handed: Handed): void {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch (error) {
    refused({ problem: `it is not JSON (${(error as Error).message})`,
              remedy: 'hand it the document itself, as JSON' }, handed);
    return;
  }
  const reading = readDocument(data, view);
  if ('refused' in reading) refused(reading.refused, handed);
  else drawn(reading.drawing, handed);
}

async function readUrl(raw: string): Promise<void> {
  let url: string;
  try {
    url = new URL(raw, window.location.href).href;
  } catch {
    refused({ problem: `${raw} is not an address`, remedy: 'name the document with ?doc=https://...' }, null);
    return;
  }
  const handed: Handed = { kind: 'url', url };
  const unreadable = readableUrl(url);
  if (unreadable) {
    refused(unreadable, handed);
    return;
  }
  let answer: Response;
  try {
    answer = await fetch(url, { credentials: 'omit' });
  } catch (error) {
    refused({ problem: `${url} could not be read (${(error as Error).message})`,
              remedy: 'check the address; a host serving it to this page must allow its origin (access-control-allow-origin)' }, handed);
    return;
  }
  if (!answer.ok) {
    refused({ problem: `${url} answered ${answer.status}${answer.statusText ? ` ${answer.statusText}` : ''}`,
              remedy: 'check the address' }, handed);
    return;
  }
  read(await answer.text(), handed);
}

async function readFile(file: File): Promise<void> {
  read(await file.text(), { kind: 'file', name: file.name });
}

open.addEventListener('click', () => chooser.click());
chooser.addEventListener('change', () => {
  const file = chooser.files?.[0];
  if (file) void readFile(file);
  chooser.value = '';
});

window.addEventListener('dragover', (event) => {
  event.preventDefault();
  document.body.classList.add('view--dropping');
});
window.addEventListener('dragleave', () => document.body.classList.remove('view--dropping'));
window.addEventListener('drop', (event) => {
  event.preventDefault();
  document.body.classList.remove('view--dropping');
  const file = event.dataTransfer?.files?.[0];
  if (file) void readFile(file);
});

document.addEventListener('paste', (event) => {
  const file = event.clipboardData?.files?.[0];
  if (file) {
    void readFile(file);
    return;
  }
  const pasted = event.clipboardData?.getData('text/plain');
  if (pasted?.trim()) read(pasted, { kind: 'paste' });
});

const doc = query.get('doc');
if (doc) void readUrl(doc);
