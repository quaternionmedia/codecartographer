/**
 * The graph's key, as an extension.
 *
 * **WHY AN EXTENSION AND NOT RENDERER CODE.** A legend that lives inside one
 * renderer belongs to one rendering path, and this project has had two.
 * `ExtensionContext` is the seam every renderer can supply, so mounting here
 * gives the key to whatever canvas is drawing rather than to whichever file
 * happens to own the code. ADR §7.
 *
 * **IT READS THE GRAPH RATHER THAN DESCRIBING IT.** A key written as literal
 * HTML names the kinds its author expected, whether or not the graph holds any
 * — a claim about the data made by a file that never looked at the data. Every
 * row here comes from the nodes and edges actually rendered, so an empty
 * section is an empty section.
 *
 * What the rows *mean* is decided in `legend_marks.ts`, which is pure and
 * tested under `node --test`. This file draws what it is given and decides
 * nothing. A swatch is `swatchPath` filled with the mark's colour -- the
 * canvas's path, sides and all, and its fill under the current "Color By" --
 * so a swatch and a node cannot disagree.
 */

import * as d3 from 'd3';

import { BaseExtension } from './base';
import type { GraphNode, GraphEdge } from '../services/graph_types';
import { DOT_OPACITY } from '../services/showcase';
import type { ShowcaseOptions } from '../services/showcase';
import { constructMarks, edgeMarks, layerMarks, nodeLabel, nodeMarks, readable, showcaseKey, swatchPath } from './legend_marks';
import type { ConstructMark, EdgeMark, KeyEntry, LayerMark, NodeMark } from './legend_marks';
import './legend_extension.css';

const SWATCH = 16;

/** A Showcase's key, in the canvas's pixels: its words, a dot's radius, a link's length, a row, the gaps. */
const KEY = { font: 11, dot: 4, line: 14, row: 16, margin: 12, gap: 12, group: 22 };

export class LegendExtension extends BaseExtension<GraphNode, GraphEdge> {
  private root: HTMLDivElement | null = null;
  private expanded = false;
  /** A Showcase's key, drawn in the canvas's svg; what it says; and the width it was laid out to. */
  private key: SVGSVGElement | null = null;
  private keyed: { dots: KeyEntry[]; links: KeyEntry[] } | null = null;
  private keyWidth = 0;
  private resized: ResizeObserver | null = null;

  /**
   * @param colorBy The colouring the canvas is drawn with, read each time the
   *   key is built: the key describes the colours on screen, and those follow
   *   "Color By".
   * @param showcase The Showcase the canvas is drawn as, or none: read each
   *   time the key is built, as a link switched off is drawn off in place.
   */
  constructor(
    private readonly colorBy: () => string | undefined = () => 'auto',
    private readonly showcase: () => ShowcaseOptions | null = () => null,
  ) {
    super('legend', 'Legend', 'A key built from the nodes and edges actually drawn');
  }

