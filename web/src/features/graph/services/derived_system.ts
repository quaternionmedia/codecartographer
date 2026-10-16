/**
 * A SystemDefinition derived from a repository's own contents.
 *
 * The PAM definition is hand-drawn because the PAM stack is a known, fixed
 * system. This one asks the backend (`/system/compose`) what a repository
 * declares — charts, deployers, infrastructure, applications, deploy and
 * dependency edges — and lays that out. moat's homelab is the worked case:
 * the diagram is about the SYSTEM THE REPO DESCRIBES, never about the repo,
 * and a chart added to the repository appears here without anyone editing a
 * layout.
 *
 * Events are the history of the same contents (`/system/events`): commits
 * mapped onto the components they touched, and branches ahead of the default
 * branch as in-flight changes — the offline proxy for open pull requests,
 * labelled as a proxy. The websocket replays them with pacing; every frame
 * carries `replay: true` and the log says REPLAY, because dressing history up
 * as a live tail would teach a reader the homelab is busier than it is.
 */

import {
  SystemDefinition,
  SystemEvent,
  SystemNode,
  SystemEdge,
  SystemRendererCallbacks,
  ComposedDoc,
  EventsDoc,
  layoutNodes,
  layoutEdges,
  demoFrom,
} from './system_core';

// ─── The definition ──────────────────────────────────────────────────────────

const CYAN   = '#00d4ff';
const ORANGE = '#ff6b35';

export class DerivedSystemDefinition implements SystemDefinition {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly wsPath: string;
  readonly httpStatusPath: string;

  private _doc: ComposedDoc | null = null;
  private _events: EventsDoc | null = null;
  private _deployerOf = new Map<string, string>();

  constructor(private readonly repo: string) {
    this.id = repo;
    this.name = `${repo} (derived)`;
    this.description = `System derived from the ${repo} repository's contents`;
    this.wsPath = `/system/ws/replay?repo=${encodeURIComponent(repo)}`;
    this.httpStatusPath = `/system/compose?repo=${encodeURIComponent(repo)}`;
  }

  async load(ctx: { httpBase: string }): Promise<void> {
    const composed = await fetch(
      `${ctx.httpBase}/system/compose?repo=${encodeURIComponent(this.repo)}`);
    if (!composed.ok) {
      throw new Error(`compose returned ${composed.status}`);
    }
    this._doc = await composed.json() as ComposedDoc;

    // Events are the demo sequence; a failure here leaves the diagram
    // standing with an empty history, which is stated, not hidden.
    const events = await fetch(
      `${ctx.httpBase}/system/events?repo=${encodeURIComponent(this.repo)}`);
    this._events = events.ok ? await events.json() as EventsDoc
                             : { changes: [], in_flight: [] };

    this._deployerOf.clear();
    for (const edge of this._doc.edges) {
      if (edge.kind === 'deploys') this._deployerOf.set(edge.target, edge.source);
    }
  }

  getNodes(): Record<string, SystemNode> {
    return this._doc ? layoutNodes(this._doc) : {};
  }

  getEdges(): SystemEdge[] {
    return this._doc ? layoutEdges(this._doc) : [];
  }

  getDemoEvents(): SystemEvent[] {
    if (!this._events) return [];
    const demo = demoFrom(this._events);
    return demo.length > 1 ? demo : [{
      event_type: 'replay_done', replay: true, timestamp: 1,
    }];
  }

  nodeTypeColor(type: string): string | undefined {
    const map: Record<string, string> = {
      infrastructure: 'var(--c-warning,   #ffcc00)',
      deployer:       'var(--c-accent,    #00d4ff)',
      chart:          'var(--c-secondary, #00ff41)',
      application:    'var(--c-font,      #cce4f5)',
    };
    return map[type];
  }

  handleEvent(ev: SystemEvent, cb: SystemRendererCallbacks): void {
    const components = (ev.components as string[] | undefined) ?? [];

    switch (ev.event_type) {
      case 'change': {
        const subject = (ev.subject as string | undefined) ?? '';
        const when = (ev.when as string | undefined) ?? '';
        cb.log(`REPLAY ${when} ${subject}`, 'dim');
        for (const id of components) {
          cb.setNodeState(id, 'active');
          const deployer = this._deployerOf.get(id);
          if (deployer) cb.firePacket(deployer, id, CYAN);
        }
        // A change is history that landed: settle to success shortly after.
        setTimeout(() => {
          for (const id of components) cb.setNodeState(id, 'success');
        }, 900);
        break;
      }

      case 'in_flight': {
        const branch = (ev.branch as string | undefined) ?? '?';
        const commits = (ev.commits as number | undefined) ?? 0;
        cb.log(
          `IN FLIGHT ${branch}: ${commits} commit(s) not on the default `
          + `branch — pull request state lives on the host and is not read here`,
          'warn');
        for (const id of components) {
          cb.setNodeState(id, 'active');
          const deployer = this._deployerOf.get(id);
          if (deployer) cb.firePacket(deployer, id, ORANGE);
        }
        break;
      }

      case 'replay_done':
        cb.log('replay complete — this was history, not a live tail', 'ok');
        setTimeout(() => cb.resetAllNodes(), 2500);
        break;
    }
  }
}
