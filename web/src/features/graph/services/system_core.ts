/**
 * The platform-free half of the system monitor: types, the definition
 * registry, and the pure layout/replay functions.
 *
 * Split from `system_renderer.ts` for the same two reasons rad's core is
 * split from its renderer: pure functions get tested as pure functions
 * (`npm run test:system`, milliseconds, no browser), and the compile for
 * that build omits the DOM lib, so a stray `document` in here is a compile
 * error before it is a review comment.
 */

// ─── Diagram types ───────────────────────────────────────────────────────────

/** A node in a system architecture diagram. Position is fractional [0,1]. */
export interface SystemNode {
  label: string;
  sub?: string;
  /** Horizontal position: 0 = left edge, 1 = right edge */
  px: number;
  /** Vertical position: 0 = top edge, 1 = bottom edge */
  py: number;
  /** Arbitrary category string — drives default border color */
  type: string;
}

/** A directed edge between two nodes. */
export interface SystemEdge {
  from: string;
  to: string;
  style: 'solid' | 'dashed' | 'dim';
  label?: string;
}

/**
 * A generic event from the system being visualized.
 * Requires at minimum `event_type` (string) and optionally `timestamp` (seconds).
 * All other fields are definition-specific.
 */
export interface SystemEvent {
  event_type: string;
  timestamp?: number;
  [key: string]: unknown;
}

/** Visual state of a rendered node. */
export type SystemNodeState = 'idle' | 'active' | 'success' | 'failed';

// ─── SystemDefinition plugin API ─────────────────────────────────────────────

/**
 * Callbacks passed into SystemDefinition.handleEvent() so definition objects
 * can drive the renderer without holding a `this` reference.
 */
export interface SystemRendererCallbacks {
  setNodeState(id: string, state: SystemNodeState): void;
  firePacket(from: string, to: string, color: string): void;
  log(text: string, level: 'ok' | 'err' | 'warn' | 'dim'): void;
  resetAllNodes(): void;
}

/**
 * A self-contained system definition.
 * Register an instance with SystemDefinitionRegistry to make it selectable
 * from the control panel.
 */
export interface SystemDefinition {
  id: string;
  name: string;
  description: string;
  getNodes(): Record<string, SystemNode>;
  getEdges(): SystemEdge[];
  getDemoEvents(): SystemEvent[];
  handleEvent(ev: SystemEvent, cb: SystemRendererCallbacks): void;
  /** WebSocket path relative to wsBase, e.g. '/pam/ws/live'; '' for none. */
  wsPath: string;
  /** HTTP status/health path, e.g. '/pam/status' */
  httpStatusPath: string;
  /**
   * Optional async preparation, awaited before the diagram is built.
   * A definition whose picture is derived from a backend (see
   * derived_system.ts) fetches here; a hand-drawn one omits it.
   * Throwing makes the renderer show the failure instead of a diagram —
   * a monitor that silently drew an empty system would read as a quiet one.
   */
  load?(ctx: { httpBase: string }): Promise<void>;
  /** Optional per-type node color override; falls back to the built-in map. */
  nodeTypeColor?(type: string): string | undefined;
}

/** Registry of all registered SystemDefinitions. */
export class SystemDefinitionRegistry {
  private static _defs = new Map<string, SystemDefinition>();

  static register(def: SystemDefinition): void {
    this._defs.set(def.id, def);
  }

  static get(id: string): SystemDefinition | undefined {
    return this._defs.get(id);
  }

  static all(): SystemDefinition[] {
    return [...this._defs.values()];
  }

  /** Returns the first registered definition, or undefined if none registered. */
  static default(): SystemDefinition | undefined {
    return this._defs.values().next().value as SystemDefinition | undefined;
  }
}

// ─── Backend document shapes (the /system router's JSON) ────────────────────

export interface ComposedComponent {
  id: string;
  name: string;
  role: string;       // 'chart' | 'deployer' | 'infrastructure' | 'application'
  group: string;
  version: string;
  upstreams: string[];
}

export interface ComposedDoc {
  system: string;
  commit: string;
  components: ComposedComponent[];
  edges: { source: string; target: string; kind: string }[];
}

export interface EventsDoc {
  changes: { sha: string; when: string; subject: string; components: string[] }[];
  in_flight: { branch: string; commits: number; components: string[] }[];
}

// ─── Layout ──────────────────────────────────────────────────────────────────

/** Column position per role. Deployers sit between infrastructure and what
 *  they deploy, which is the direction change actually flows. */
export const ROLE_COLUMN: Record<string, number> = {
  infrastructure: 0.07,
  deployer: 0.28,
  chart: 0.55,
  application: 0.9,
};

/** A role column with more rows than this splits into further columns —
 *  twenty-one charts in one column is a list, not a diagram. */
export const MAX_ROWS = 12;

export function layoutNodes(doc: ComposedDoc): Record<string, SystemNode> {
  const byRole = new Map<string, ComposedComponent[]>();
  for (const component of doc.components) {
    const list = byRole.get(component.role) ?? [];
    list.push(component);
    byRole.set(component.role, list);
  }

  const nodes: Record<string, SystemNode> = {};
  for (const [role, list] of byRole) {
    const baseX = ROLE_COLUMN[role] ?? 0.5;
    const columns = Math.max(1, Math.ceil(list.length / MAX_ROWS));
    const rows = Math.ceil(list.length / columns);
    // The sideways spread never walks off the canvas: at four or more
    // columns a fixed step put the rightmost at px > 1 (found by the unit-
    // square test at forty charts), so the step shrinks to fit inside 0.97.
    const step = columns === 1 ? 0
      : Math.min(0.16, (0.97 - baseX) / (columns - 1));
    list.forEach((component, index) => {
      const column = Math.floor(index / rows);
      const row = index % rows;
      nodes[component.id] = {
        label: component.name,
        sub: component.version || role,
        px: baseX + column * step,
        // Vertical span 0.06..0.94, evenly distributed. A single node sits
        // centred rather than at the top.
        py: rows === 1 ? 0.5 : 0.06 + (row / (rows - 1)) * 0.88,
        type: role,
      };
    });
  }
  return nodes;
}

export function layoutEdges(doc: ComposedDoc): SystemEdge[] {
  return doc.edges.map(edge => ({
    from: edge.source,
    to: edge.target,
    style: edge.kind === 'deploys' ? 'dashed' : 'dim',
    label: edge.kind,
  }));
}

// ─── Events → demo sequence ──────────────────────────────────────────────────

/** The replayed history as a timed demo, so demo mode shows the same truth
 *  the websocket replays — one sequence, two transports. */
export function demoFrom(events: EventsDoc, pace = 1.4): SystemEvent[] {
  const out: SystemEvent[] = [];
  let at = 0.5;
  for (const change of events.changes) {
    out.push({
      event_type: 'change', replay: true, timestamp: at,
      sha: change.sha, when: change.when, subject: change.subject,
      components: change.components,
    });
    at += pace;
  }
  for (const branch of events.in_flight) {
    out.push({
      event_type: 'in_flight', replay: true, timestamp: at,
      branch: branch.branch, commits: branch.commits,
      components: branch.components,
    });
    at += pace;
  }
  out.push({ event_type: 'replay_done', replay: true, timestamp: at });
  return out;
}
