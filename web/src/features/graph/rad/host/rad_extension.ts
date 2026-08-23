/**
 * rad, mounted as a graph extension.
 *
 * This is the half that knows about codecartographer, and the only file in
 * `rad/` that imports application code. Everything above it is liftable.
 *
 * Why an extension rather than renderer code: `ExtensionContext` is the one
 * seam both renderers can supply, so mounting here is what puts the menu on
 * the streaming path — the path every real code map actually takes — instead
 * of only on the static renderer nothing reaches.
 */
import * as d3 from 'd3';
import { BaseExtension } from '../../extensions/base';
import type { ExtensionContext } from '../../extensions/base';
import type { GraphNode, GraphEdge } from '../../services/graph_renderer';
import type { Effect, MenuContext } from '../core/types.js';
import { createSession } from '../session.js';
import type { Session } from '../session.js';
import { attach } from '../dom/attach.js';
import type { Attachment } from '../dom/attach.js';
import { resolveGraphMenu } from './resolve.js';
import type { MenuFacts } from './resolve.js';
import { createIntentRouter } from './graph_intents.js';
import type { GraphOps } from './graph_intents.js';
import { EMPTY_VIEW_STATE, anyHidden } from './view_state.js';
import type { NodeViewState } from './view_state.js';
import { resolveToken } from '../dom/theme.js';

export interface RadExtensionOptions {
  ops: GraphOps;
  /** Current per-node view state. Read fresh on every apply — never cached. */
  viewState: () => NodeViewState;
  /** Facts the resolver needs that only the host knows. */
  facts: (context: MenuContext) => MenuFacts;
  onError?: (verb: string, err: unknown) => void;
}

/** Nodes carry `data-node-id`; that attribute is the id under the pointer. */
function nodeIdAt(target: EventTarget | null): string | null {
  if (!(target instanceof Element)) return null;
  const g = target.closest('[data-node-id]');
  return g ? g.getAttribute('data-node-id') : null;
}

export class RadExtension extends BaseExtension<GraphNode, GraphEdge> {
  private session: Session | null = null;
  private attachment: Attachment | null = null;

  constructor(private readonly opts: RadExtensionOptions) {
    super('rad', 'Radial menu', 'QM rad radial menu, conformant to vectors v0.4.0');
  }

  public apply(): void {
    const ctx = this.assertContext();
    const svg = ctx.svg.node();
    if (!svg) return;

    const route = createIntentRouter({ ops: this.opts.ops, onError: this.opts.onError });

    this.session = createSession({
      resolve: (menuContext) => resolveGraphMenu(menuContext, this.opts.facts(menuContext)),
      onIntent: (intent) => {
        route(intent);
        // The renderer derives from state, so re-apply after every verb
        // rather than letting the committing path paint anything itself.
        this.applyViewState();
        ctx.onGraphChange?.();
      },
      onEffect: (fx: Effect) => this.onEffect(fx),
    });

    this.attachment = attach({
      session: this.session,
      svg,
      container: ctx.container,
      contextAt: (ev) => this.contextFor(ev),
    });

    // The container must be focusable or the keyboard path is unreachable —
    // the contract's "pointer never required" clause is a host obligation
    // as much as a menu one.
    if (!ctx.container.hasAttribute('tabindex')) ctx.container.setAttribute('tabindex', '0');

    this.applyViewState();
  }

  /**
   * Build the MenuContext for a raw event.
   *
   * Selection wins over the node under the pointer: acting on a selection the
   * user built and then losing it because they happened to press over one
   * member is the kind of thing that teaches people not to select.
   */
  private contextFor(ev: PointerEvent | KeyboardEvent): MenuContext | null {
    const ctx = this.assertContext();
    const rect = ctx.container.getBoundingClientRect();

    const point =
      'clientX' in ev
        ? { x: ev.clientX - rect.left, y: ev.clientY - rect.top }
        : { x: rect.width / 2, y: rect.height / 2 };

    const selected = [...ctx.selectedNodes].map((n) => n.id);
    const hovered = 'target' in ev ? nodeIdAt(ev.target) : null;

    if (selected.length > 1) {
      return { type: 'selection', targetIds: selected, position: point };
    }
    if (hovered) {
      return { type: 'node', targetIds: [hovered], position: point };
    }
    if (selected.length === 1) {
      return { type: 'node', targetIds: selected, position: point };
    }
    return { type: 'canvas', targetIds: [], position: point };
  }

  private onEffect(_fx: Effect): void {
    // Rendering and announcements are the DOM layer's job; this hook exists
    // for haptics and instrumentation, neither of which this host has yet.
  }

  /**
   * Paint per-node view state onto the DOM.
   *
   * This is a projection, not a mutation: the source of truth is the state
   * this reads, so a re-render, a relayout or a cache replay reproduces it.
   */
  public applyViewState(): void {
    const ctx = this.context;
    if (!ctx) return;
    const state = this.opts.viewState();

    ctx.svg.selectAll<SVGGElement, unknown>('g.graph-node').each(function () {
      const el = d3.select(this);
      const id = this.getAttribute('data-node-id');
      const v = id ? state[id] : undefined;

      el.attr('opacity', v?.hidden ? 0 : 1);
      if (v?.hidden) el.style('pointer-events', 'none');
      else el.style('pointer-events', null);

      const path = el.select<SVGPathElement>('path');
      if (!path.empty()) {
        const base = path.attr('data-base-fill');
        if (v?.colorToken) path.attr('fill', resolveToken(v.colorToken));
        else if (base) path.attr('fill', base);

        path.attr('stroke', v?.pinned ? resolveToken('gold') : '#fff');
        if (v?.pinned) path.attr('stroke-width', 2);
        else path.attr('stroke-width', null);
      }
    });
  }

  /** Whether anything is hidden — the canvas ring needs it for `show-hidden`. */
  public anyHidden(): boolean {
    return anyHidden(this.opts.viewState() ?? EMPTY_VIEW_STATE);
  }

  public destroy(): void {
    this.attachment?.destroy();
    this.attachment = null;
    this.session = null;
    super.destroy();
  }
}
