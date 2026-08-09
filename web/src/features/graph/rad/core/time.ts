/**
 * rad core — time. Platform-free.
 *
 * MIDI clock = 24 ppqn 0xF8 ticks. Tempo from the median inter-tick period
 * (robust to USB jitter). Quantization maps a wall-clock time onto a grid
 * {phase, period}; a scheduler commits at max(now, gridT).
 *
 * These are ported in full because the conformance vectors cover them, and a
 * partial port makes "conformant" a description of intent. This host binds
 * none of them to a clock today — see host/README.md.
 *
 * Ported from quaternionmedia/rad @ d362abd.
 */

export const TIME = { ppqn: 24, chordGapMs: 30, burstSplitMs: 250 };

/** Legal grid subdivisions, per beat. */
export const DIVS = [0.5, 1, 2, 3, 4];

export const TEMPO_RANGE = { bpm: [30, 300] as const, aps: [0.25, 8] as const };

export function medianOf(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/**
 * Median rather than mean: one dropped or delayed tick moves a mean and
 * leaves a median alone, and USB MIDI delivers both.
 */
export function estimateBpm(tickTimes: number[], ppqn: number = TIME.ppqn): number | null {
  if (tickTimes.length < 2) return null;
  const diffs: number[] = [];
  for (let i = 1; i < tickTimes.length; i++) diffs.push(tickTimes[i] - tickTimes[i - 1]);
  const p = medianOf(diffs);
  return p !== null && p > 0 ? 60000 / (p * ppqn) : null;
}

/** `next` leaves an already-on-grid time where it is; `nearest` rounds. */
export function quantizeTime(
  t: number,
  phase: number,
  period: number,
  policy: 'nearest' | 'next' | string,
): number {
  if (policy === 'nearest') return phase + Math.round((t - phase) / period) * period;
  return phase + Math.ceil((t - phase - 1e-9) / period) * period;
}

function clampTo(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

/** Actions per second derived from the clock, when the axes are linked. */
export function apsFromTempo(bpm: number, div: number): number {
  return (bpm / 60) * div;
}

export function ccToRange(cc: number, lo: number, hi: number): number {
  return lo + (clampTo(cc, 0, 127) / 127) * (hi - lo);
}

export function ccToDiv(cc: number, divs: number[] = DIVS): number {
  return divs[Math.min(divs.length - 1, Math.floor((clampTo(cc, 0, 127) / 128) * divs.length))];
}

/** The quantize target: one beat divided by the subdivision axis. */
export function gridPeriod(bpm: number, div: number): number {
  return 60000 / bpm / div;
}
