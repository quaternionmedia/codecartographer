/**
 * Per-node view state, and the reducer that intents fold into it.
 *
 * Integration standard §5.1: "Route intents through the authoritative state
 * layer. Applying an intent by mutating the rendered scene directly is the
 * defect this project's own history records; the visual state must derive
 * from application state or it will not survive a re-render."
 *
 * So `hide`, `pin` and `color:*` do not touch the DOM. They produce a new
 * NodeViewState, the renderer applies it, and a re-render replays it. The
 * legacy menu's `d3.selectAll(...).attr('opacity', 0)` was invisible to
 * every other part of the application and vanished on the next redraw.
 *
 * Pure and app-import-free, so it compiles into the conformance build and is
 * tested without a graph.
 */

export interface NodeView {
  hidden?: boolean;
  pinned?: boolean;
  /** A palette TOKEN — 'sky', 'signal', … — never a resolved colour. */
  colorToken?: string;
}

/** Sparse by design: an untouched node has no entry, not a default one. */
export type NodeViewState = Readonly<Record<string, NodeView>>;

export const EMPTY_VIEW_STATE: NodeViewState = Object.freeze({});

function patch(state: NodeViewState, ids: string[], change: NodeView): NodeViewState {
  if (!ids.length) return state;
  const next: Record<string, NodeView> = { ...state };
  for (const id of ids) {
    const merged = { ...next[id], ...change };
    // Drop keys that are back to their default so the map stays sparse and
    // two states that mean the same thing compare equal.
    for (const k of Object.keys(merged) as Array<keyof NodeView>) {
      if (merged[k] === undefined || merged[k] === false) delete merged[k];
    }
    if (Object.keys(merged).length) next[id] = merged;
    else delete next[id];
  }
  return next;
}

export const viewActions = {
  hide: (state: NodeViewState, ids: string[]): NodeViewState => patch(state, ids, { hidden: true }),

  showAll: (state: NodeViewState): NodeViewState => {
    const next: Record<string, NodeView> = {};
    for (const [id, v] of Object.entries(state)) {
      const { hidden, ...rest } = v;
      if (Object.keys(rest).length) next[id] = rest;
    }
    return next;
  },

  /** Toggles per node, so a mixed selection ends up uniformly pinned. */
  togglePin: (state: NodeViewState, ids: string[]): NodeViewState => {
    const anyUnpinned = ids.some((id) => !state[id]?.pinned);
    return patch(state, ids, { pinned: anyUnpinned });
  },

  colour: (state: NodeViewState, ids: string[], token: string): NodeViewState =>
    patch(state, ids, { colorToken: token }),

  /** Forget nodes entirely — used when they leave the graph. */
  forget: (state: NodeViewState, ids: string[]): NodeViewState => {
    if (!ids.length) return state;
    const next = { ...state };
    for (const id of ids) delete next[id];
    return next;
  },
};

export function anyHidden(state: NodeViewState): boolean {
  return Object.values(state).some((v) => v.hidden);
}

/** `color:sky` → `sky`. Returns null for any other verb. */
export function colourTokenOf(action: string): string | null {
  return action.startsWith('color:') ? action.slice('color:'.length) : null;
}
