/**
 * The intent router: rad's outbound half, joined to this application.
 *
 * Every verb lands in exactly one of two places, and the split is the whole
 * design (integration standard §5.1):
 *
 *   STATE   hide · pin · color:* · expand · collapse · delete
 *           fold into application state. The renderer derives from it, so
 *           the effect survives a re-render, a relayout and a cache replay.
 *
 *   VIEW    fit · relayout · spread · cluster · toggle-physics ·
 *           select-neighbors · clear-selection · focus-group
 *           are camera and selection operations. They own no graph facts,
 *           so routing them through the store would add a write that
 *           nothing reads back.
 *
 * `view-source` and `node-info` are neither: they leave the canvas entirely.
 *
 * A verb that is not handled throws rather than being ignored. A silently
 * dropped intent is indistinguishable from a working one at the call site,
 * and that is precisely how the legacy menu shipped stubbed edge actions.
 */
import type { Intent } from '../core/types.js';
import { colourTokenOf } from './view_state.js';

/**
 * What a host renderer must provide. Deliberately a flat record of small
 * operations rather than a renderer handle: the router cannot reach past
 * what is on this interface, which is the same property that keeps rad off
 * the scene.
 */
export interface GraphOps {
  // ── state-layer ────────────────────────────────────────────────────────
  hide(ids: string[]): void;
  showHidden(): void;
  togglePin(ids: string[]): void;
  colour(ids: string[], token: string): void;
  remove(ids: string[]): void;
  /** Async: reaches the parser. Rejection is the caller's to surface. */
  expand(ids: string[]): Promise<void>;
  collapse(ids: string[]): void;

  // ── camera and selection ───────────────────────────────────────────────
  fit(): void;
  relayout(): void;
  spread(): void;
  cluster(): void;
  togglePhysics(): void;
  selectNeighbors(ids: string[]): void;
  clearSelection(): void;
  focusGroup(id: string): void;

  // ── leaves the canvas ──────────────────────────────────────────────────
  viewSource(id: string): void;
  showInfo(id: string): void;
}

export interface RouterOptions {
  ops: GraphOps;
  /** Surface an async failure. Defaults to rethrowing on the microtask queue. */
  onError?: (verb: string, err: unknown) => void;
}

export function createIntentRouter(opts: RouterOptions): (intent: Intent) => void {
  const { ops, onError } = opts;

  const fail = (verb: string, err: unknown) => {
    if (onError) onError(verb, err);
    // Rethrow off the call stack so an unhandled failure reaches the host's
    // error reporting instead of dying inside a promise nobody awaited.
    // `Promise.resolve().then` rather than `queueMicrotask`: this file
    // compiles with no DOM and no node typings, and that is the check
    // keeping it portable.
    else void Promise.resolve().then(() => { throw err; });
  };

  return function route(intent: Intent): void {
    const { action, context } = intent;
    const ids = context.targetIds;
    const first = ids[0];

    const token = colourTokenOf(action);
    if (token) {
      ops.colour(ids, token);
      return;
    }

    switch (action) {
      // state
      case 'hide': ops.hide(ids); return;
      case 'show-hidden': ops.showHidden(); return;
      case 'pin': ops.togglePin(ids); return;
      case 'delete': ops.remove(ids); return;
      case 'collapse': ops.collapse(ids); return;
      case 'expand':
        ops.expand(ids).catch((e) => fail('expand', e));
        return;

      // camera and selection
      case 'fit': ops.fit(); return;
      case 'relayout': ops.relayout(); return;
      case 'spread': ops.spread(); return;
      case 'cluster': ops.cluster(); return;
      case 'toggle-physics': ops.togglePhysics(); return;
      case 'select-neighbors': ops.selectNeighbors(ids); return;
      case 'clear-selection': ops.clearSelection(); return;
      case 'focus-group':
        if (first) ops.focusGroup(first);
        return;

      // off-canvas
      case 'view-source':
        if (first) ops.viewSource(first);
        return;
      case 'node-info':
        if (first) ops.showInfo(first);
        return;

      default:
        throw new Error(
          `rad: no handler for verb '${action}'. Every verb the resolver can ` +
            `commit must be routed — a dropped intent looks exactly like a ` +
            `working one from the menu.`,
        );
    }
  };
}
