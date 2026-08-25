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
 * nothing. Shapes come from `nodePath`, the same function the canvas draws
 * with, so a swatch and a node cannot disagree.
 */

import * as d3 from 'd3';

import { BaseExtension } from './base';
import type { GraphNode, GraphEdge } from '../services/graph_renderer';
import { nodePath } from '../services/node_shapes';
import { edgeMarks, nodeMarks, readable } from './legend_marks';
import type { EdgeMark, NodeMark } from './legend_marks';
import './legend_extension.css';

const SWATCH = 16;

export class LegendExtension extends BaseExtension<GraphNode, GraphEdge> {
  private root: HTMLDivElement | null = null;
  private expanded = false;

  constructor() {
    super('legend', 'Legend', 'A key built from the nodes and edges actually drawn');
  }

  public apply(): void {
    const ctx = this.assertContext();
    this.destroyDom();
    if (!this.enabled) return;

    const nodes = ctx.data.nodes ?? [];
    const edges = ctx.data.edges ?? [];
    const nodes_ = nodeMarks(nodes);
    const edges_ = edgeMarks(edges);

    const root = document.createElement('div');
    root.className = 'graph-legend';
    this.root = root;

    const header = document.createElement('button');
    header.type = 'button';
    header.className = 'graph-legend__header';
    header.setAttribute('aria-expanded', 'false');
    header.textContent = `${nodes.length} nodes · ${edges.length} edges`;

    const caret = document.createElement('span');
    caret.className = 'graph-legend__caret';
    caret.setAttribute('aria-hidden', 'true');
    caret.textContent = '▾';
    header.appendChild(caret);

    const body = document.createElement('div');
    body.className = 'graph-legend__body';
    body.hidden = true;

    if (nodes_.length) {
      body.appendChild(this.section('Nodes', nodes_.map((m) => this.nodeRow(m))));
    }
    if (edges_.length) {
      body.appendChild(this.section('Edges', edges_.map((m) => this.edgeRow(m))));
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
      .attr('d', nodePath(mark.shape, SWATCH / 2 - 2))
      .attr('transform', `translate(${SWATCH / 2},${SWATCH / 2})`)
      .attr('fill', mark.color)
      .attr('stroke', 'currentColor')
      .attr('stroke-width', 1);
    return this.row(svg.node() as SVGSVGElement, readable(mark.kind), mark.count);
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

  private destroyDom(): void {
    this.root?.remove();
    this.root = null;
  }

  public destroy(): void {
    this.destroyDom();
    super.destroy();
  }
}
