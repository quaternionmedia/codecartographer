/**
 * The one live D3 canvas, and who to tell when it is replaced.
 *
 * **WHY A SEAM RATHER THAN A DIRECT CALL.** This application draws graphs from
 * two directions. `layout_context` streams a repository over SSE and owns the
 * renderer it created. `state/actions.ts` hands a finished `GraphData` to the
 * renderer registry, which builds its own canvas inside a Mithril vnode and
 * hands it back to nobody. Both produce a `StreamingGraphRenderer`; only the
 * first could mount anything against it, which is why the radial menu reached
 * repository plots and not Load Demo, and why the legend reached neither.
 *
 * A canvas announces itself here instead. Whoever needs to attach to the live
 * scene — the menu, the key, anything later — subscribes once and stops caring
 * which path drew it. ADR §7.
 *
 * **THE LAST ONE WINS, AND THERE IS ONLY EVER ONE.** Every render replaces the
 * container's contents, so a published surface supersedes its predecessor
 * absolutely. Subscribers are handed the new one and are responsible for
 * discarding whatever they had attached to the old.
 */

import type { StreamingGraphRenderer } from './streaming_renderer';

type Subscriber = (renderer: StreamingGraphRenderer) => void;

let live: StreamingGraphRenderer | null = null;
const subscribers = new Set<Subscriber>();

export const GraphSurface = {
  /**
   * Announce a freshly drawn canvas.
   *
   * Subscribers are called synchronously and in registration order. A throw
   * from one does not stop the rest: a menu that fails to mount must not also
   * cost the reader their legend, and the failure belongs in the console rather
   * than half-way up a render path that has already succeeded.
   */
  publish(renderer: StreamingGraphRenderer): void {
    live = renderer;
    for (const notify of subscribers) {
      try {
        notify(renderer);
      } catch (error) {
        console.error('GraphSurface subscriber failed', error);
      }
    }
  },

  /** The canvas currently on screen, or null before anything has been drawn. */
  current(): StreamingGraphRenderer | null {
    return live;
  },

  /** Subscribe. Returns the unsubscribe. Does not replay the current surface. */
  subscribe(notify: Subscriber): () => void {
    subscribers.add(notify);
    return () => {
      subscribers.delete(notify);
    };
  },

  /** Forget the live surface — the container was torn down, not replaced. */
  clear(): void {
    live = null;
  },
};
