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
import type { GraphNode, GraphEdge } from '../../services/graph_types';
import type { Effect, Intent, MenuContext } from '../core/types.js';
import { createSession } from '../session.js';
import type { Session } from '../session.js';
import { attach } from '../dom/attach.js';
import type { Attachment } from '../dom/attach.js';
import { resolveGraphMenu } from './resolve.js';
import { canvasKeyVerb, menuContextFor } from './menu_context.js';
import type { MenuFacts } from './resolve.js';
import { createIntentRouter } from './graph_intents.js';
import type { GraphOps } from './graph_intents.js';
import { EMPTY_VIEW_STATE, anyHidden } from './view_state.js';
import type { NodeViewState } from './view_state.js';
import { resolveToken } from '../dom/theme.js';
import { VECTOR_VERSION } from '../index.js';

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
  private unlisten: (() => void) | null = null;
  /**
   * True from a context-menu key or Shift+F10 on the canvas until the next
   * `contextmenu` or pointer press. The `contextmenu` the browser fires for
   * that key is a MouseEvent, with coordinates like a right-click's, so the
   * key before it is what says no pointer opened the ring.
   */
  private menuKeyPressed = false;

  constructor(private readonly opts: RadExtensionOptions) {
    super('rad', 'Radial menu', `QM rad radial menu, conformant to vectors v${VECTOR_VERSION}`);
  }

  public apply(): void {
    const ctx = this.assertContext();
    const svg = ctx.svg.node();
    if (!svg) return;

    const route = createIntentRouter({ ops: this.opts.ops, onError: this.opts.onError });
    const commit = (intent: Intent) => {
      route(intent);
      // The renderer derives from state, so re-apply after every verb
      // rather than letting the committing path paint anything itself.
      this.applyViewState();
      ctx.onGraphChange?.();
    };

    this.session = createSession({
      resolve: (menuContext) => resolveGraphMenu(menuContext, this.opts.facts(menuContext)),
      onIntent: commit,
      onEffect: (fx: Effect) => this.onEffect(fx),
    });

    this.attachment = attach({
      session: this.session,
      svg,
      container: ctx.container,
      contextAt: (ev) => this.contextFor(ev),
    });

    // After attach's own keydown listener, so a key the open ring took --
    // Escape closing it among them -- arrives here already handled.
    const onKeyDown = (ev: KeyboardEvent) => {
      this.menuKeyPressed = ev.key === 'ContextMenu' || (ev.key === 'F10' && ev.shiftKey);
      if (ev.defaultPrevented || this.session?.isOpen) return;
      const selected = [...ctx.selectedNodes].map((n) => n.id);
      const action = canvasKeyVerb(ev.key, selected);
      if (!action) return;
      ev.preventDefault();
      commit({ action, context: { type: 'canvas', targetIds: [], position: { x: 0, y: 0 } }, itemId: ev.key });
    };
    const onPointerDown = () => { this.menuKeyPressed = false; };
    ctx.container.addEventListener('keydown', onKeyDown);
    ctx.container.addEventListener('pointerdown', onPointerDown, true);
    this.unlisten = () => {
      ctx.container.removeEventListener('keydown', onKeyDown);
      ctx.container.removeEventListener('pointerdown', onPointerDown, true);
    };

    // The container must be focusable or the keyboard path is unreachable —
    // the contract's "pointer never required" clause is a host obligation
    // as much as a menu one.
    if (!ctx.container.hasAttribute('tabindex')) ctx.container.setAttribute('tabindex', '0');

    this.applyViewState();
  }

  /** Build the MenuContext for a raw event; `menu_context.ts` decides which ring. */
  private contextFor(ev: PointerEvent | KeyboardEvent): MenuContext | null {
    const ctx = this.assertContext();
    const rect = ctx.container.getBoundingClientRect();
    const pointer = 'clientX' in ev && !(ev.type === 'contextmenu' && this.menuKeyPressed);
    if (ev.type === 'contextmenu') this.menuKeyPressed = false;
    return menuContextFor({
      pointer,
      underPointer: pointer ? nodeIdAt(ev.target) : null,
      selected: [...ctx.selectedNodes].map((n) => n.id),
      position: pointer
        ? { x: ev.clientX - rect.left, y: ev.clientY - rect.top }
        : { x: rect.width / 2, y: rect.height / 2 },
    });
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
        // Unpinned, a node's border is the one it was drawn with. Cleared,
        // SVG's default drew every node on the canvas when this ran with a
        // white border a unit wide: a ring round a Showcase's dot, two
        // units across.
        if (v?.pinned) path.attr('stroke-width', 2);
        else path.attr('stroke-width', path.attr('data-base-stroke-width'));
      }
    });
  }

  /** Whether anything is hidden — the canvas ring needs it for `show-hidden`. */
  public anyHidden(): boolean {
    return anyHidden(this.opts.viewState() ?? EMPTY_VIEW_STATE);
  }

  public destroy(): void {
    this.unlisten?.();
    this.unlisten = null;
    this.attachment?.destroy();
    this.attachment = null;
    this.session = null;
    super.destroy();
  }
}