  public apply(): void {
    const ctx = this.assertContext();
    this.destroyDom();
    // **A CANVAS CARRIES ONE KEY.** Each key removed only the one it drew, so
    // a second mounted on the same canvas -- a second subscriber, in a page
    // kept open while the demo updated itself -- was drawn exactly over the
    // first, the same counts twice. Whatever key the canvas holds goes.
    for (const other of ctx.container.querySelectorAll(':scope > .graph-legend')) other.remove();
    ctx.svg.selectAll(':scope > svg.showcase-key').remove();
    if (!this.enabled) return;

    const nodes = ctx.data.nodes ?? [];
    const edges = ctx.data.edges ?? [];
    const colorBy = this.colorBy();
    const showcase = this.showcase();
    if (showcase) {
      this.keyed = showcaseKey(nodes, edges, showcase.links, colorBy);
      this.drawKey();
      this.resized = new ResizeObserver(() => this.drawKey());
      this.resized.observe(ctx.container);
      return;
    }
    const nodes_ = nodeMarks(nodes, colorBy);
    const edges_ = edgeMarks(edges);
    const layers_ = layerMarks(nodes, colorBy);
    const constructs_ = constructMarks(nodes, colorBy);

    const root = document.createElement('div');
    root.className = 'graph-legend';
    this.root = root;

    const header = document.createElement('button');
    header.type = 'button';
    header.className = 'graph-legend__header';
    header.setAttribute('aria-expanded', String(this.expanded));
    header.textContent = `${nodes.length} nodes · ${edges.length} edges`;

    const caret = document.createElement('span');
    caret.className = 'graph-legend__caret';
    caret.setAttribute('aria-hidden', 'true');
    caret.textContent = this.expanded ? '▴' : '▾';
    header.appendChild(caret);

    const body = document.createElement('div');
    body.className = 'graph-legend__body';
    // Rebuilt when "Color By" changes; a key the reader had open stays open.
    body.hidden = !this.expanded;

    if (nodes_.length) {
      body.appendChild(this.section('Nodes', nodes_.map((m) => this.nodeRow(m))));
    }
    if (edges_.length) {
      body.appendChild(this.section('Edges', edges_.map((m) => this.edgeRow(m))));
    }
    if (layers_.length) {
      body.appendChild(this.section('Abstraction layers', layers_.map((m) => this.layerRow(m))));
    }
    if (constructs_.length) {
      body.appendChild(this.section('Constructs', constructs_.map((m) => this.constructRow(m))));
    }
    if (!nodes_.length && !edges_.length) {
      const empty = document.createElement('p');
      empty.className = 'graph-legend__empty';
      empty.textContent = 'Nothing drawn yet.';
      body.appendChild(empty);
    }

    const toggle = () => {
      this.expanded = !this.expanded;
      body.hidden = !this.expanded;
      caret.textContent = this.expanded ? '▴' : '▾';
      header.setAttribute('aria-expanded', String(this.expanded));
    };
    header.addEventListener('click', toggle);

    root.append(header, body);
    ctx.container.appendChild(root);
  }

  private section(title: string, rows: HTMLElement[]): HTMLElement {
    const section = document.createElement('section');
    section.className = 'graph-legend__section';
    const heading = document.createElement('h4');
    heading.className = 'graph-legend__heading';
    heading.textContent = title;
    section.appendChild(heading);
    for (const row of rows) section.appendChild(row);
    return section;
  }

  private row(swatch: SVGSVGElement, label: string, count: number): HTMLElement {
    const row = document.createElement('div');
    row.className = 'graph-legend__row';
    row.appendChild(swatch);
    const name = document.createElement('span');
    name.className = 'graph-legend__label';
    name.textContent = label;
    const tally = document.createElement('span');
    tally.className = 'graph-legend__count';
    tally.textContent = String(count);
    row.append(name, tally);
    return row;
  }

  private nodeRow(mark: NodeMark): HTMLElement {
    const svg = d3
      .create('svg')
      .attr('width', SWATCH)
      .attr('height', SWATCH)
      .attr('class', 'graph-legend__swatch')
      .attr('aria-hidden', 'true');
    svg
      .append('path')
      .attr('d', swatchPath(mark, SWATCH / 2 - 2))
      .attr('transform', `translate(${SWATCH / 2},${SWATCH / 2})`)
      .attr('fill', mark.color)
      .attr('stroke', 'currentColor')
      .attr('stroke-width', 1);
    return this.row(svg.node() as SVGSVGElement, nodeLabel(mark), mark.count);
  }

  private layerRow(mark: LayerMark): HTMLElement {
    const svg = d3
      .create('svg')
      .attr('width', SWATCH)
      .attr('height', SWATCH)
      .attr('class', 'graph-legend__swatch')
      .attr('aria-hidden', 'true');
    svg
      .append('rect')
      .attr('x', 2)
      .attr('y', 2)
      .attr('width', SWATCH - 4)
      .attr('height', SWATCH - 4)
      .attr('fill', mark.color);
    return this.row(svg.node() as SVGSVGElement, mark.label, mark.count);
  }

  private constructRow(mark: ConstructMark): HTMLElement {
    const svg = d3
      .create('svg')
      .attr('width', SWATCH)
      .attr('height', SWATCH)
      .attr('class', 'graph-legend__swatch')
      .attr('aria-hidden', 'true');
    svg
      .append('circle')
      .attr('cx', SWATCH / 2)
      .attr('cy', SWATCH / 2)
      .attr('r', SWATCH / 2 - 2)
      .attr('fill', mark.color);
    const row = this.row(svg.node() as SVGSVGElement, mark.name, mark.count);
    row.dataset.construct = mark.construct;
    return row;
  }

