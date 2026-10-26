/**
 * Where the badge naming a node's file is drawn: beside the point it was
 * opened from, and wholly inside the window.
 *
 * No DOM types, so this compiles under `tsconfig.pure.json`; the renderer
 * measures the badge and the window and places it by what this returns.
 */

export interface Size {
  width: number;
  height: number;
}

/** How far the badge keeps from the window's edges, in px. */
export const BADGE_MARGIN = 8;

/** How far below the point a badge put under it starts, in px: clear of a
 *  pointer's arrow, which is drawn down and right of its point. */
export const BADGE_BELOW = 20;

/**
 * The badge's `left` and `top`: 8px right of `at` with its bottom 6px above
 * it, moved left or down as far as it takes to keep `margin` between the
 * badge and every edge of `viewport`; one that moving down puts over `at` is
 * put `BADGE_BELOW` below it instead. One wider than the window less its
 * margins is placed at the left margin; the renderer bounds its width to that
 * and lets it wrap.
 *
 * **THE BADGE STAYS IN THE WINDOW.** It was placed at the point plus a fixed
 * offset, on one line. A path read from disk is most of a window wide --
 * `delay  C:\Users\...\crates\blinky\src\main.rs:21` is 756px at 11px -- so a
 * double-click on a node right of the window's middle drew the badge past the
 * right edge, and what was cut off was its end: the file's name and the line.
 */
export function badgePlace(
  at: { x: number; y: number },
  badge: Size,
  viewport: Size,
  margin: number = BADGE_MARGIN,
): { left: number; top: number } {
  const within = (v: number, low: number, high: number): number => Math.max(low, Math.min(v, high));
  const left = within(at.x + 8, margin, viewport.width - badge.width - margin);
  let top = within(at.y - 6 - badge.height, margin, viewport.height - badge.height - margin);
  // Moved down over the point, it would take the wheel and the clicks there
  // until it goes, since the renderer lets it take the pointer for its title.
  const holds = (v: number, start: number, size: number): boolean => v >= start && v <= start + size;
  if (holds(at.x, left, badge.width) && holds(at.y, top, badge.height)) {
    top = within(at.y + BADGE_BELOW, margin, viewport.height - badge.height - margin);
  }
  return { left, top };
}
