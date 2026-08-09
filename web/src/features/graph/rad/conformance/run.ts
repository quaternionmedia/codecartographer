/**
 * rad — conformance runner.
 *
 * Replays `conformance/vectors.json` against this port. Obligation 4 of the
 * host integration standard §5: "Replay conformance/vectors.json in the
 * host's own test runner and pin the vector version claimed. Integrating
 * without this makes 'conformant' a description of intent."
 *
 * The runner takes the vector set as an argument rather than importing one,
 * so a test can replay the GOVERNED file rather than a copy this package
 * happens to ship. It is platform-free for the same reason the core is: these
 * are pure functions and they have no need of a browser.
 */
import type { Geometry, InputEvent, MenuItem } from '../core/types.js';
import {
  GEOM,
  MAX_ITEMS,
  RING,
  angleToIndex,
  clampRingCentre,
  fitRing,
} from '../core/geometry.js';
import { createMachine, step } from '../core/machine.js';
import {
  TIME,
  apsFromTempo,
  ccToDiv,
  ccToRange,
  estimateBpm,
  gridPeriod,
  quantizeTime,
} from '../core/time.js';
import { classifyBurst, prefixCollisions, splitBursts } from '../core/chord.js';

export interface VectorSet {
  version: string;
  geometry: Record<string, number | boolean>;
  time: Record<string, number>;
  cases: VectorCase[];
}

/** Loosely typed on purpose — the JSON is the governed shape, not this. */
export interface VectorCase {
  name: string;
  n?: number;
  geom?: Partial<Geometry>;
  trace?: Array<InputEvent & { t?: number }>;
  expectHighlights?: Array<number | null>;
  expectLabels?: string[];
  expect?: {
    committed: number | null;
    cancelled: boolean;
    opened?: boolean;
    stillOpen?: boolean;
  };
  [k: string]: unknown;
}

export interface CaseResult {
  name: string;
  pass: boolean;
  why: string;
}

export interface RunOptions {
  /**
   * The host's chord vocabulary. One vector (`source: "CHORD_MAP"`) asserts
   * that whatever the host binds is prefix-free — so this host's own verbs
   * are checked by rad's vector rather than by this host's opinion.
   */
  chordWords?: string[];
}

const near = (a: number, b: number, eps = 1e-9) => Math.abs(a - b) <= eps;

/**
 * Assert the constants this port compiled against still match the ones the
 * vector set declares. Without this a rad constant could move and every
 * behavioural case would keep passing against a port that had quietly
 * diverged on the numbers underneath them.
 */
export function checkGeometryBlock(v: VectorSet): CaseResult {
  const want = v.geometry;
  const mine: Record<string, number | boolean> = {
    startDeg: GEOM.startDeg,
    clockwise: GEOM.clockwise,
    r0: GEOM.r0,
    r1: GEOM.r1,
    longPressMs: GEOM.longPressMs,
    slop: GEOM.slop,
    cancelScale: GEOM.cancelScale,
    maxItems: MAX_ITEMS,
    bandMin: RING.bandMin,
    margin: RING.margin,
    topInset: RING.topInset,
    bottomInset: RING.bottomInset,
  };
  const bad: string[] = [];
  for (const k of Object.keys(want)) {
    if (mine[k] !== want[k]) bad.push(`${k}: port ${String(mine[k])}, vectors ${String(want[k])}`);
  }
  for (const k of Object.keys(v.time)) {
    const t = TIME as unknown as Record<string, number>;
    if (t[k] !== v.time[k]) bad.push(`time.${k}: port ${t[k]}, vectors ${v.time[k]}`);
  }
  return {
    name: 'declared constants match the vector set',
    pass: bad.length === 0,
    why: bad.join('; '),
  };
}

