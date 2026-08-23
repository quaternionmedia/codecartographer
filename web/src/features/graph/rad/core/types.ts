/**
 * rad — shared types for the platform-free core.
 *
 * These are the shapes named in §4 of the rad host integration standard
 * ("What travels across the seam"). Everything here is plain data: no
 * functions, no class instances, no host objects. That is what lets an
 * Intent be serialized, queued, replayed, or sent over a wire.
 *
 * Ported from quaternionmedia/rad @ d362abd, vectors v0.4.0.
 * The JSON vectors are the governed artifact; this is an implementation of
 * them. If the two disagree, the vectors win and this file is wrong.
 */

/** A single wedge. `children` makes it a submenu parent instead of a verb. */
export interface MenuItem {
  id: string;
  label?: string;
  /** Palette token name, never a literal colour — contract §1. */
  swatch?: string | null;
  enabled?: boolean;
  destructive?: boolean;
  /** The verb committed when this item is chosen. Absent on submenu parents. */
  action?: string;
  children?: MenuItem[];
}

/**
 * What the menu was opened on.
 *
 * A host may extend `type` with its own values; rad treats an unknown type as
 * opaque and passes it to `resolve` unchanged (standard §4).
 */
export interface MenuContext {
  type: 'node' | 'edge' | 'canvas' | 'selection' | (string & {});
  targetIds: string[];
  /** In the HOST's coordinates. rad only carries this through. */
  position: { x: number; y: number };
}

/** One ring. 1..8 items, enforced by `assertRing`. */
export interface MenuSpec {
  title?: string;
  items: MenuItem[];
}

/** What a commit produces. Plain data, by construction. */
export interface Intent {
  action: string;
  context: MenuContext;
  itemId: string;
}

/**
 * A highlight effect carries its own resolved `label` and `id`, not just an
 * index — contract §3. A batch can replace the ring (`submenu` does), so an
 * index alone is ambiguous by the time a consumer reads it. Never re-resolve
 * `i` against live state.
 */
export type Effect =
  | { t: 'highlight'; i: number | null; id: string | null; label: string }
  | { t: 'open' }
  | { t: 'submenu'; item: MenuItem }
  | { t: 'back' }
  | { t: 'cancel' }
  | { t: 'commit'; item: MenuItem };

/** Ring geometry. Travels with the machine, never read from a global. */
export interface Geometry {
  startDeg: number;
  clockwise: boolean;
  r0: number;
  r1: number;
  cancelScale: number;
  longPressMs: number;
  slop: number;
}

/** Input in ring-polar coordinates. The host converts — standard §3. */
export type InputEvent =
  | { type: 'open' }
  | { type: 'longpress' }
  | { type: 'close' }
  | { type: 'down'; r: number; thetaDeg: number }
  | { type: 'move'; r: number; thetaDeg: number }
  | { type: 'up'; r: number; thetaDeg: number }
  | { type: 'key'; key: string };

/** Internal machine state. Hosts read `Session.view`, not this. */
export interface MachineState {
  geom: Geometry;
  status: 'closed' | 'pending' | 'open';
  mode: 'tracking' | 'idle' | null;
  stack: MenuSpec[];
  highlight: number | null;
  pressIndex: number | 'hub' | null;
  opened: boolean;
  committed: MenuItem | null;
  cancelled: boolean;
}

/** The read-only projection a renderer needs. Standard §2. */
export interface RingView {
  title: string | null;
  items: Array<{
    id: string;
    label: string;
    swatch: string | null;
    enabled: boolean;
    destructive: boolean;
    hasChildren: boolean;
  }>;
  highlight: number | null;
  depth: number;
  geometry: Geometry | null;
}
