/**
 * The harness's run state, drawn on the boxes it names.
 *
 * An extension on the one canvas: each drawn node whose address names a
 * project the harness gave a state carries `data-run-state` and a ring around
 * its shape, which the stylesheet beside this file colours. A node with no
 * state carries neither. It adds no renderer.
 *
 * Which box takes which state is decided in `run_state.ts`, which is pure and
 * tested under node. This file reads the states it is handed each time it is
 * applied, so a newer reading is drawn by calling `apply` again.
 *
 * The canvas draws a graph's nodes over several frames after it announces
 * itself, so the nodes are read from the page on every `apply`, and nodes
 * drawn later are marked as they arrive.
 */

import { BaseExtension } from './base';
import type { GraphNode, GraphEdge } from '../services/graph_types';
import { joinStates } from '../../estate/run_state';
import type { RunState } from '../../estate/run_state';
import './run_state_extension.css';

export const RUN_STATE_ATTRIBUTE = 'data-run-state';
const BECAUSE_ATTRIBUTE = 'data-run-because';
const RING_CLASS = 'run-state-ring';
const SVG = 'http://www.w3.org/2000/svg';

/** How far outside the shape the ring sits, as a share of the shape's radius. */
const RING_CLEARANCE = 1.45;

type Drawn = SVGGElement & { __data__?: GraphNode };

export class RunStateExtension extends BaseExtension<GraphNode, GraphEdge> {
  private observer: MutationObserver | null = null;
  private pending = false;

  /**
   * @param states The states of the newest reading, or an empty list when
   *   there is none; read on every `apply`.
   */
  constructor(private readonly states: () => readonly RunState[]) {
    super('run-state', 'Run state', 'What the harness is running, on the boxes it names');
  }

  public apply(): void {
    const ctx = this.assertContext();
    this.mark();
    if (this.observer) return;
    const group = ctx.graphGroup.node();
    if (!group || typeof MutationObserver === 'undefined') return;
    // Nodes being added or removed. `mark` changes nothing on a node that is
    // already as it should be, so the ring it adds does not set it off again.
    this.observer = new MutationObserver(() => {
      if (this.pending) return;
      this.pending = true;
      requestAnimationFrame(() => {
        this.pending = false;
        if (this.context) this.mark();
      });
    });
    this.observer.observe(group, { childList: true, subtree: true });
  }

  /** Set or clear the mark on every node in the page now. */
  private mark(): void {
    const ctx = this.assertContext();
    const drawn = Array.from(
      ctx.container.querySelectorAll<Drawn>('g.graph-node'),
    ).filter((el) => el.__data__ && typeof el.__data__.id === 'string');
    const joined = this.enabled
      ? joinStates(this.states(), drawn.map((el) => el.__data__ as GraphNode))
      : { byNode: {} as Record<string, RunState>, unmatched: [] };
    for (const el of drawn) {
      const state = joined.byNode[(el.__data__ as GraphNode).id];
      if (state) {
        if (el.getAttribute(RUN_STATE_ATTRIBUTE) !== state.state) el.setAttribute(RUN_STATE_ATTRIBUTE, state.state);
        if (el.getAttribute(BECAUSE_ATTRIBUTE) !== state.because) el.setAttribute(BECAUSE_ATTRIBUTE, state.because);
        this.ring(el);
      } else if (el.hasAttribute(RUN_STATE_ATTRIBUTE)) {
        RunStateExtension.clear(el);
      }
    }
  }

  /** The ring around a node's shape, added once and sized from the shape. */
  private ring(el: Drawn): void {
    if (el.querySelector(`:scope > .${RING_CLASS}`)) return;
    const shape = el.querySelector<SVGGraphicsElement>(':scope > path');
    let radius = 12;
    try {
      const box = shape?.getBBox();
      if (box && box.width > 0) radius = (Math.max(box.width, box.height) / 2) * RING_CLEARANCE;
    } catch {
      // A shape not laid out yet has no box; the default radius stands.
    }
    const ring = document.createElementNS(SVG, 'circle');
    ring.setAttribute('class', RING_CLASS);
    ring.setAttribute('r', String(radius));
    el.appendChild(ring);
  }

  private static clear(el: Element): void {
    el.removeAttribute(RUN_STATE_ATTRIBUTE);
    el.removeAttribute(BECAUSE_ATTRIBUTE);
    el.querySelector(`:scope > .${RING_CLASS}`)?.remove();
  }

  public destroy(): void {
    this.observer?.disconnect();
    this.observer = null;
    if (this.context) {
      for (const el of this.context.container.querySelectorAll('g.graph-node')) RunStateExtension.clear(el);
    }
    super.destroy();
  }
}
