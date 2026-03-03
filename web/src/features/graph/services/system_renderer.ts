import { IGraphRenderer } from './base_renderer';
import { GraphStylingOptions } from '../../../state/types';

// ─── Public types (exported for subclass use) ─────────────────────────────────

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
 * All other fields are subclass-specific.
 */
export interface SystemEvent {
  event_type: string;
  timestamp?: number;
  [key: string]: unknown;
}

/** Visual state of a rendered node. */
export type SystemNodeState = 'idle' | 'active' | 'success' | 'failed';

// ─── SystemDefinition plugin API ──────────────────────────────────────────────

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
 * A self-contained system architecture definition.
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
  /** WebSocket path relative to wsBase, e.g. '/pam/ws/live' */
  wsPath: string;
  /** HTTP status/health path, e.g. '/pam/status' */
  httpStatusPath: string;
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

// ─── Cubic bezier helper ──────────────────────────────────────────────────────

function cubicBezier(
  x0: number, y0: number,
  x1: number, y1: number,
  x2: number, y2: number,
  x3: number, y3: number,
  t: number
): { x: number; y: number } {
  const u = 1 - t;
  return {
    x: u*u*u*x0 + 3*u*u*t*x1 + 3*u*t*t*x2 + t*t*t*x3,
    y: u*u*u*y0 + 3*u*u*t*y1 + 3*u*t*t*y2 + t*t*t*y3,
  };
}

function edgeKey(from: string, to: string): string {
  return `${from}\u2192${to}`;
}

// ─── Abstract SystemRenderer ──────────────────────────────────────────────────

/**
 * Abstract base class for fixed-layout system architecture renderers with live event feeds.
 *
 * Provides all shared infrastructure:
 *   - DOM layout (header, SVG edge layer, node overlay, log strip)
 *   - SVG bezier edge rendering with ResizeObserver
 *   - Packet animation (requestAnimationFrame along cubic bezier)
 *   - WebSocket lifecycle (connect, backfill, reconnect → demo fallback)
 *   - Demo loop (schedules getDemoEvents() via handleEvent())
 *   - Node state management and CSS class toggling
 *   - Log strip with level coloring
 *
 * Subclasses must implement:
 *   - `type` / `name` (IGraphRenderer identity)
 *   - `getNodes()` → Record<string, SystemNode>
 *   - `getEdges()` → SystemEdge[]
 *   - `getDemoEvents()` → SystemEvent[]  (each event needs a `timestamp` in seconds)
 *   - `handleEvent(ev)` → void  (maps event fields to setNodeState / firePacket calls)
 *
 * Subclasses may optionally override:
 *   - `nodeTypeColor(type)` → CSS color string
 *
 * See `pam_renderer.ts` for a complete worked example.
 */
export abstract class SystemRenderer implements IGraphRenderer {
  // ── IGraphRenderer identity ───────────────────────────────────────────────
  readonly type = 'system';
  /** Human-readable name shown in the header and control panel. */
  abstract readonly name: string;

  // ── Abstract data providers — implemented by each concrete subclass ────────
  /** Return the nodes for this system diagram. */
  protected abstract getNodes(): Record<string, SystemNode>;
  /** Return the edges for this system diagram. */
  protected abstract getEdges(): SystemEdge[];
  /** Return the demo event sequence (each event needs a `timestamp` in seconds). */
  protected abstract getDemoEvents(): SystemEvent[];
  /**
   * Handle a single system event and update visual state.
   * Use the protected helpers (setNodeState, firePacket, log, resetAllNodes)
   * to drive the renderer.
   */
  protected abstract handleEvent(ev: SystemEvent): void;
  /**
   * WebSocket path relative to the base URL for live event streaming.
   * Example: '/pam/ws/live'
   */
  protected abstract readonly wsPath: string;

  // ── Private state (internal to SystemRenderer) ────────────────────────────
  private _nodeEls: Map<string, HTMLElement> = new Map();
  private _edgePaths: Map<string, SVGPathElement> = new Map();
  private _packetLayer: HTMLElement | null = null;
  private _logEl: HTMLElement | null = null;
  private _badgeEl: HTMLElement | null = null;
  private _statsEl: HTMLElement | null = null;
  private _ws: WebSocket | null = null;
  private _demoTimers: ReturnType<typeof setTimeout>[] = [];
  private _eventCount = 0;
  private _resizeObserver: ResizeObserver | null = null;

