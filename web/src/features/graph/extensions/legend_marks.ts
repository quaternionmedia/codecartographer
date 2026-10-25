/**
 * What a legend says, separated from how it is drawn.
 *
 * **THE LESSON THIS FILE IS BUILT ON.** rad's integration review found three
 * verbs that were one `fitView()` call wearing three labels, and the suite
 * stayed green because the spy sat at the operation boundary and never read an
 * operation body. Op bodies were application code that no test build compiled.
 * A legend has the same shape of risk: the DOM is easy to assert and says
 * nothing, while the interesting question — *does the key describe the graph
 * that was actually drawn* — lives in these two functions.
 *
 * So they are pure, DOM-free, and compiled by `tsconfig.pure.json` for
 * `node --test`. `legend_extension.ts` renders what they return and decides
 * nothing itself.
 */

// `.js`, so the build `node --test` reads resolves it as the bundler does.
import { nodePath, nodeSides, polygonSides } from '../services/node_shapes.js';

/** A node kind, and the mark that stands for it. */
export interface NodeMark {
  kind: string;
  shape: string | undefined;
  /** The side count a record (`ngon`) is drawn with; absent for every other shape. */
  sides?: number;
  color: string;
  count: number;
}

/** An edge kind, and the mark that stands for it. */
export interface EdgeMark {
  kind: string;
  color: string;
  count: number;
}

/** The fields a mark is derived from. Deliberately narrower than `GraphNode`. */
export interface MarkableNode {
  kind?: unknown;
  shape?: unknown;
  color?: unknown;
  meta?: unknown;
  layer_color?: unknown;
  construct_color?: unknown;
}

export interface MarkableEdge {
  kind?: unknown;
  label?: unknown;
  color?: unknown;
}

export const DEFAULT_NODE_KIND = 'node';
export const DEFAULT_NODE_COLOR = 'steelblue';
export const DEFAULT_EDGE_KIND = 'edge';
export const DEFAULT_EDGE_COLOR = '#555';

/** `async_function` -> `Async function`. Display only; never a key. */
export function readable(kind: string): string {
  const spaced = kind.replace(/[_-]+/g, ' ').trim();
  return spaced ? spaced[0].toUpperCase() + spaced.slice(1) : kind;
}

/**
 * The distinct node marks present, most common first.
 *
 * **KEYED ON KIND *AND* MARK.** One kind drawn two ways is two rows: a reader
 * matching a swatch against a node needs the row that matches what is on
 * screen, and collapsing them yields a key that is right on average and wrong
 * in front of them.
 *
 * **A NODE WITH NO KIND IS COUNTED, NOT DROPPED.** The counts have to add up to
 * the picture, or the key becomes a second, quieter claim about how much of the
 * graph the reader is seeing.
 *
 * **THE MARK IS WHAT THE CANVAS DREW, UNDER THE COLOURING IT WAS DRAWN WITH.**
 * A record's side count is part of its mark -- the key drew every one as the
 * default pentagon -- and its fill is `drawnFill` under `colorBy`: the key kept
 * each node's own colour while "Color By: Abstraction Layer" painted the canvas
 * by layer.
 */
export function nodeMarks(nodes: readonly MarkableNode[], colorBy: string | undefined = 'auto'): NodeMark[] {
  const seen = new Map<string, NodeMark>();
  for (const node of nodes) {
    const kind = typeof node.kind === 'string' && node.kind ? node.kind : DEFAULT_NODE_KIND;
    const shape = typeof node.shape === 'string' && node.shape ? node.shape : undefined;
    const sides = shape === 'ngon' ? polygonSides(nodeSides(node)) : undefined;
    const color = drawnFill(node, colorBy);
    const key = `${kind}|${shape ?? ''}|${sides ?? ''}|${color}`;
    const found = seen.get(key);
    if (found) found.count += 1;
    else seen.set(key, sides === undefined ? { kind, shape, color, count: 1 } : { kind, shape, sides, color, count: 1 });
  }
  return [...seen.values()].sort((a, b) => b.count - a.count);
}

