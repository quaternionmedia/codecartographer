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
 * IT IS WALKED. Its own address opens every family, from the corpus's show
 * folder beside it; the bar's trail steps up, its views step across, and its
 * list of families and projects -- or a double-click on one -- steps down.
 * Each step rewrites the address, so it can be copied, and adds a history
 * entry, so Back returns (`view_walk.ts`). `docs/journeys.md` is each walk.
 *
 * Its ways in, each read by `readDocument` and checked the same way:
 *
 *   view.html[?show=<address>[&view=<view>][&docs=<folder>]]   a subject, from a show folder
 *   view.html?doc=<url>[&view=<view>]                          a document by URL
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
import { SHOW_OPEN_EVENT } from './features/graph/services/streaming_renderer';
import { LegendExtension } from './features/graph/extensions/legend_extension';
import type { GraphData } from './features/graph/services/graph_types';
import { DEFAULT_GRAPH_STYLING } from './state/graph_styling';
import { VIEW_NAMES, crumbLabel, fromNode, trail, type ShowAddress } from './features/show/show_address';
import {
  readDocument, readableUrl, type Drawing, type GraphDocument, type Refusal,
} from './features/view/view_document';
import {
  atView, documentUrl, formatPage, learnFrom, nesting, openables, readPage, trailSubjects, viewsOf, windowLink,
  type PageAddress,
} from './features/view/view_walk';

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

/** A link that opens `address` here on a plain click; a modified one, or a middle click, is the browser's. */
function walkLink(className: string, text: string, address: PageAddress, title?: string): HTMLAnchorElement {
  const link = element('a', className, text);
  link.href = formatPage(address);
  if (title) link.title = title;
  link.addEventListener('click', (event) => {
    if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    void go(address, 'push');
  });
  return link;
}

const root = document.getElementById('view')!;

const bar = element('header', 'view__bar');
const trailNav = element('nav', 'view__trail');
trailNav.setAttribute('aria-label', 'where this drawing is');
const subject = element('strong', 'view__subject', 'Code Cartographer');
const viewsNav = element('nav', 'view__views');
viewsNav.setAttribute('aria-label', 'views of this subject');

const here = element('details', 'view__here');
const hereSummary = element('summary', 'view__here-summary');
const hereFilter = element('input', 'view__here-filter');
hereFilter.type = 'search';
hereFilter.placeholder = 'filter by name';
hereFilter.setAttribute('aria-label', 'filter the families and projects by name');
const hereList = element('ul', 'view__here-list');
here.append(hereSummary, hereFilter, hereList);

const counts = element('span', 'view__counts');
const handedLine = element('span', 'view__handed');
const tools = element('span', 'view__tools');
const copy = element('button', 'view__copy', 'copy link');
copy.type = 'button';
copy.title = "copy this drawing's address";
const open = element('button', 'view__open', 'open a file');
open.type = 'button';
const chooser = element('input', 'view__chooser');
chooser.type = 'file';
chooser.accept = '.json,application/json';
chooser.hidden = true;
tools.append(copy, open, chooser);
bar.append(trailNav, subject, viewsNav, here, counts, handedLine, tools);

const hint = element('p', 'view__hint');
// The producer's caveat and where the document was drawn, folded as the window folds them.
const about = element('details', 'view__about');
const caveat = element('p', 'view__caveat');
const drawnLine = element('p', 'view__drawn');
about.append(element('summary', 'view__about-summary', 'What this drawing can say'), caveat, drawnLine);
const problem = element('section', 'view__problem');
problem.setAttribute('role', 'alert');
const problemWhat = element('p', 'view__problem-what');
const problemRemedy = element('p', 'view__problem-remedy');
const dismiss = element('button', 'view__problem-dismiss', 'dismiss');
dismiss.type = 'button';
dismiss.addEventListener('click', () => {
  problem.hidden = true;
  delete document.body.dataset.refused;
});
problem.append(dismiss, problemWhat, problemRemedy);

const empty = element('section', 'view__empty');
const emptyWhy = element('p', 'view__empty-why');
empty.append(
  element('p', 'view__empty-lead', 'Drop a graph document here, open one, or paste it.'),
  element('p', 'view__empty-more',
    'This page draws a show document (show.json, as codecarto show export writes it) or a gJGF graph, '
    + 'with the positions it was drawn at, and asks no server for anything. '
    + 'Name a subject with ?show=project:<name>, and a folder of show documents with &docs=<url>; '
    + 'or a document by URL with ?doc=<url>; and a view with &view=estate, code or imports.'),
  emptyWhy,
);

const canvas = element('div', 'view__canvas graph_content graphRenderer');
root.append(bar, hint, about, problem, empty, canvas);
for (const hidden of [trailNav, viewsNav, here, copy, hint, about, caveat, drawnLine, problem, canvas, emptyWhy]) {
  hidden.hidden = true;
}