  // ── IGraphRenderer ────────────────────────────────────────────────────────

  render(container: HTMLElement, _data: unknown, styling?: GraphStylingOptions): void {
    container.innerHTML = '';
    this._nodeEls.clear();
    this._edgePaths.clear();
    this._eventCount = 0;

    this._injectStyles(container);
    this._buildLayout(container);
    this._runDemo();

    const s = styling as Record<string, unknown> | undefined;
    const wsBase = s?.systemWsBase as string | undefined;
    const mode   = s?.pamMode      as string | undefined;
    if (mode !== 'demo' && wsBase) {
      this._connectLive(`${wsBase}${this.wsPath}`);
    }
  }

  canHandle(_data: unknown): boolean {
    // System renderers are explicitly selected, never auto-detected
    return false;
  }

  cleanup(): void {
    this._ws?.close();
    this._ws = null;
    this._demoTimers.forEach(clearTimeout);
    this._demoTimers = [];
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._nodeEls.clear();
    this._edgePaths.clear();
    this._packetLayer = null;
    this._logEl = null;
    this._badgeEl = null;
    this._statsEl = null;
    this._eventCount = 0;
  }

  // ── Protected helpers available to subclasses ─────────────────────────────

  /** Set the visual state of a node by ID. */
  protected setNodeState(id: string, state: SystemNodeState): void {
    const el = this._nodeEls.get(id);
    if (!el) return;
    el.className = el.className.replace(
      /sys-node--(idle|active|success|failed)/,
      `sys-node--${state}`
    );
  }

  /** Reset all nodes to idle state. */
  protected resetAllNodes(): void {
    for (const id of this._nodeEls.keys()) {
      this.setNodeState(id, 'idle');
    }
  }

  /**
   * Animate a glowing packet dot from one node to another along the bezier path.
   * Also briefly activates the edge color.
   */
  protected firePacket(from: string, to: string, color: string): void {
    const layer = this._packetLayer;
    if (!layer) return;
    const mainEl = layer.parentElement;
    if (!mainEl) return;
    const rect = mainEl.getBoundingClientRect();
    if (rect.width < 10) return;

    const nodes = this.getNodes();
    const nodeA = nodes[from];
    const nodeB = nodes[to];
    if (!nodeA || !nodeB) return;

    const ax = nodeA.px * rect.width;
    const ay = nodeA.py * rect.height;
    const bx = nodeB.px * rect.width;
    const by = nodeB.py * rect.height;
    const cx = ax + (bx - ax) * 0.55;

    const dot = document.createElement('div');
    dot.className = 'sys-packet';
    dot.style.background = color;
    dot.style.boxShadow = `0 0 7px ${color}`;
    layer.appendChild(dot);

    const FRAMES = 40;
    let frame = 0;
    const tick = (): void => {
      if (!layer.contains(dot)) return;
      const t = frame / FRAMES;
      const pos = cubicBezier(ax, ay, cx, ay, cx, by, bx, by, t);
      dot.style.left = pos.x + 'px';
      dot.style.top  = pos.y + 'px';
      frame++;
      if (frame <= FRAMES) requestAnimationFrame(tick);
      else dot.remove();
    };
    requestAnimationFrame(tick);
    this._activateEdge(from, to, color);
  }

  /** Append a line to the log strip. */
  protected log(text: string, level: 'ok' | 'err' | 'warn' | 'dim'): void {
    const el = this._logEl;
    if (!el) return;
    const line = document.createElement('div');
    line.className = `sys-log-line sys-log-line--${level}`;
    const ts = new Date().toISOString().slice(11, 23);
    line.textContent = `[${ts}] ${text}`;
    el.appendChild(line);
    // Keep last 200 lines to avoid unbounded growth
    while (el.children.length > 200) el.removeChild(el.firstChild!);
    el.scrollTop = el.scrollHeight;
  }

  /** Update the header connection badge. */
  protected setBadge(text: string, cls: 'demo' | 'live' | 'connect' | 'offline'): void {
    if (!this._badgeEl) return;
    this._badgeEl.textContent = text;
    this._badgeEl.className = `sys-badge sys-badge--${cls}`;
  }