/**
 * The fill the canvas draws a node with, under the chosen colouring -- the
 * renderer's and the key's one decision.
 *
 * **"COLOR BY: ABSTRACTION LAYER" PAINTS `layer_color`, WHICH THE SERVER SETS.**
 * The ramp lives with the lexicons (`construct_service.LAYER_RAMP`), so a node
 * the server placed on a layer and sent no colour for keeps its own, as the
 * control's tooltip says, rather than this side guessing a colour for it.
 *
 * **"COLOR BY: CONSTRUCT" PAINTS `construct_color`, WHICH THE SERVER STAMPS.**
 * What a node is, in one colour across languages -- a C struct and a Rust
 * struct alike, whatever look each parser gave them. A node the vocabulary did
 * not place keeps its own colour.
 */
export function drawnFill(node: MarkableNode, colorBy: string | undefined): string {
  return paintedColor(node, colorBy) ?? DEFAULT_NODE_COLOR;
}

/**
 * `drawnFill` before the D3 canvas's default: undefined for a node with no
 * colour under this colouring, which the vis-network canvas leaves to its own
 * default (`vis_look.ts`). One rule for all three, so the second canvas
 * follows "Color By" as the first does.
 */
export function paintedColor(node: MarkableNode, colorBy: string | undefined): string | undefined {
  if (colorBy === 'layer' && typeof node.layer_color === 'string' && node.layer_color) {
    return node.layer_color;
  }
  if (colorBy === 'construct' && typeof node.construct_color === 'string' && node.construct_color) {
    return node.construct_color;
  }
  return typeof node.color === 'string' && node.color ? node.color : undefined;
}

/** The path a node row's swatch is drawn with, at half-extent `s`: the canvas's, sides and all. */
export function swatchPath(mark: NodeMark, s: number): string {
  return nodePath(mark.shape, s, mark.sides);
}

/** What a node row says; a record's says how many sides it is drawn with. */
export function nodeLabel(mark: NodeMark): string {
  const name = readable(mark.kind);
  return mark.sides === undefined ? name : `${name} · ${mark.sides} sides`;
}

/**
 * The distinct edge marks present, most common first.
 *
 * **`kind` IS READ BEFORE `label`.** A label is what one edge says about itself
 * and is often unique per edge, which would produce a key with one row per
 * edge — technically accurate and useless. `kind` is the field Q3 adds for
 * exactly this: a fact about the class of relation rather than the instance.
 */
export function edgeMarks(edges: readonly MarkableEdge[]): EdgeMark[] {
  const seen = new Map<string, EdgeMark>();
  for (const edge of edges) {
    const named =
      (typeof edge.kind === 'string' && edge.kind) ||
      (typeof edge.label === 'string' && edge.label) ||
      DEFAULT_EDGE_KIND;
    const color = typeof edge.color === 'string' && edge.color ? edge.color : DEFAULT_EDGE_COLOR;
    const key = `${named}|${color}`;
    const found = seen.get(key);
    if (found) found.count += 1;
    else seen.set(key, { kind: named, color, count: 1 });
  }
  return [...seen.values()].sort((a, b) => b.count - a.count);
}

/** Total nodes and edges the marks account for — the key's own arithmetic. */
export function marksCover(
  marks: readonly { count: number }[],
): number {
  return marks.reduce((total, mark) => total + mark.count, 0);
}

/** An abstraction layer present in the graph, and how many nodes sit on it. */
export interface LayerMark {
  /** The language whose lexicon placed the node; '' when the node did not say. */
  language: string;
  ordinal: number;
  /** The layer's name in the lexicon that placed the node, when the node said. */
  name: string;
  /** What the row says. */
  label: string;
  color: string;
  count: number;
}

export interface ConstructMark {
  construct: string;
  name: string;
  color: string;
  count: number;
}

export interface ConstructedNode extends MarkableNode {
  construct?: unknown;
  construct_name?: unknown;
  construct_color?: unknown;
  [key: string]: unknown;
}

/**
 * The constructs the canvas paints, most numerous first.
 *
 * **WHAT "COLOR BY: CONSTRUCT" MEANS, IN THE KEY.** The server stamps each node
 * the vocabulary places with its construct and that construct's colour and
 * name; the key names each and counts it, so a C struct and a Rust struct are
 * one row. A node the vocabulary did not place has no construct, and this
 * does not invent one.
 *
 * **ONLY WHERE THE CANVAS PAINTS A NODE IN ITS CONSTRUCT'S COLOUR**, as
 * `layerMarks` counts layers: `drawnFill` under the current colouring is the
 * construct's colour. Under "Auto" the crate graph's crates are drawn in the
 * Cargo panel's own colours, and the key listed Package in a purple nothing on
 * the canvas was painted with; a node whose own colour is its construct's (a
 * look the vocabulary gave it) is a construct row in any colouring.
 */