/** The view a file or a paste is drawn at: the address's `&view=`, whatever document it is. */
const askedView = new URLSearchParams(window.location.search).get('view');

/**
 * The document in hand: drawn at `view`, or, before anything is drawn, the
 * one whose asked view was refused, so its other views are offered. Its page
 * address is null for a file or a paste.
 */
let held: { data: unknown; handed: Handed; page: PageAddress | null; view: string | null } | null = null;
let legend: LegendExtension | null = null;
let drawing = 0;
let asking = 0;

/** What nests in what, from every show document read this visit: the trail's families. */
const known = nesting();
/** The show folders whose index has been asked for, for the trail. */
const indexAsked = new Set<string>();

function say(line: HTMLElement, value: string | null): void {
  line.textContent = value ?? '';
  line.hidden = !value;
}

/** What a drawing is called: `carlos · code map`, `the corpus · every family`, or a gJGF document's own subject. */
function titleOf(shown: Drawing): string {
  const address = shown.subject ? fromNode(shown.subject) : null;
  if (!address) return shown.subject ?? 'a graph';
  const names: Partial<Record<string, { label: string }>> = VIEW_NAMES[address.kind];
  const view = shown.view ? names[shown.view]?.label ?? shown.view : null;
  const name = address.kind === 'index' ? 'the corpus' : address.name;
  return view ? `${name} · ${view}` : name;
}

/** A document not drawn: what is wrong with it and where it came from. What is drawn already stays drawn. */
function refused(refusal: Refusal, handed: Handed | null): void {
  problemWhat.textContent = `Not drawn${handed ? `, ${handedBy(handed)}` : ''}: ${refusal.problem}.`;
  say(problemRemedy, refusal.remedy ? `To draw it, ${refusal.remedy}.` : null);
  if (refusal.window) {
    // Where codecarto runs on this machine, the window draws it.
    const link = element('a', 'view__window', 'Open it in codecarto ↗');
    link.href = windowLink(refusal.window);
    link.target = '_blank';
    link.rel = 'noopener';
    link.title = 'the window, where codecarto serve runs on this machine';
    problemRemedy.append(' ', link);
    problemRemedy.hidden = false;
  }
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

  const title = titleOf(shown);
  subject.textContent = title;
  document.title = `${title} · Code Cartographer`;
  counts.textContent = `${shown.nodes} nodes, ${shown.edges} edges`
    + (shown.unplaced ? `; ${shown.unplaced} arrived with no position and are placed on their depth ring` : '');
  say(handedLine, handedBy(handed));
  say(caveat, shown.caveat);
  say(drawnLine, shown.drawn);
  about.hidden = !shown.caveat && !shown.drawn;

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

/** The subject in hand, when its document came from a show folder: what the trail and the list walk from. */
function walked(): { show: ShowAddress; docs: string | null } | null {
  return held?.page && 'show' in held.page ? held.page : null;
}

/** The bar's trail, views and list, for the document in hand: drawn at `view`, or at none yet. */
function walkBar(view: string | null, graph: GraphDocument | null, drawnSubject: string | null): void {
  const from = walked();

  trailNav.replaceChildren();
  if (from) {
    const show = { ...from.show, view: (view ?? from.show.view) as ShowAddress['view'] };
    const levels = trail(show, trailSubjects(known));
    levels.forEach((level, i) => {
      if (i) trailNav.append(element('span', 'view__sep', '›'));
      level.forEach((step, j) => {
        if (j) trailNav.append(element('span', 'view__sep', '·'));
        if (i === levels.length - 1) {
          const current = element('span', 'view__crumb is-current', crumbLabel(step));
          current.setAttribute('aria-current', 'page');
          trailNav.append(current);
        } else {
          trailNav.append(walkLink('view__crumb', crumbLabel(step), { show: step, docs: from.docs }));
        }
      });
    });
  }
  trailNav.hidden = !from;
  subject.hidden = !!from;

  viewsNav.replaceChildren();
  const inHand = held;
  const choices = inHand ? viewsOf(inHand.data) : [];
  for (const choice of choices) {
    if (choice.view === view) {
      const current = element('span', 'view__view is-current', choice.label);
      current.setAttribute('aria-current', 'page');
      current.dataset.view = choice.view;
      viewsNav.append(current);
    } else if (choice.refused) {
      // Pressed, it says why and where it can be drawn; what is drawn stays.
      const refusal = choice.refused;
      const button = element('button', 'view__view is-refused', choice.label);
      button.type = 'button';
      button.dataset.view = choice.view;
      button.title = `not drawn here: ${refusal.problem}`;
      button.addEventListener('click', () => refused(refusal, inHand?.handed ?? null));
      viewsNav.append(button);
    } else if (inHand?.page) {
      const link = walkLink('view__view', choice.label, atView(inHand.page, choice.view), choice.title);
      link.dataset.view = choice.view;
      viewsNav.append(link);
    } else {
      // A file's or a paste's views are drawn from the document in hand; they have no address.
      const button = element('button', 'view__view', choice.label);
      button.type = 'button';
      button.dataset.view = choice.view;
      button.title = choice.title;
      button.addEventListener('click', () => {
        if (inHand) show(inHand.data, inHand.handed, null, choice.view, 'none');
      });
      viewsNav.append(button);
    }
  }
  viewsNav.hidden = choices.length < 2;

  const listed = from && graph ? openables(graph, drawnSubject) : [];
  hereList.replaceChildren(...listed.map((one) => {
    const item = element('li', 'view__here-item');
    item.dataset.name = one.label.toLowerCase();
    item.append(walkLink('view__here-link', one.label, { show: one.address, docs: from!.docs }),
                element('span', 'view__here-kind', one.address.kind));
    return item;
  }));
  const families = listed.filter((one) => one.address.kind === 'family').length;
  const projects = listed.length - families;
  hereSummary.textContent = [families ? `${families} ${families === 1 ? 'family' : 'families'}` : '',
                             projects ? `${projects} ${projects === 1 ? 'project' : 'projects'}` : '']
    .filter(Boolean).join(' and ') + ' to open';
  hereFilter.value = '';
  hereFilter.hidden = listed.length < 8;
  here.hidden = !listed.length;
  here.open = false;
  say(hint, !graph ? null : listed.length
    ? 'Double-click a family or a project to open it, or choose it from the list. Scroll to zoom; drag the background to move.'
    : 'Scroll to zoom; drag the background to move.');
  copy.hidden = !inHand?.page;
}

hereFilter.addEventListener('input', () => {
  const needle = hereFilter.value.trim().toLowerCase();
  for (const item of hereList.children as HTMLCollectionOf<HTMLElement>) {
    item.hidden = !!needle && !(item.dataset.name ?? '').includes(needle);
  }
});
hereFilter.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter') return;
  // Enter opens the one name the filter leaves.
  const left = [...hereList.children as HTMLCollectionOf<HTMLElement>].filter((item) => !item.hidden);
  if (left.length === 1) left[0].querySelector('a')?.click();
});
// Opened, the list is typed into; Escape, or a click anywhere else, folds it again.
here.addEventListener('toggle', () => {
  if (here.open) (hereFilter.hidden ? hereList.querySelector('a') : hereFilter)?.focus();
});
here.addEventListener('keydown', (event) => {
  if (event.key !== 'Escape' || !here.open) return;
  here.open = false;
  hereSummary.focus();
});
document.addEventListener('click', (event) => {
  if (here.open && !here.contains(event.target as Node)) here.open = false;
});