  private edgeRow(mark: EdgeMark): HTMLElement {
    const svg = d3
      .create('svg')
      .attr('width', SWATCH * 1.75)
      .attr('height', SWATCH)
      .attr('class', 'graph-legend__swatch')
      .attr('aria-hidden', 'true');
    svg
      .append('line')
      .attr('x1', 1)
      .attr('y1', SWATCH / 2)
      .attr('x2', SWATCH * 1.75 - 1)
      .attr('y2', SWATCH / 2)
      .attr('stroke', mark.color)
      .attr('stroke-width', 2);
    return this.row(svg.node() as SVGSVGElement, readable(mark.kind), mark.count);
  }

  /**
   * A Showcase's key: a line of dots and links, each with its word, at the
   * canvas's bottom left, wrapped to the canvas's width and laid out again
   * as that changes. No count, no heading, no box: the picture is the dots.
   *
   * **IN THE CANVAS'S SVG, NOT OVER IT.** A showgraph's picture is the
   * canvas's svg (`web/tests/export`), so a key drawn over the canvas, as the
   * collapsible one is, never reaches a picture. Drawn in the svg, outside the
   * zoomed drawing, it stays put as the drawing pans and is in every picture
   * taken; a nested svg at `y="100%"` keeps it at the bottom as the canvas is
   * resized. Drawn after the drawing, as the exporter reads the svg's first
   * group for the zoom, and at full opacity, as it takes a picture only once
   * nothing is part-faded.
   */
  private drawKey(): void {
    const ctx = this.context;
    const keyed = this.keyed;
    if (!ctx || !keyed) return;
    // A canvas not yet laid out is as wide as the key: it is laid out again once it is.
    const room = ctx.container.clientWidth || Infinity;
    if (this.key?.isConnected && room === this.keyWidth) return;
    this.key?.remove();
    this.key = null;
    this.keyWidth = room;
    const entries = [
      ...keyed.dots.map((entry) => ({ ...entry, line: false })),
      ...keyed.links.map((entry) => ({ ...entry, line: true })),
    ];
    if (!entries.length) return;

    const key = ctx.svg.append('svg')
      .attr('class', 'showcase-key')
      .attr('x', 0)
      .attr('y', '100%')
      .attr('overflow', 'visible');
    const body = key.append('g');
    let x = 0;
    let row = 0;
    let last: boolean | null = null;
    for (const entry of entries) {
      const item = body.append('g').attr('class', 'showcase-key__entry');
      const swatch = entry.line ? KEY.line : 2 * KEY.dot;
      if (entry.line) {
        item.append('line').attr('x2', KEY.line).attr('stroke', entry.color).attr('stroke-width', 2);
      } else {
        item.append('circle').attr('cx', KEY.dot).attr('r', KEY.dot)
          .attr('fill', entry.color).attr('fill-opacity', DOT_OPACITY);
      }
      const text = item.append('text')
        .attr('x', swatch + 4)
        .attr('dominant-baseline', 'central')
        .attr('font-size', KEY.font)
        .text(entry.label);
      const width = swatch + 4 + (text.node()!.getComputedTextLength() || entry.label.length * KEY.font * 0.6);
      // A little apart from the next; the links further, from the dots.
      const lead = last === null ? 0 : entry.line === last ? KEY.gap : KEY.group;
      if (x > 0 && x + lead + width > room - 2 * KEY.margin) {
        row += 1;
        x = 0;
      } else {
        x += lead;
      }
      item.attr('transform', `translate(${x},${row * KEY.row})`);
      x += width;
      last = entry.line;
    }
    body.attr('transform', `translate(${KEY.margin},${-(KEY.margin + KEY.row / 2 + row * KEY.row)})`);
    this.key = key.node();
  }

  private destroyDom(): void {
    this.root?.remove();
    this.root = null;
    this.resized?.disconnect();
    this.resized = null;
    this.key?.remove();
    this.key = null;
    this.keyed = null;
    this.keyWidth = 0;
  }

  public destroy(): void {
    this.destroyDom();
    super.destroy();
  }
}
