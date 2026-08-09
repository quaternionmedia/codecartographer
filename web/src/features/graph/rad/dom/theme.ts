/**
 * rad/dom — palette tokens.
 *
 * Contract §1: `color:*` names a palette TOKEN, never a literal colour. A hex
 * in an intent is a platform detail smuggled into the portable vocabulary —
 * it cannot survive a theme change, a light/dark switch or forced-colors, and
 * it makes two implementations that agree on meaning disagree on bytes.
 *
 * Token names are contract. Their resolved values are the theme's business,
 * which is this file. Resolution reads CSS custom properties so a host that
 * already themes itself gets rad for free; the literals here are only
 * fallbacks for when a property is unset.
 *
 * No application imports — this file is part of the liftable package.
 */

/** The five tokens the standard vocabulary names. */
export const PALETTE_TOKENS = ['sky', 'calm', 'royal', 'gold', 'signal'] as const;
export type PaletteToken = (typeof PALETTE_TOKENS)[number];

const FALLBACK: Record<PaletteToken, string> = {
  sky: '#4aa8ff',
  calm: '#2fc4a8',
  royal: '#8b6bff',
  gold: '#e0b341',
  signal: '#e5484d',
};

/** `--rad-sky`, falling back to the host's own vars, then to a literal. */
export function resolveToken(token: string, root?: Element): string {
  const t = token as PaletteToken;
  const el = root ?? (typeof document !== 'undefined' ? document.documentElement : null);
  if (!el) return FALLBACK[t] ?? FALLBACK.sky;
  const cs = getComputedStyle(el);
  const own = cs.getPropertyValue(`--rad-${t}`).trim();
  if (own) return own;
  return FALLBACK[t] ?? FALLBACK.sky;
}

/** Chrome colours, read from the host's theme with sane fallbacks. */
export interface RingTheme {
  wedge: string;
  wedgeHi: string;
  hub: string;
  text: string;
  textHi: string;
  danger: string;
  stroke: string;
}

export function readTheme(root?: Element): RingTheme {
  const el = root ?? (typeof document !== 'undefined' ? document.documentElement : null);
  const v = (name: string, fb: string) => {
    if (!el) return fb;
    return getComputedStyle(el).getPropertyValue(name).trim() || fb;
  };
  return {
    wedge: v('--rad-wedge', v('--c-bg-alt', '#1b2228')),
    wedgeHi: v('--rad-wedge-hi', v('--c-accent', '#00d4ff')),
    hub: v('--rad-hub', v('--c-bg', '#11161a')),
    text: v('--rad-text', v('--c-font', '#d6dee4')),
    textHi: v('--rad-text-hi', v('--c-bg', '#11161a')),
    danger: v('--rad-danger', '#e5484d'),
    stroke: v('--rad-stroke', v('--c-border', '#2c3941')),
  };
}
