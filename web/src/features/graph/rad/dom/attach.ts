/**
 * rad/dom — input adapters, and the wiring that joins them to a session.
 *
 * This is the twenty lines the integration standard §3 predicts every host
 * writes: screen coordinates in, ring-polar out. rad cannot do this itself
 * without acquiring a dependency on the host's camera, transform and scroll
 * state, which is the exact coupling that made the legacy menu unportable.
 *
 * Pointer Events throughout — one code path for mouse, touch and pen, which
 * is also the house rule against layering tap detectors.
 *
 * No application imports — part of the liftable package.
 */
import type { Effect, MenuContext } from '../core/types.js';
import type { Session } from '../session.js';
import { GEOM, clampRingCentre, fitRing, toPolar } from '../core/geometry.js';
import { RingRenderer } from './ring_view.js';

export interface AttachOptions {
  /** The session to drive. */
  session: Session;
  /** SVG root. The ring layer mounts here, outside any pan/zoom group. */
  svg: SVGSVGElement;
  /** Element that owns pointer/keyboard events and hosts the live region. */
  container: HTMLElement;
  /**
   * Build the MenuContext for a raw event. Return null to decline — that is
   * how a host says "not here" (e.g. a click that hit no node).
   */
  contextAt: (ev: PointerEvent | KeyboardEvent) => MenuContext | null;
  /** Optional hook after every effect, for haptics or instrumentation. */
  onEffect?: (fx: Effect) => void;
}

export interface Attachment {
  /** Open programmatically — used by tests and by keyboard invocation. */
  openAt(context: MenuContext, screenX: number, screenY: number, mode?: 'idle' | 'tracking'): void;
  destroy(): void;
}

export function attach(opts: AttachOptions): Attachment {
  const { session, svg, container, contextAt, onEffect } = opts;
  const ring = new RingRenderer(svg, container);

  let longPressTimer: number | null = null;
  let pressOrigin: { x: number; y: number } | null = null;
  let activePointerId: number | null = null;

  const rect = () => svg.getBoundingClientRect();

  /** Screen point → ring-polar about the current centre. */
  function polar(clientX: number, clientY: number) {
    const r = rect();
    const c = ring.getCentre();
    return toPolar(clientX - r.left - c.x, clientY - r.top - c.y);
  }

  function paint() {
    ring.render(session.view);
  }

  function handle(effects: Effect[]) {
    for (const fx of effects) {
      // The effect carries its own label; never re-resolve the index against
      // live state, because a batch may already have replaced the ring.
      if (fx.t === 'highlight' && fx.i != null) ring.announce(fx.label);
      if (fx.t === 'cancel') ring.clear();
      onEffect?.(fx);
    }
    paint();
  }

  function openAt(
    context: MenuContext,
    screenX: number,
    screenY: number,
    mode: 'idle' | 'tracking' = 'idle',
  ): void {
    const r = rect();
    const viewport = { width: r.width, height: r.height };
    // Fit first, then clamp against the fitted radius — clamping against the
    // natural r1 would place a shrunken ring using a radius it does not have.
    const fitted = fitRing(viewport.width, viewport.height);
    const centre = clampRingCentre(
      screenX - r.left,
      screenY - r.top,
      viewport.width,
      viewport.height,
      fitted.r1,
    );
    ring.setCentre(centre.x, centre.y);
    handle(session.openAt(context, viewport, mode));
  }

  function cancelLongPress() {
    if (longPressTimer !== null) {
      clearTimeout(longPressTimer);
      longPressTimer = null;
    }
    pressOrigin = null;
  }

  // ── Pointer ──────────────────────────────────────────────────────────────

  const onPointerDown = (ev: PointerEvent) => {
    if (session.isOpen) {
      const p = polar(ev.clientX, ev.clientY);
      handle(session.input({ type: 'down', r: p.r, thetaDeg: p.thetaDeg }));
      return;
    }
    // Long-press opens in release-select mode. Touch and pen only: a mouse
    // has a secondary button and does not need to be held.
    if (ev.pointerType === 'mouse') return;
    const context = contextAt(ev);
    if (!context) return;

    activePointerId = ev.pointerId;
    pressOrigin = { x: ev.clientX, y: ev.clientY };
    longPressTimer = window.setTimeout(() => {
      longPressTimer = null;
      if (!pressOrigin) return;
      openAt(context, pressOrigin.x, pressOrigin.y, 'tracking');
    }, GEOM.longPressMs);
  };

  const onPointerMove = (ev: PointerEvent) => {
    if (!session.isOpen) {
      // Slop: a press that wanders further than the contract's tolerance was
      // a drag, not a long press.
      if (pressOrigin && Math.hypot(ev.clientX - pressOrigin.x, ev.clientY - pressOrigin.y) > GEOM.slop) {
        cancelLongPress();
      }
      return;
    }
    if (activePointerId !== null && ev.pointerId !== activePointerId) return;
    const p = polar(ev.clientX, ev.clientY);
    handle(session.input({ type: 'move', r: p.r, thetaDeg: p.thetaDeg }));
  };

  const onPointerUp = (ev: PointerEvent) => {
    cancelLongPress();
    activePointerId = null;
    if (!session.isOpen) return;
    const p = polar(ev.clientX, ev.clientY);
    handle(session.input({ type: 'up', r: p.r, thetaDeg: p.thetaDeg }));
  };

  const onContextMenu = (ev: MouseEvent) => {
    const context = contextAt(ev as PointerEvent);
    if (!context) return;
    ev.preventDefault();
    if (session.isOpen) handle(session.close());
    openAt(context, ev.clientX, ev.clientY, 'idle');
  };

  // ── Keyboard ─────────────────────────────────────────────────────────────

  const onKeyDown = (ev: KeyboardEvent) => {
    if (session.isOpen) {
      if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter', 'Escape'].includes(ev.key)) {
        ev.preventDefault();
        ev.stopPropagation();
        handle(session.input({ type: 'key', key: ev.key }));
      }
      return;
    }
    // `m` invokes on the focused element — the contract's keyboard entry
    // point, and the reason a pointer is never required.
    if (ev.key === 'm' && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
      const context = contextAt(ev);
      if (!context) return;
      ev.preventDefault();
      const r = rect();
      openAt(context, r.left + context.position.x, r.top + context.position.y, 'idle');
    }
  };

  container.addEventListener('pointerdown', onPointerDown);
  container.addEventListener('pointermove', onPointerMove);
  container.addEventListener('pointerup', onPointerUp);
  container.addEventListener('pointercancel', onPointerUp);
  container.addEventListener('contextmenu', onContextMenu);
  container.addEventListener('keydown', onKeyDown);

  return {
    openAt,
    destroy() {
      cancelLongPress();
      container.removeEventListener('pointerdown', onPointerDown);
      container.removeEventListener('pointermove', onPointerMove);
      container.removeEventListener('pointerup', onPointerUp);
      container.removeEventListener('pointercancel', onPointerUp);
      container.removeEventListener('contextmenu', onContextMenu);
      container.removeEventListener('keydown', onKeyDown);
      ring.destroy();
    },
  };
}
