/**
 * rad core — chorded input. Platform-free.
 *
 * A CharaChorder-class chord arrives as a word whose inter-key gaps are
 * machine-fast; serial typing is human-slow. Same words, same verbs —
 * `chorded` only affects IPA accounting (a chord is one input).
 *
 * Ported from quaternionmedia/rad @ d362abd.
 */
import { TIME } from './time.js';

export interface KeyEvt {
  k: string;
  t: number;
}

/** Split a key stream into bursts at gaps wider than `splitGap`. */
export function splitBursts(evts: KeyEvt[], splitGap: number = TIME.burstSplitMs): KeyEvt[][] {
  const out: KeyEvt[][] = [];
  for (const e of evts) {
    const cur = out[out.length - 1];
    if (!cur || e.t - cur[cur.length - 1].t > splitGap) out.push([e]);
    else cur.push(e);
  }
  return out;
}

/** A single key is never a chord. Two or more within `chordGap` each is. */
export function classifyBurst(
  evts: KeyEvt[],
  chordGap: number = TIME.chordGapMs,
): { word: string; chorded: boolean } {
  const word = evts.map((e) => e.k).join('');
  let chorded = evts.length >= 2;
  for (let i = 1; i < evts.length; i++) {
    if (evts[i].t - evts[i - 1].t > chordGap) chorded = false;
  }
  return { word, chorded };
}

/**
 * The chord vocabulary must be prefix-free — the latency claim rests on it.
 * A known word can only finalize on its last keystroke if no other word
 * extends it; otherwise recognition has to wait out the split window.
 */
export function prefixCollisions(words: string[]): string[] {
  const out: string[] = [];
  for (const a of words) {
    for (const b of words) {
      if (a !== b && b.startsWith(a)) out.push(`${a} ⊂ ${b}`);
    }
  }
  return out.sort();
}