/**
 * Draw `view` of a document in hand, or say why not. A page address is
 * written to the address bar once it is drawn: `push` adds a history entry,
 * `replace` rewrites this one, `none` leaves the address as it is.
 */
function show(data: unknown, handed: Handed, page: PageAddress | null, view: string | null,
              history: 'push' | 'replace' | 'none'): void {
  const reading = readDocument(data, view);
  if ('refused' in reading) {
    if (!drawing) {
      // Nothing drawn yet: the first of its views this page draws is drawn
      // under the refusal, and the address says so; with none, its views
      // are still offered.
      const drawable = viewsOf(data).find((choice) => !choice.refused);
      if (drawable) {
        show(data, handed, page, drawable.view, page ? 'replace' : 'none');
      } else {
        held = { data, handed, page, view: null };
        walkBar(null, null, null);
      }
    }
    refused(reading.refused, handed);
    return;
  }
  learnFrom(known, data);
  held = { data, handed, page, view: reading.drawing.view };
  drawn(reading.drawing, handed);
  walkBar(reading.drawing.view, reading.drawing.document, reading.drawing.subject);
  if (page && history !== 'none') {
    const search = formatPage(reading.drawing.view ? atView(page, reading.drawing.view) : page);
    if (history === 'push') window.history.pushState(null, '', search);
    else window.history.replaceState(null, '', search);
  }
  askIndex();
}

/** A document read, or why it could not be. */
type Fetched = { data: unknown } | { refused: Refusal };
const documents = new Map<string, Promise<Fetched>>();