/** Replay every case. Returns one result per case, in file order. */
export function runConformanceWith(v: VectorSet, opts: RunOptions = {}): CaseResult[] {
  const results: CaseResult[] = [];

  for (const c of v.cases as VectorCase[]) {
    let pass = true;
    let why = '';

    if (c.fit) {
      for (const k of c.fit as Array<{ vw: number; vh: number; expectR1: number }>) {
        const got = fitRing(k.vw, k.vh).r1;
        if (!near(got, k.expectR1)) {
          pass = false;
          why = `${k.vw}x${k.vh} → r1 ${got}, want ${k.expectR1}`;
          break;
        }
      }
    } else if (c.clamp) {
      for (const k of c.clamp as Array<{
        x: number; y: number; vw: number; vh: number; r1: number; expectX: number; expectY: number;
      }>) {
        const got = clampRingCentre(k.x, k.y, k.vw, k.vh, k.r1);
        if (!near(got.x, k.expectX) || !near(got.y, k.expectY)) {
          pass = false;
          why = `(${k.x},${k.y}) in ${k.vw}x${k.vh} r1=${k.r1} → (${got.x},${got.y}), want (${k.expectX},${k.expectY})`;
          break;
        }
      }
    } else if (c.ceiling) {
      for (const k of c.ceiling as Array<{ n: number; expectThrows: boolean }>) {
        let threw = false;
        try {
          createMachine({
            items: Array.from({ length: k.n }, (_, i) => ({ id: 'i' + i, label: 'i' + i })),
          });
        } catch {
          threw = true;
        }
        if (threw !== k.expectThrows) {
          pass = false;
          why = `n=${k.n} threw ${threw}`;
          break;
        }
      }
    } else if (c.vocab) {
      const vc = c.vocab as { words?: string[]; expectPrefixFree: boolean; expectCollisions?: string[] };
      const words = vc.words ?? opts.chordWords;
      if (!words) {
        pass = false;
        why = 'case needs the host chord vocabulary; pass RunOptions.chordWords';
      } else {
        const cols = prefixCollisions(words);
        if ((cols.length === 0) !== vc.expectPrefixFree) {
          pass = false;
          why = `collisions ${JSON.stringify(cols)}`;
        } else if (
          vc.expectCollisions &&
          JSON.stringify(cols) !== JSON.stringify(vc.expectCollisions)
        ) {
          pass = false;
          why = `collisions ${JSON.stringify(cols)}`;
        }
      }
    } else if (c.aps) {
      for (const k of c.aps as Array<{ bpm: number; div: number; expectAps: number }>) {
        const got = apsFromTempo(k.bpm, k.div);
        if (!near(got, k.expectAps)) {
          pass = false;
          why = `bpm=${k.bpm} div=${k.div} → ${got}`;
          break;
        }
      }
    } else if (c.cc) {
      for (const k of c.cc as Array<{ cc: number; lo: number; hi: number; expect: number }>) {
        const got = ccToRange(k.cc, k.lo, k.hi);
        if (!near(got, k.expect)) {
          pass = false;
          why = `cc=${k.cc} → ${got}, want ${k.expect}`;
          break;
        }
      }
    } else if (c.ccdiv) {
      for (const k of c.ccdiv as Array<{ cc: number; expect: number }>) {
        const got = ccToDiv(k.cc);
        if (got !== k.expect) {
          pass = false;
          why = `cc=${k.cc} → ${got}, want ${k.expect}`;
          break;
        }
      }
    } else if (c.grid) {
      for (const k of c.grid as Array<{ bpm: number; div: number; expectMs: number }>) {
        const got = gridPeriod(k.bpm, k.div);
        if (!near(got, k.expectMs)) {
          pass = false;
          why = `bpm=${k.bpm} div=${k.div} → ${got}ms`;
          break;
        }
      }
    } else if (c.quant) {
      for (const q of c.quant as Array<{
        t: number; phase: number; period: number; policy: string; expectT: number;
      }>) {
        const got = quantizeTime(q.t, q.phase, q.period, q.policy);
        if (!near(got, q.expectT, 1e-6)) {
          pass = false;
          why = `t=${q.t} → ${got}, want ${q.expectT}`;
          break;
        }
      }
    } else if (c.tempo) {
      const tc = c.tempo as { periods: number[]; expectBpm: number | null; tol: number };
      const times: number[] = [];
      let t = 1000;
      for (const p of tc.periods) {
        times.push(t);
        t += p;
      }
      if (tc.periods.length) times.push(t);
      const got = estimateBpm(times);
      const bad =
        tc.expectBpm === null ? got !== null : got === null || Math.abs(got - tc.expectBpm) > tc.tol;
      if (bad) {
        pass = false;
        why = `bpm ${got}`;
      }
    } else if (c.chord) {
      const cc = c.chord as { evts: Array<{ k: string; t: number }>; expectWord: string; expectChorded: boolean };
      const r = classifyBurst(cc.evts);
      if (r.word !== cc.expectWord || r.chorded !== cc.expectChorded) {
        pass = false;
        why = `${r.word}/${r.chorded}`;
      }
    } else if (c.split) {
      const sc = c.split as { evts: Array<{ k: string; t: number }>; expectWords: string[] };
      const words = splitBursts(sc.evts).map((b) => b.map((e) => e.k).join(''));
      if (JSON.stringify(words) !== JSON.stringify(sc.expectWords)) {
        pass = false;
        why = JSON.stringify(words);
      }
    } else if (c.pure) {
      for (const p of c.pure as Array<{ thetaDeg: number; expectIndex: number }>) {
        const got = angleToIndex(p.thetaDeg, c.n as number);
        if (got !== p.expectIndex) {
          pass = false;
          why = `θ=${p.thetaDeg} → ${got}, want ${p.expectIndex}`;
          break;
        }
      }
    } else {
      // Behavioural trace.
      const n = c.n as number;
      const items: MenuItem[] = Array.from({ length: n }, (_, i) => ({
        id: 'i' + i,
        label: 'i' + i,
      }));
      const st = createMachine({ items }, c.geom ? { ...GEOM, ...c.geom } : GEOM);
      const hl: Array<number | null> = [];
      const labels: string[] = [];
      for (const ev of c.trace ?? []) {
        for (const f of step(st, ev as InputEvent)) {
          if (f.t === 'highlight') {
            hl.push(f.i);
            if (f.i != null) labels.push(f.label);
          }
        }
      }
      const e = c.expect!;
      const committedIdx = st.committed ? Number(st.committed.id.slice(1)) : null;
      if (JSON.stringify(hl) !== JSON.stringify(c.expectHighlights)) {
        pass = false;
        why = `highlights ${JSON.stringify(hl)}`;
      } else if (c.expectLabels && JSON.stringify(labels) !== JSON.stringify(c.expectLabels)) {
        pass = false;
        why = `labels ${JSON.stringify(labels)}`;
      } else if (committedIdx !== e.committed) {
        pass = false;
        why = `committed ${committedIdx}`;
      } else if (st.cancelled !== e.cancelled) {
        pass = false;
        why = `cancelled ${st.cancelled}`;
      } else if ('opened' in e && st.opened !== e.opened) {
        pass = false;
        why = `opened ${st.opened}`;
      } else if (e.stillOpen && st.status !== 'open') {
        pass = false;
        why = `status ${st.status}`;
      }
    }

    results.push({ name: c.name, pass, why });
  }

  return results;
}
