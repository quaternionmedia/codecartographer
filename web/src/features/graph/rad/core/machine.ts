/**
 * rad core — the interaction state machine. Platform-free.
 *
 * States: CLOSED → PENDING → OPEN → TRACKING → (SUBMENU→OPEN…) → COMMITTED | CLOSED
 * Two commit styles (release-select, tap-select) over one identical band.
 *
 * Ported from quaternionmedia/rad @ d362abd. Semantics are fixed by
 * conformance/vectors.json v0.4.0.
 */
import type { Effect, Geometry, InputEvent, MachineState, MenuItem, MenuSpec } from './types.js';
import { GEOM, MAX_ITEMS, angleToIndex, inBand, rCancel } from './geometry.js';

/**
 * Contract §1: at most 8 items per ring, enforced here rather than by a
 * reviewer. Checked in `createMachine` and on submenu entry so nested rings
 * are covered too — overflow is a design error, and wedges thinner than a
 * 44-unit target are what it silently produces.
 */
export function assertRing(items: MenuItem[] | undefined, where: string): void {
  if (!Array.isArray(items) || items.length < 1) {
    throw new RangeError(`rad: ${where} ring must hold at least one item`);
  }
  if (items.length > MAX_ITEMS) {
    throw new RangeError(
      `rad: ${where} ring has ${items.length} items, contract §1 caps a ring at ${MAX_ITEMS} — group into a submenu`,
    );
  }
}

/**
 * The machine carries the geometry it was opened with.
 *
 * Reading a module global made the committing band a property of the page
 * rather than of the menu, so a ring fitted to a small viewport would have
 * been drawn at one radius and judged at another.
 */
export function createMachine(spec: MenuSpec, geom: Geometry = GEOM): MachineState {
  assertRing(spec.items, spec.title || 'root');
  return {
    geom,
    status: 'closed',
    mode: null,
    stack: [spec],
    highlight: null,
    pressIndex: null,
    opened: false,
    committed: null,
    cancelled: false,
  };
}

/** The items of the ring currently on top of the submenu stack. */
export function mItems(s: MachineState): MenuItem[] {
  return s.stack[s.stack.length - 1].items;
}

/**
 * step(state, event) → effects. Mutates `state` in place and returns the
 * batch produced by this event.
 */
export function step(s: MachineState, ev: InputEvent): Effect[] {
  const fx: Effect[] = [];
  const items = mItems(s);
  const n = items.length;
  const g = s.geom ?? GEOM;
  const beyond = (r: number) => r > rCancel(g);

  /**
   * Highlight changes are edge-triggered — required for haptics and for
   * screen-reader announcements, both of which must fire once per index
   * change rather than once per pointer sample.
   */
  const setHl = (i: number | null) => {
    if (i === s.highlight) return;
    s.highlight = i;
    const it = i == null ? null : items[i];
    fx.push({ t: 'highlight', i, id: it ? it.id : null, label: it ? it.label ?? '' : '' });
  };

  function enterSub(st: MachineState, out: Effect[], item: MenuItem): void {
    assertRing(item.children, item.label || item.id);
    st.stack.push({ items: item.children as MenuItem[], title: item.label });
    st.highlight = null;
    st.pressIndex = null;
    out.push({ t: 'submenu', item });
  }

  function back(st: MachineState, out: Effect[]): void {
    if (st.stack.length > 1) {
      st.stack.pop();
      st.highlight = null;
      out.push({ t: 'back' });
    } else {
      close(st, out, true);
    }
  }

  function commit(st: MachineState, out: Effect[], item: MenuItem | undefined): void {
    if (!item || item.enabled === false) {
      close(st, out, true);
      return;
    }
    if (item.children) {
      enterSub(st, out, item);
      if (st.mode === 'tracking') st.mode = 'idle';
      return;
    }
    st.committed = item;
    st.status = 'closed';
    out.push({ t: 'commit', item });
  }

  function close(st: MachineState, out: Effect[], cancelled: boolean): void {
    st.status = 'closed';
    st.cancelled = !!cancelled;
    st.highlight = null;
    out.push({ t: 'cancel' });
  }

  switch (ev.type) {
    case 'open': // explicit open → tap-select mode
      s.status = 'open';
      s.mode = 'idle';
      s.opened = true;
      fx.push({ t: 'open' });
      break;

    case 'down':
      if (s.status === 'closed') {
        s.status = 'pending';
        break;
      }
      if (s.status === 'open' && s.mode === 'idle') {
        if (ev.r <= g.r0) {
          s.pressIndex = 'hub'; // latch the back/cancel affordance
          break;
        }
        if (beyond(ev.r)) {
          close(s, fx, true);
          break;
        }
        s.pressIndex = angleToIndex(ev.thetaDeg, n);
        setHl(s.pressIndex);
      }
      break;

    case 'longpress': // pending press matured → release-select mode
      if (s.status === 'pending') {
        s.status = 'open';
        s.mode = 'tracking';
        s.opened = true;
        fx.push({ t: 'open' });
      }
      break;

    case 'move':
      if (s.status !== 'open') break;
      // A latched hub press can no longer commit a wedge, so it must not
      // highlight one: a highlight that cannot commit is the interface lying
      // about its own next state, and it fires a haptic for a non-event.
      if (s.pressIndex === 'hub') break;
      if (inBand(ev.r, g)) {
        const i = angleToIndex(ev.thetaDeg, n);
        setHl(i);
        // drag-through submenu entry (release-select only)
        if (s.mode === 'tracking' && ev.r > g.r1 + 12 && items[i] && items[i].children) {
          enterSub(s, fx, items[i]);
        }
      } else {
        setHl(null); // inside the dead zone, or beyond r_cancel
      }
      break;

    case 'up':
      if (s.status === 'pending') {
        close(s, fx, true); // short press: never opened
        break;
      }
      if (s.status !== 'open') break;
      if (s.mode === 'tracking') {
        if (inBand(ev.r, g) && s.highlight != null) commit(s, fx, items[s.highlight]);
        else close(s, fx, true); // dead zone or beyond r_cancel
      } else {
        if (s.pressIndex === 'hub') {
          s.pressIndex = null;
          back(s, fx);
          break;
        }
        if (
          s.pressIndex != null &&
          inBand(ev.r, g) &&
          angleToIndex(ev.thetaDeg, n) === s.pressIndex
        ) {
          commit(s, fx, items[s.pressIndex as number]);
        }
        s.pressIndex = null;
      }
      break;

    case 'key':
      if (s.status !== 'open') break;
      if (ev.key === 'ArrowRight' || ev.key === 'ArrowDown') {
        setHl(s.highlight == null ? 0 : (s.highlight + 1) % n);
      } else if (ev.key === 'ArrowLeft' || ev.key === 'ArrowUp') {
        setHl(s.highlight == null ? n - 1 : (s.highlight - 1 + n) % n);
      } else if (ev.key === 'Enter') {
        if (s.highlight != null) commit(s, fx, items[s.highlight]);
      } else if (ev.key === 'Escape') {
        back(s, fx);
      }
      break;

    case 'close':
      close(s, fx, true);
      break;
  }

  return fx;
}