/** Read a document by URL once a visit; a failed read is read again when it is asked for again. */
function fetchDocument(url: string): Promise<Fetched> {
  let asked = documents.get(url);
  if (!asked) {
    asked = (async (): Promise<Fetched> => {
      let answer: Response;
      try {
        answer = await fetch(url, { credentials: 'omit' });
      } catch (error) {
        return { refused: { problem: `${url} could not be read (${(error as Error).message})`,
                            remedy: 'check the address; a host serving it to this page must allow its origin (access-control-allow-origin)' } };
      }
      if (!answer.ok) {
        return { refused: { problem: `${url} answered ${answer.status}${answer.statusText ? ` ${answer.statusText}` : ''}`,
                            remedy: 'check the address' } };
      }
      const text = await answer.text();
      try {
        return { data: JSON.parse(text) };
      } catch (error) {
        return { refused: { problem: `it is not JSON (${(error as Error).message})`,
                            remedy: 'hand it the document itself, as JSON' } };
      }
    })();
    documents.set(url, asked);
    void asked.then((fetched) => { if ('refused' in fetched) documents.delete(url); });
  }
  return asked;
}

/** Where a page address's document is, as an absolute URL; a refusal when it is none the page reads. */
function locate(address: PageAddress): { url: string } | { refused: Refusal } {
  const raw = 'doc' in address ? address.doc : documentUrl(address.docs, address.show);
  let url: string;
  try {
    url = new URL(raw, window.location.href).href;
  } catch {
    return { refused: { problem: `${raw} is not an address`, remedy: 'name the document with ?doc=https://...' } };
  }
  const unreadable = readableUrl(url);
  return unreadable ? { refused: unreadable } : { url };
}

/** Open a page address: read its document, and draw it at its view. Only the latest asked for is drawn. */
async function go(address: PageAddress, history: 'push' | 'replace' | 'none', bare = false): Promise<void> {
  const number = ++asking;
  const located = locate(address);
  if ('refused' in located) {
    refused(located.refused, 'doc' in address ? { kind: 'url', url: address.doc } : null);
    return;
  }
  const handed: Handed = { kind: 'url', url: located.url };
  const fetched = await fetchDocument(located.url);
  if (number !== asking) return;
  if ('refused' in fetched) {
    if (bare) {
      // The page's own address, with no show folder beside it: it opens on its ways in.
      say(emptyWhy, `No show documents are beside this page: ${fetched.refused.problem}.`);
      return;
    }
    const subjectOf = (show: ShowAddress) => (show.kind === 'index' ? 'index' : `${show.kind}:${show.name}`);
    refused('show' in address && /answered 404/.test(fetched.refused.problem)
      ? { problem: `the show folder holds no document for ${subjectOf(address.show)} (${fetched.refused.problem})`,
          remedy: 'open it in codecarto, which draws it from its clone',
          window: formatPage({ show: address.show, docs: null }) }
      : fetched.refused, handed);
    return;
  }
  show(fetched.data, handed, address, 'show' in address ? address.show.view : address.view, history);
}

/** Read the show folder's index once, for the trail: it names every family and what each holds. */
function askIndex(): void {
  const from = walked();
  if (!from || from.show.kind === 'index' || indexAsked.has(from.docs ?? '')) return;
  indexAsked.add(from.docs ?? '');
  const located = locate({ show: { kind: 'index', name: '', view: 'estate' }, docs: from.docs });
  if ('refused' in located) return;
  void fetchDocument(located.url).then((fetched) => {
    if (!('data' in fetched)) return;
    learnFrom(known, fetched.data);
    const now = held ? readDocument(held.data, held.view) : null;
    if (now && 'drawing' in now) walkBar(now.drawing.view, now.drawing.document, now.drawing.subject);
  });
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
  ++asking;
  show(data, handed, null, askedView, 'none');
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

copy.addEventListener('click', () => {
  const again = () => { copy.textContent = 'copy link'; };
  const copied = navigator.clipboard?.writeText(window.location.href) ?? Promise.reject(new Error('no clipboard'));
  copied.then(
    () => { copy.textContent = 'copied'; window.setTimeout(again, 2000); },
    () => { copy.textContent = 'the address bar holds it'; window.setTimeout(again, 4000); },
  );
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
  // A paste into the list's filter is the filter's.
  if (event.target instanceof HTMLInputElement) return;
  const file = event.clipboardData?.files?.[0];
  if (file) {
    void readFile(file);
    return;
  }
  const pasted = event.clipboardData?.getData('text/plain');
  if (pasted?.trim()) read(pasted, { kind: 'paste' });
});

// A double-click on a family or a project opens it, as the window's does.
window.addEventListener(SHOW_OPEN_EVENT, (event) => {
  const from = walked();
  const address = fromNode((event as CustomEvent<unknown>).detail);
  if (from && address) void go({ show: address, docs: from.docs }, 'push');
});

// Back and Forward walk the drawings, each drawn again from the document read.
window.addEventListener('popstate', () => {
  const reading = readPage(window.location.search);
  if ('address' in reading) void go(reading.address, 'none', reading.bare);
});

const opening = readPage(window.location.search);
if ('refused' in opening) refused(opening.refused, null);
else void go(opening.address, 'none', opening.bare);
