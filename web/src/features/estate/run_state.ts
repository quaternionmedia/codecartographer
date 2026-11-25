/**
 * Joining the harness's run states to the boxes on the canvas.
 *
 * `/harness/data` names a project for each state. A box names a place by its
 * address, `<owner>/<repo>` or `<owner>/<repo>/<kind>/<id>`. A state belongs
 * to every box whose address has that project as its repository, and a state
 * no box carries is returned as unmatched so a panel can say so.
 *
 * Pure: no DOM and no request, so `web/tests/pure/run-state.test.mjs` asserts
 * every branch under node.
 *
 * What it cannot do: tell two owners' repositories of one name apart. The
 * harness's rows carry the name alone.
 */

export type RunStateName = 'idle' | 'active' | 'success' | 'failed';

/** One entry of `/harness/data`'s `states`. */
export interface RunState {
  project: string;
  state: RunStateName;
  /** The row that gave the state, in the server's words. */
  because: string;
}

/** One list of `/harness/data`: the rows shown and what was held back. */
export interface HarnessListing {
  rows: Array<Record<string, unknown>>;
  shown: number;
  more: number;
  more_is_floor: boolean;
  problem: string;
  remedy: string;
  where: string;
}

export interface HarnessDocument {
  runs: HarnessListing;
  queue: HarnessListing;
  instructions: HarnessListing;
  states: RunState[];
  unplaced: Array<{ what: string; count: number; why: string }>;
  caveat: string;
}

/** As much of a drawn node as the join reads. */
export interface AddressedNode {
  id: string;
  address?: unknown;
  metadata?: unknown;
}

export interface Joined {
  /** Node id to the state its box carries. */
  byNode: Record<string, RunState>;
  /** States whose project no drawn box names. */
  unmatched: RunState[];
}

const STATES: readonly string[] = ['idle', 'active', 'success', 'failed'];

/** The address a node carries, wherever the graph format put it. */
export function addressOf(node: AddressedNode): string {
  if (typeof node.address === 'string') return node.address;
  const metadata = node.metadata as { address?: unknown } | undefined;
  return typeof metadata?.address === 'string' ? metadata.address : '';
}

/** The repository an address names, or the empty string when it names none. */
export function repoOf(address: string): string {
  const parts = address.split('/').filter((part) => part !== '');
  return parts.length >= 2 ? parts[1] : '';
}

/** Give each state to the boxes that name its project, and keep the rest. */
export function joinStates(states: readonly RunState[], nodes: readonly AddressedNode[]): Joined {
  const byProject = new Map<string, RunState>();
  for (const state of states) {
    if (state.project && STATES.includes(state.state)) byProject.set(state.project, state);
  }
  const byNode: Record<string, RunState> = {};
  const seen = new Set<string>();
  for (const node of nodes) {
    const state = byProject.get(repoOf(addressOf(node)));
    if (state) {
      byNode[node.id] = state;
      seen.add(state.project);
    }
  }
  const unmatched = [...byProject.values()].filter((state) => !seen.has(state.project));
  return { byNode, unmatched };
}

/** What a panel says under a list about the rows it does not show. */
export function heldBack(listing: Pick<HarnessListing, 'more' | 'more_is_floor'>): string {
  if (listing.more <= 0) return '';
  return listing.more_is_floor
    ? `at least ${listing.more} more the harness holds and this panel does not show`
    : `${listing.more} more the harness holds and this panel does not show`;
}
