/**
 * codecartographer's `resolve(context) → MenuSpec`.
 *
 * Pure by construction: everything it needs about the graph arrives as plain
 * data in `MenuFacts`, computed by the caller. That is a deliberate departure
 * from the legacy menu, which closed over renderer state — and it is what
 * makes the menu content testable without a graph, a DOM, or a network.
 *
 * Item construction is conditional spread, never post-filtering of a master
 * list, per contract §1. A ring is built correct rather than trimmed correct.
 *
 * No application imports, so this compiles into the conformance build and the
 * menu-as-superset rule can be asserted rather than reviewed.
 */
import type { MenuContext, MenuItem, MenuSpec } from '../core/types.js';
import { HOST_VERBS } from './vocabulary.js';

/**
 * What the host knows about the thing the menu was opened on.
 *
 * All optional: an absent fact disables the item that depends on it, which is
 * how a menu opened on a partially-streamed graph stays honest.
 */
export interface MenuFacts {
  /** Unified-schema depth: 0 dir, 1 file, 2 symbol. */
  depth?: number;
  /** Unified-schema kind, e.g. 'function', 'class', 'directory'. */
  kind?: string;
  /** True when this node's children are already on the canvas. */
  hasRenderedChildren?: boolean;
  /** True when the node is currently pinned. */
  pinned?: boolean;
  /** True when a forge URL and line number are resolvable for this node. */
  hasSource?: boolean;
  /** True when this node belongs to a compound cluster with bounds. */
  hasGroup?: boolean;
  /** Number of nodes currently selected. */
  selectionCount?: number;
  /** True when at least one node is hidden. */
  anyHidden?: boolean;
  /** True when the force simulation exists on this renderer. */
  physicsAvailable?: boolean;
}

/** Palette tokens, never literals — contract §1. */
const COLOUR_RING: MenuItem[] = [
  { id: 'color-sky', label: 'Sky', action: 'color:sky', swatch: 'sky' },
  { id: 'color-calm', label: 'Calm', action: 'color:calm', swatch: 'calm' },
  { id: 'color-royal', label: 'Royal', action: 'color:royal', swatch: 'royal' },
  { id: 'color-gold', label: 'Gold', action: 'color:gold', swatch: 'gold' },
  { id: 'color-signal', label: 'Signal', action: 'color:signal', swatch: 'signal' },
];

/**
 * Depth 2 is the deepest tier the parser emits, so a symbol has nothing to
 * expand into. Expanding is what makes a large repo navigable, so it takes
 * the 12 o'clock wedge — index 0, the one a straight-up flick reaches.
 */
function nodeRing(f: MenuFacts): MenuItem[] {
  const canExpand = (f.depth ?? 0) < 2;
  return [
    { id: 'expand', label: 'Expand', action: 'expand', enabled: canExpand },
    { id: 'collapse', label: 'Collapse', action: 'collapse', enabled: !!f.hasRenderedChildren },
    { id: 'neighbors', label: 'Neighbours', action: 'select-neighbors' },
    { id: 'pin', label: f.pinned ? 'Unpin' : 'Pin', action: 'pin' },
    { id: 'colour', label: 'Colour', children: COLOUR_RING },
    {
      id: 'view',
      label: 'View',
      children: [
        { id: 'source', label: 'Source', action: HOST_VERBS.VIEW_SOURCE, enabled: !!f.hasSource },
        { id: 'info', label: 'Info', action: HOST_VERBS.NODE_INFO },
        { id: 'focus', label: 'Focus', action: HOST_VERBS.FOCUS_GROUP, enabled: !!f.hasGroup },
      ],
    },
    { id: 'hide', label: 'Hide', action: 'hide' },
    { id: 'delete', label: 'Delete', action: 'delete', destructive: true },
  ];
}

function canvasRing(f: MenuFacts): MenuItem[] {
  return [
    { id: 'fit', label: 'Fit', action: 'fit' },
    { id: 'relayout', label: 'Relayout', action: 'relayout' },
    { id: 'spread', label: 'Spread', action: 'spread' },
    { id: 'cluster', label: 'Cluster', action: 'cluster' },
    {
      id: 'physics',
      label: 'Physics',
      action: 'toggle-physics',
      enabled: !!f.physicsAvailable,
    },
    { id: 'unhide', label: 'Unhide', action: 'show-hidden', enabled: !!f.anyHidden },
    {
      id: 'clear',
      label: 'Deselect',
      action: 'clear-selection',
      enabled: (f.selectionCount ?? 0) > 0,
    },
    { id: 'colour', label: 'Colour', children: COLOUR_RING },
  ];
}

function selectionRing(f: MenuFacts): MenuItem[] {
  return [
    { id: 'expand', label: 'Expand', action: 'expand' },
    { id: 'neighbors', label: 'Neighbours', action: 'select-neighbors' },
    { id: 'spread', label: 'Spread', action: 'spread' },
    { id: 'cluster', label: 'Cluster', action: 'cluster' },
    { id: 'colour', label: 'Colour', children: COLOUR_RING },
    { id: 'hide', label: 'Hide', action: 'hide' },
    { id: 'clear', label: 'Deselect', action: 'clear-selection' },
    {
      id: 'delete',
      label: `Delete ${f.selectionCount ?? 0}`,
      action: 'delete',
      destructive: true,
    },
  ];
}

/**
 * Edges here are derived facts about source, not authored objects, so the
 * standard `reverse` and `edit-label` verbs have no honest meaning. The ring
 * offers only what is true of a derived edge.
 */
function edgeRing(): MenuItem[] {
  return [
    { id: 'neighbors', label: 'Endpoints', action: 'select-neighbors' },
    { id: 'hide', label: 'Hide', action: 'hide' },
    { id: 'info', label: 'Info', action: HOST_VERBS.NODE_INFO },
  ];
}

export function resolveGraphMenu(context: MenuContext, facts: MenuFacts = {}): MenuSpec {
  switch (context.type) {
    case 'node':
      return { title: 'node', items: nodeRing(facts) };
    case 'edge':
      return { title: 'edge', items: edgeRing() };
    case 'selection':
      return { title: `${facts.selectionCount ?? context.targetIds.length} selected`, items: selectionRing(facts) };
    case 'canvas':
    default:
      return { title: 'canvas', items: canvasRing(facts) };
  }
}

/** Every verb any ring can commit. Used to assert menu-as-superset. */
export function allMenuVerbs(): string[] {
  const facts: MenuFacts = {
    depth: 0,
    hasRenderedChildren: true,
    hasSource: true,
    hasGroup: true,
    selectionCount: 2,
    anyHidden: true,
    physicsAvailable: true,
  };
  const seen = new Set<string>();
  const walk = (items: MenuItem[]) => {
    for (const i of items) {
      if (i.action) seen.add(i.action);
      if (i.children) walk(i.children);
    }
  };
  for (const type of ['node', 'edge', 'canvas', 'selection'] as const) {
    walk(resolveGraphMenu({ type, targetIds: ['x'], position: { x: 0, y: 0 } }, facts).items);
  }
  return [...seen].sort();
}
