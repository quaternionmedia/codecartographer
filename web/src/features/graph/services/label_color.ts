/**
 * The colour a graph's names are drawn in.
 *
 * Graph Settings starts the name colour at `THEME_LABEL_COLOR`, and that value
 * means "the theme's": names take the theme's font colour (`--c-font`). Any
 * other colour is the reader's choice, drawn as chosen.
 *
 * **THE CANVAS DREW THE STARTING VALUE LITERALLY.** The other renderers already
 * read it as the theme's (`actions.ts`, `applyThemeToGraphData`), but the
 * streaming canvas, which draws every parse and every showgraph, drew it as the
 * Terminal theme's green on every theme, and every exported picture with it.
 */

export const THEME_LABEL_COLOR = '#00ff41';

export function labelColorOf(chosen: string | undefined, themeFont: string): string {
  const own = (chosen ?? '').trim();
  if (!own || own.toLowerCase() === THEME_LABEL_COLOR) return themeFont.trim() || THEME_LABEL_COLOR;
  return own;
}