  /**
   * Return a CSS color string for a node type.
   * Override in subclasses to add custom types.
   */
  protected nodeTypeColor(type: string): string {
    const map: Record<string, string> = {
      service:  'var(--c-accent,     #00d4ff)',
      core:     'var(--c-font,       #00ff41)',
      auth:     'var(--c-secondary,  #00ff41)',
      account:  'var(--c-secondary,  #00ff41)',
      session:  'var(--c-warning,    #ffcc00)',
      backend:  'var(--c-accent,     #00d4ff)',
      process:  'var(--c-secondary,  #00ff41)',
      network:  'var(--c-accent,     #00d4ff)',
      storage:  'var(--c-warning,    #ffcc00)',
      external: 'var(--c-font-muted, #3a5570)',
    };
    return map[type] ?? 'var(--c-font, #cce4f5)';
  }

  // ── Private implementation ────────────────────────────────────────────────

  private _activateEdge(from: string, to: string, color: string): void {
    const path = this._edgePaths.get(edgeKey(from, to));
    if (!path) return;
    path.style.stroke = color;
    path.style.strokeOpacity = '0.75';
    setTimeout(() => {
      if (path) {
        path.style.stroke = 'var(--c-font-muted, #3a5570)';
        path.style.strokeOpacity = '0.20';
      }
    }, 1200);
  }

  private _injectStyles(container: HTMLElement): void {
    const style = document.createElement('style');
    style.textContent = `
      .sys-wrap {
        display: flex; flex-direction: column; height: 100%; overflow: hidden;
        background: var(--c-bg, #05080d);
        font-family: 'Share Tech Mono', 'Courier New', monospace;
        color: var(--c-font, #7a9db8);
      }
      .sys-header {
        height: 40px; flex-shrink: 0; display: flex; align-items: center;
        padding: 0 14px; gap: 12px;
        border-bottom: 1px solid var(--c-border, #132030);
        background: var(--c-primary, #08111a);
      }
      .sys-title {
        font-size: .65rem; letter-spacing: 4px;
        color: var(--c-accent, #00d4ff); text-transform: uppercase; white-space: nowrap;
      }
      .sys-stats { font-size: .58rem; color: var(--c-font-muted, #3a5570); flex: 1; }
      .sys-badge {
        font-size: .55rem; padding: 2px 8px; border: 1px solid;
        letter-spacing: 2px; text-transform: uppercase; transition: all .3s; white-space: nowrap;
      }
      .sys-badge--demo    { color: #ffd600; border-color: #ffd600; }
      .sys-badge--live    { color: var(--c-accent, #00d4ff); border-color: var(--c-accent, #00d4ff); }
      .sys-badge--connect { color: #b060ff; border-color: #b060ff; }
      .sys-badge--offline { color: var(--c-error, #ff3333); border-color: var(--c-error, #ff3333); }
      .sys-main { flex: 1; position: relative; overflow: hidden; min-height: 0; }
      .sys-svg  { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
      .sys-nodes   { position: absolute; inset: 0; }
      .sys-packets { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
      .sys-node {
        position: absolute; transform: translate(-50%, -50%);
        padding: 5px 8px; border: 1px solid var(--c-border, #132030);
        background: var(--c-primary, #08111a); min-width: 92px; text-align: center;
        transition: border-color .25s, box-shadow .25s; user-select: none; cursor: default;
      }
      .sys-node--idle    { border-color: var(--c-border, #132030); }
      .sys-node--active  { border-color: #00d4ff; box-shadow: 0 0 8px rgba(0,212,255,.35); }
      .sys-node--success { border-color: var(--c-accent, #00ffb3); box-shadow: 0 0 8px rgba(0,255,179,.35); }
      .sys-node--failed  { border-color: var(--c-error,  #ff2d55); box-shadow: 0 0 8px rgba(255,45,85,.35);  }
      .sys-node-badge {
        position: absolute; top: -7px; right: 4px; font-size: .45rem;
        padding: 1px 4px; border: 1px solid; display: none;
      }
      .sys-node--success .sys-node-badge {
        display: block;
        color: var(--c-accent, #00ffb3); border-color: var(--c-accent, #00ffb3);
      }
      .sys-node-tag {
        font-size: .46rem; letter-spacing: 2px; text-transform: uppercase;
        color: var(--c-font-muted, #3a5570);
      }
      .sys-node-label { font-size: .62rem; color: var(--c-font, #cce4f5); margin-top: 2px; }
      .sys-node-sub   { font-size: .5rem;  color: var(--c-font-muted, #3a5570); margin-top: 1px; }
      .sys-packet {
        position: absolute; width: 7px; height: 7px; border-radius: 50%;
        transform: translate(-50%, -50%); pointer-events: none;
      }
      .sys-log {
        height: 100px; flex-shrink: 0; overflow-y: auto;
        border-top: 1px solid var(--c-border, #132030);
        padding: 4px 10px; font-size: .62rem; line-height: 1.5;
        background: var(--c-bg, #05080d);
      }
      .sys-log::-webkit-scrollbar { width: 3px; }
      .sys-log::-webkit-scrollbar-thumb { background: var(--c-border, #132030); }
      .sys-log-line { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .sys-log-line--ok   { color: var(--c-accent, #00ffb3); }
      .sys-log-line--err  { color: var(--c-error,  #ff2d55); }
      .sys-log-line--warn { color: #ffd600; }
      .sys-log-line--dim  { color: var(--c-font-muted, #3a5570); }
    `;
    container.appendChild(style);
  }

