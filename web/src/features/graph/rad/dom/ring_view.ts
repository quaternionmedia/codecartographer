/**
 * rad/dom — the SVG ring renderer.
 *
 * Draws whatever `Session.view` reports and nothing else. It holds no state
 * of its own beyond the elements it created, so it cannot disagree with the
 * machine about what is on screen.
 *
 * Accessibility is built in rather than added: the container is a `menu`,
 * wedges are `menuitem`s with labels, and exactly ONE live region announces
 * highlight changes. One, because two regions compete and a screen reader
 * reads the loser — rad's own audit found that.
 *
 * No application imports — part of the liftable package.
 */
import type { RingView } from '../core/types.js';
import { arcPath, itemCenterDeg } from '../core/geometry.js';
import { readTheme, resolveToken } from './theme.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

function el<K extends keyof SVGElementTagNameMap>(
  name: K,
  attrs: Record<string, string | number> = {},
): SVGElementTagNameMap[K] {
  const n = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
  return n;
}

/** Labels are shortened, never ellipsized — the resolver owns brevity. */
function shorten(label: string, max = 12): string {
  return label.length <= max ? label : label.slice(0, max);
}

export class RingRenderer {
  private layer: SVGGElement;
  private live: HTMLElement;
  private centre = { x: 0, y: 0 };

  /**
   * @param mount an SVG element OUTSIDE the host's pan/zoom transform. The
   *   ring is screen furniture: if it were inside the transform it would
   *   scale with the graph and its committing band would stop matching the
   *   geometry the machine is judging against.
   * @param liveRegionHost where to put the single aria-live element.
   */
  constructor(mount: SVGSVGElement, liveRegionHost: HTMLElement) {
    this.layer = el('g', { class: 'rad-layer', 'pointer-events': 'none' });
    mount.appendChild(this.layer);

    const existing = liveRegionHost.querySelector<HTMLElement>('[data-rad-live]');
    if (existing) {
      this.live = existing;
    } else {
      const region = document.createElement('div');
      region.setAttribute('data-rad-live', '');
      region.setAttribute('aria-live', 'polite');
      region.setAttribute('aria-atomic', 'true');
      // Visually hidden, not display:none — display:none is not announced.
      region.style.cssText =
        'position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;';
      liveRegionHost.appendChild(region);
      this.live = region;
    }
  }

  setCentre(x: number, y: number): void {
    this.centre = { x, y };
  }

  getCentre(): { x: number; y: number } {
    return this.centre;
  }

  /** Announce a highlight. Called with the effect's OWN label, never a re-lookup. */
  announce(label: string): void {
    this.live.textContent = label;
  }

  clear(): void {
    while (this.layer.firstChild) this.layer.removeChild(this.layer.firstChild);
    this.live.textContent = '';
  }

  /** Redraw from the session's read-only view. */
  render(view: RingView | null): void {
    while (this.layer.firstChild) this.layer.removeChild(this.layer.firstChild);
    if (!view || !view.geometry) return;

    const theme = readTheme();
    const { x: cx, y: cy } = this.centre;
    const { r0, r1 } = view.geometry;
    const n = view.items.length;
    const half = 180 / n;

    const root = el('g', { class: 'rad-root' });
    root.setAttribute('role', 'menu');
    root.setAttribute('aria-label', view.title || 'menu');

    for (let i = 0; i < n; i++) {
      const item = view.items[i];
      const mid = itemCenterDeg(i, n);
      const a0 = mid - half;
      const a1 = mid + half;
      const active = view.highlight === i;

      const fill = active
        ? item.destructive
          ? theme.danger
          : theme.wedgeHi
        : item.swatch
          ? resolveToken(item.swatch)
          : theme.wedge;

      const wedge = el('path', {
        d: arcPath(cx, cy, r0, r1, a0, a1),
        fill,
        stroke: theme.stroke,
        'stroke-width': 1,
        opacity: item.enabled ? 1 : 0.35,
      });
      wedge.setAttribute('role', 'menuitem');
      wedge.setAttribute('aria-label', item.label);
      if (!item.enabled) wedge.setAttribute('aria-disabled', 'true');
      if (item.hasChildren) wedge.setAttribute('aria-haspopup', 'true');
      root.appendChild(wedge);

      // Label at mid-band, upright regardless of wedge angle.
      const rad = (mid * Math.PI) / 180;
      const lr = (r0 + r1) / 2;
      const label = el('text', {
        x: cx + lr * Math.cos(rad),
        y: cy + lr * Math.sin(rad),
        'text-anchor': 'middle',
        'dominant-baseline': 'central',
        'font-size': 11,
        'pointer-events': 'none',
        fill: active ? theme.textHi : theme.text,
      });
      label.textContent = shorten(item.label) + (item.hasChildren ? ' ▸' : '');
      root.appendChild(label);
    }

    // Hub: the back/cancel affordance, and where the submenu title lives.
    const hub = el('circle', {
      cx,
      cy,
      r: r0,
      fill: theme.hub,
      stroke: theme.stroke,
      'stroke-width': 1,
    });
    root.appendChild(hub);

    if (view.depth > 1 && view.title) {
      const t = el('text', {
        x: cx,
        y: cy,
        'text-anchor': 'middle',
        'dominant-baseline': 'central',
        'font-size': 10,
        fill: theme.text,
        'pointer-events': 'none',
      });
      t.textContent = shorten(view.title, 10);
      root.appendChild(t);
    }

    this.layer.appendChild(root);
  }

  destroy(): void {
    this.layer.remove();
    this.live.remove();
  }
}
