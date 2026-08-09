/**
 * rad — the public surface, named once.
 *
 * This mirrors the frozen `window.rad` object the reference implementation
 * exports (quaternionmedia/rad @ d362abd). A host reaches exactly this and
 * nothing else; anything not on it is private, and reaching past it is
 * relying on a coincidence.
 *
 * ── Boundary note ────────────────────────────────────────────────────────
 * Everything under `rad/core/`, plus `session.ts` and `dom/`, is free of any
 * import from the rest of this application. That is deliberate: this
 * directory is shaped as a package so it can be lifted into a shared
 * `@quaternionmedia/rad-web` without change once a second web host wants it.
 * The codecartographer-specific half lives in `rad/host/`, which is the only
 * part that imports app code, and is the part every host writes for itself.
 *
 * `core/` additionally may not mention `document`, `window` or `HTMLElement`.
 * That is checked — see `scripts/rad-core-lint.mjs`.
 */

export const VECTOR_VERSION = '0.4.0';

export type {
  Effect,
  Geometry,
  InputEvent,
  Intent,
  MachineState,
  MenuContext,
  MenuItem,
  MenuSpec,
  RingView,
} from './core/types.js';

// geometry
export {
  GEOM,
  MAX_ITEMS,
  RING,
  angleToIndex,
  arcPath,
  clampRingCentre,
  fitRing,
  inBand,
  itemCenterDeg,
  normDeg,
  rCancel,
  toPolar,
} from './core/geometry.js';

// machine
export { assertRing, createMachine, mItems, step } from './core/machine.js';

// time
export {
  DIVS,
  TEMPO_RANGE,
  TIME,
  apsFromTempo,
  ccToDiv,
  ccToRange,
  estimateBpm,
  gridPeriod,
  medianOf,
  quantizeTime,
} from './core/time.js';

// chord
export type { KeyEvt } from './core/chord.js';
export { classifyBurst, prefixCollisions, splitBursts } from './core/chord.js';

// integration
export type { Session, SessionOptions } from './session.js';
export { createSession } from './session.js';