export function constructMarks(nodes: readonly ConstructedNode[], colorBy: string | undefined): ConstructMark[] {
  const seen = new Map<string, ConstructMark>();
  for (const node of nodes) {
    if (typeof node.construct !== 'string' || typeof node.construct_color !== 'string') continue;
    if (drawnFill(node, colorBy) !== node.construct_color) continue;
    const found = seen.get(node.construct);
    if (found) {
      found.count += 1;
      continue;
    }
    seen.set(node.construct, {
      construct: node.construct,
      name: typeof node.construct_name === 'string' ? node.construct_name : node.construct,
      color: node.construct_color,
      count: 1,
    });
  }
  return [...seen.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}

export interface LayeredNode {
  color?: unknown;
  language?: unknown;
  layer_ordinal?: unknown;
  layer_color?: unknown;
  meta?: unknown;
}

/**
 * The abstraction layers the canvas paints, machine-facing first.
 *
 * **WHAT "COLOR BY: ABSTRACTION LAYER" MEANS, IN THE KEY.** A colour that
 * carries a layer is a state, and no state rides on colour alone: the key names
 * each layer the canvas paints and counts its nodes. A node is counted when the
 * canvas paints it in its layer's colour: the server placed it
 * (`layer_ordinal`), sent the colour (`layer_color`), and `drawnFill` under the
 * current colouring is that colour. Under "Color By: Abstraction Layer" that is
 * every such node; under "Auto" only one whose own colour is its layer's, as
 * the chrestomathy's tokens are -- a C struct on layer 2 drawn in its own blue
 * is no layer row then. A node placed and sent no colour keeps its own, and is
 * a node row, not a layer row in a colour nothing drew.
 *
 * **AN ORDINAL IS A RANK IN ONE LEXICON.** Each language numbers its keyword
 * layers and its operator layers from 0, so one ordinal -- and so one colour --
 * is several layers: C's 0 and Python's 0, or C's keyword 0 and operator 0. A
 * row is one language's one named layer, and where the graph holds more than
 * one language each row says whose it is.
 */
export function layerMarks(nodes: readonly LayeredNode[], colorBy: string | undefined): LayerMark[] {
  const seen = new Map<string, LayerMark>();
  for (const node of nodes) {
    if (typeof node.layer_ordinal !== 'number' || node.layer_ordinal < 0) continue;
    if (typeof node.layer_color !== 'string' || !node.layer_color) continue;
    if (drawnFill(node, colorBy) !== node.layer_color) continue;
    const ordinal = node.layer_ordinal;
    const language = typeof node.language === 'string' ? node.language : '';
    const name = layerName(node.meta, ordinal);
    const color = node.layer_color;
    const key = `${language}|${ordinal}|${name}|${color}`;
    const found = seen.get(key);
    if (found) found.count += 1;
    else seen.set(key, { language, ordinal, name, label: '', color, count: 1 });
  }
  const marks = [...seen.values()];
  const multilingual = new Set(marks.map((m) => m.language).filter(Boolean)).size > 1;
  for (const mark of marks) {
    const layer = mark.name ? `L${mark.ordinal} ${mark.name}` : `Layer ${mark.ordinal}`;
    mark.label = multilingual && mark.language ? `${readable(mark.language)} · ${layer}` : layer;
  }
  return marks.sort((a, b) => a.ordinal - b.ordinal || a.label.localeCompare(b.label));
}

function layerName(meta: unknown, ordinal: number): string {
  const layers = (meta as { lexicon_layers?: unknown } | undefined)?.lexicon_layers;
  if (!Array.isArray(layers)) return '';
  const match = layers.find(
    (c) => (c as { layer_ordinal?: unknown }).layer_ordinal === ordinal,
  ) as { layer_name?: unknown } | undefined;
  return typeof match?.layer_name === 'string' ? match.layer_name : '';
}