  private _buildLayout(container: HTMLElement): void {
    const wrap = document.createElement('div');
    wrap.className = 'sys-wrap';
    container.appendChild(wrap);

    // Header
    const header = document.createElement('div');
    header.className = 'sys-header';

    const title = document.createElement('div');
    title.className = 'sys-title';
    title.textContent = this.name;
    header.appendChild(title);

    this._statsEl = document.createElement('div');
    this._statsEl.className = 'sys-stats';
    this._statsEl.textContent = 'events: 0';
    header.appendChild(this._statsEl);

    this._badgeEl = document.createElement('div');
    this._badgeEl.className = 'sys-badge sys-badge--demo';
    this._badgeEl.textContent = 'DEMO';
    header.appendChild(this._badgeEl);
    wrap.appendChild(header);

    // Main graph area
    const main = document.createElement('div');
    main.className = 'sys-main';
    wrap.appendChild(main);

    // SVG edge layer
    const svgNs = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNs, 'svg') as SVGSVGElement;
    svg.setAttribute('class', 'sys-svg');

    // Arrowhead marker
    const defs = document.createElementNS(svgNs, 'defs');
    const marker = document.createElementNS(svgNs, 'marker');
    marker.setAttribute('id', `sys-arrow-${this.type}`);
    marker.setAttribute('markerWidth', '8');
    marker.setAttribute('markerHeight', '8');
    marker.setAttribute('refX', '7');
    marker.setAttribute('refY', '3');
    marker.setAttribute('orient', 'auto');
    const arrowPath = document.createElementNS(svgNs, 'path');
    arrowPath.setAttribute('d', 'M0,0 L0,6 L8,3 z');
    arrowPath.setAttribute('fill', 'var(--c-font-muted, #3a5570)');
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    svg.appendChild(defs);
    main.appendChild(svg);

    // Node overlay
    const nodeLayer = document.createElement('div');
    nodeLayer.className = 'sys-nodes';
    main.appendChild(nodeLayer);

    // Packet overlay
    this._packetLayer = document.createElement('div');
    this._packetLayer.className = 'sys-packets';
    main.appendChild(this._packetLayer);

    // Build node elements
    const nodes = this.getNodes();
    for (const [id, node] of Object.entries(nodes)) {
      const el = document.createElement('div');
      el.className = `sys-node sys-node--${node.type} sys-node--idle`;
      el.style.left = `${node.px * 100}%`;
      el.style.top  = `${node.py * 100}%`;

      const badge = document.createElement('div');
      badge.className = 'sys-node-badge';
      badge.textContent = 'OK';
      el.appendChild(badge);

      const tag = document.createElement('div');
      tag.className = 'sys-node-tag';
      tag.textContent = node.type.toUpperCase();
      el.appendChild(tag);

      const label = document.createElement('div');
      label.className = 'sys-node-label';
      label.textContent = node.label;
      el.appendChild(label);

      if (node.sub) {
        const sub = document.createElement('div');
        sub.className = 'sys-node-sub';
        sub.textContent = node.sub;
        el.appendChild(sub);
      }

      nodeLayer.appendChild(el);
      this._nodeEls.set(id, el);
    }

