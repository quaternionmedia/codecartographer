/**
 * The harness's run state, drawn on the boxes it names.
 *
 * An extension on the one canvas: it sets `data-run-state` on each drawn
 * node whose address names a project the harness gave a state, and the
 * stylesheet beside this file draws the mark. It adds no renderer and no
 * element; a node with no state carries no attribute.
 *
 * Which box takes which state is decided in `run_state.ts`, which is pure and
 * tested under node. This file reads the states it is handed each time it is
 * applied, so a newer reading is drawn by calling `apply` again.
 */

import { BaseExtension } from './base';
import type { GraphNode, GraphEdge } from '../services/graph_types';
import { joinStates } from '../../estate/run_state';
import type { RunState } from '../../estate/run_state';
import './run_state_extension.css';

export const RUN_STATE_ATTRIBUTE = 'data-run-state';

export class RunStateExtension extends BaseExtension<GraphNode, GraphEdge> {
  /**
   * @param states The states of the newest reading, or an empty list when
   *   there is none; read on every `apply`.
   */
  constructor(private readonly states: () => readonly RunState[]) {
    super('run-state', 'Run state', 'What the harness is running, on the boxes it names');
  }

  public apply(): void {
    const ctx = this.assertContext();
    const joined = this.enabled
      ? joinStates(this.states(), ctx.data.nodes ?? [])
      : { byNode: {}, unmatched: [] };
    ctx.nodes.each(function (node) {
      const state = joined.byNode[node.id];
      if (state) {
        this.setAttribute(RUN_STATE_ATTRIBUTE, state.state);
        this.setAttribute('data-run-because', state.because);
      } else {
        this.removeAttribute(RUN_STATE_ATTRIBUTE);
        this.removeAttribute('data-run-because');
      }
    });
  }

  public destroy(): void {
    if (this.context) {
      this.context.nodes.each(function () {
        this.removeAttribute(RUN_STATE_ATTRIBUTE);
        this.removeAttribute('data-run-because');
      });
    }
    super.destroy();
  }
}
