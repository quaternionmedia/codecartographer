/**
 * codecartographer's rad vocabulary.
 *
 * This is host content, not contract — but it is pure data with no
 * application imports, so it compiles into the conformance build and the
 * prefix-free vector checks the words this host ACTUALLY binds rather than a
 * copy of them. One source, no drift.
 *
 * Standard vocabulary, per the interaction contract §1 (hosts may extend,
 * never repurpose):
 *   node      pin · hide · delete · expand · collapse · select-neighbors · color:*
 *   edge      delete · reverse · edit-label
 *   canvas    add-node · fit · relayout · toggle-physics
 *   selection hide · spread · cluster · delete
 *
 * What this host omits, and why — omitting a standard verb is allowed;
 * giving it different semantics is not:
 *   add-node    a code map's nodes come from parsing source. There is no
 *               meaningful "add" that is not an edit to a repository.
 *   reverse     an edge's direction is a fact about the code (A calls B).
 *   edit-label  likewise: a label is derived, not authored.
 */

/** Verbs this host extends the standard vocabulary with. */
export const HOST_VERBS = {
  /** Open the node's source at its line, on the origin forge. */
  VIEW_SOURCE: 'view-source',
  /** Show the node's parsed metadata. */
  NODE_INFO: 'node-info',
  /** Zoom/pan to the bounding circle of this node's compound cluster. */
  FOCUS_GROUP: 'focus-group',
} as const;

/**
 * Chord words → verbs. Contract §4: chords are accelerators over the SAME
 * verbs the menu resolves, never private functions, and the vocabulary must
 * be prefix-free so a known word finalizes on its last keystroke.
 *
 * Integration standard §5.3 makes "every chord-bound verb is also reachable
 * in the menu" a HOST obligation, since the host owns both surfaces. That is
 * asserted in tests/rad/vocabulary.test.mjs rather than left to review.
 */
export const CHORD_MAP: Record<string, string> = {
  xp: 'expand',
  co: 'collapse',
  nbr: 'select-neighbors',
  pin: 'pin',
  hd: 'hide',
  del: 'delete',
  fit: 'fit',
  fg: 'focus-group',
  lay: 'relayout',
  src: 'view-source',
  nfo: 'node-info',
  red: 'color:signal',
  blu: 'color:sky',
  tea: 'color:calm',
  vio: 'color:royal',
  gld: 'color:gold',
};

export const CHORD_WORDS: string[] = Object.keys(CHORD_MAP);

/**
 * Every verb this host can commit, from any surface. The menu is the
 * superset; this list is what the menu must cover.
 */
export const ALL_VERBS: string[] = [
  'expand',
  'collapse',
  'select-neighbors',
  'pin',
  'hide',
  'delete',
  'fit',
  'relayout',
  'toggle-physics',
  'spread',
  'cluster',
  'clear-selection',
  'show-hidden',
  HOST_VERBS.VIEW_SOURCE,
  HOST_VERBS.NODE_INFO,
  HOST_VERBS.FOCUS_GROUP,
  'color:signal',
  'color:sky',
  'color:calm',
  'color:royal',
  'color:gold',
];