    // Build edges — requires actual pixel dimensions, use ResizeObserver
    const arrowMarkerId = `sys-arrow-${this.type}`;
    const drawEdges = (): void => {
      const rect = main.getBoundingClientRect();
      if (rect.width < 10) return;

      // Remove previous paths (keep defs)
      const children = Array.from(svg.childNodes);
      children.forEach(child => {
        if (child !== defs) svg.removeChild(child);
      });
      this._edgePaths.clear();

      const getCenter = (id: string): { x: number; y: number } => {
        const n = nodes[id];
        return { x: n.px * rect.width, y: n.py * rect.height };
      };

      for (const edge of this.getEdges()) {
        const a = getCenter(edge.from);
        const b = getCenter(edge.to);
        const dx = b.x - a.x;
        const cx = a.x + dx * 0.55;

        const path = document.createElementNS(svgNs, 'path');
        path.setAttribute('d', `M ${a.x} ${a.y} C ${cx} ${a.y}, ${cx} ${b.y}, ${b.x} ${b.y}`);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', 'var(--c-font-muted, #3a5570)');
        path.setAttribute('stroke-width', edge.style === 'dim' ? '1' : '1.2');
        path.setAttribute('stroke-opacity', '0.20');
        path.setAttribute('marker-end', `url(#${arrowMarkerId})`);
        if (edge.style === 'dashed') {
          path.setAttribute('stroke-dasharray', '4 4');
        }
        (path.style as CSSStyleDeclaration).transition = 'stroke .3s, stroke-opacity .3s';
        svg.appendChild(path);
        this._edgePaths.set(edgeKey(edge.from, edge.to), path);
      }
    };

    requestAnimationFrame(drawEdges);
    this._resizeObserver = new ResizeObserver(drawEdges);
    this._resizeObserver.observe(main);

    // Log strip
    this._logEl = document.createElement('div');
    this._logEl.className = 'sys-log';
    wrap.appendChild(this._logEl);
  }

  private _runDemo(): void {
    this.setBadge('DEMO', 'demo');
    this.resetAllNodes();
    const events = this.getDemoEvents();
    const timestamps = events.map(e => e.timestamp ?? 0);
    const last = timestamps.length > 0 ? Math.max(...timestamps) : 5;

    events.forEach(ev => {
      const t = setTimeout(() => {
        if (this._ws) return; // live mode took over
        this._eventCount++;
        if (this._statsEl) this._statsEl.textContent = `events: ${this._eventCount}`;
        this.handleEvent(ev);
      }, (ev.timestamp ?? 0) * 1000);
      this._demoTimers.push(t);
    });

    // Loop: restart 1.5s after the last event
    const loop = setTimeout(() => {
      if (!this._ws) this._runDemo();
    }, (last + 1.5) * 1000);
    this._demoTimers.push(loop);
  }

  private _connectLive(wsUrl: string): void {
    this.setBadge('CONNECTING', 'connect');
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      this.setBadge('OFFLINE', 'offline');
      this.log('WebSocket unavailable — staying in demo', 'warn');
      return;
    }
    this._ws = ws;

    ws.onopen = (): void => {
      this.setBadge('LIVE', 'live');
      // Cancel demo loop now that live data is flowing
      this._demoTimers.forEach(clearTimeout);
      this._demoTimers = [];
      this.resetAllNodes();
      this.log('WebSocket connected', 'ok');
    };

    ws.onclose = (): void => {
      this._ws = null;
      this.setBadge('OFFLINE', 'offline');
      this.log('WebSocket disconnected — reverting to demo', 'warn');
      this._runDemo();
    };

    ws.onerror = (): void => {
      ws.close();
    };

    ws.onmessage = (e: MessageEvent): void => {
      try {
        const msg = JSON.parse(e.data as string) as Record<string, unknown>;
        if (msg.type === 'event') {
          this._eventCount++;
          if (this._statsEl) this._statsEl.textContent = `events: ${this._eventCount}`;
          this.handleEvent(msg.data as SystemEvent);
        } else if (msg.type === 'backfill') {
          const events = msg.events as SystemEvent[];
          events.forEach(ev => {
            this._eventCount++;
            this.handleEvent(ev);
          });
          if (this._statsEl) this._statsEl.textContent = `events: ${this._eventCount}`;
        } else if (msg.type === 'connected') {
          const hostname = msg.hostname as string | undefined;
          if (hostname) this.log(`Connected to ${hostname}`, 'dim');
        }
      } catch {
        // Ignore malformed messages
      }
    };
  }
}
