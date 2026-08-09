/**
 * LayoutContext
 *
 * Central state-management hub for the Golden Layout integration.
 * Shared state hub for the Golden Layout panels so they can use the same
 * actions, streaming state, and callbacks without duplicating business logic.
 *
 * Usage:
 *   const ctx = new LayoutContext(initialCell);
 *   // pass ctx to each panel factory function
 */

import m from 'mithril';
import { LayoutManager } from 'golden-layout';
import type { LayoutConfig } from 'golden-layout';

import { ICell, ICellState } from '../state/cell_state';
import { StateController } from '../state/state_controller';
import { createActions, AppActions } from '../state/actions';
import { Directory, RawFile, RawFolder, RepoInfo } from '../components/models/source';
import {
  ControlPanelState,
  ControlPanelCallbacks,
  ControlPanelContent,
  LoadingProgress,
  CachedEntry,
} from '../components/codecarto/control_panel';
import { PlotService } from '../services/plot_service';
import { StreamingGraphRenderer } from '../features/graph/services/streaming_renderer';
import { ToastManager } from '../components/codecarto/help/toast';
import { DockPanelId, PanelRegistry } from './panel_registry';
import { DEFAULT_LAYOUT_CONFIG } from './default_layout';
import { GraphbaseService, GraphbaseBookmark, GraphbaseSnapshotMeta, GraphbaseHistoryMeta } from '../services/graphbase_service';
import { RadExtension } from '../features/graph/rad/host/rad_extension';
import { viewActions, EMPTY_VIEW_STATE, anyHidden } from '../features/graph/rad/host/view_state';
import type { NodeViewState } from '../features/graph/rad/host/view_state';
import type { GraphOps } from '../features/graph/rad/host/graph_intents';
import type { MenuContext } from '../features/graph/rad/core/types';
import type { GraphNode, GraphEdge } from '../features/graph/services/graph_renderer';

export type { DockPanelId } from './panel_registry';

// ── Layout helpers ───────────────────────────────────────────────────────────

/** localStorage key for the user-saved default Golden Layout configuration. */
const SAVED_LAYOUT_KEY = 'cc:gl-layout:default';

function convertLayout(frontendLayout: string): string {
  const map: Record<string, string> = {
    spring_layout: 'Spring',
    spectral_layout: 'Spectral',
    kamada_kawai_layout: 'Kamada_Kawai',
    circular_layout: 'Circular',
    spiral_layout: 'Spiral',
    random_layout: 'Random',
    shell_layout: 'Shell',
    sorted_square_layout: 'Sorted_Square',
  };
  return map[frontendLayout] ?? 'Spring';
}

function findFileByUrl(folder: RawFolder, url: string): RawFile | null {
  for (const f of folder.files) {
    if (f.url === url) return f;
  }
  for (const sub of folder.folders) {
    const found = findFileByUrl(sub, url);
    if (found) return found;
  }
  return null;
}

// ── LayoutContext class ──────────────────────────────────────────────────────

export class LayoutContext {
  public readonly appState: StateController;
  public readonly actions: AppActions;
  private _layoutManager: LayoutManager | null = null;

  // Reactive UI-only state shared by the docked panels.
  public panelState: ControlPanelState = {
    isOpen: true,
    activeTab: 'source',
    codeSourceMode: 'upload',
    repoUrl: '',
    currentTheme: 'forest',
    isLoading: false,
    statusMessage: 'Ready',
    progress: null,
    panelHeight: 380,
    graphSections: { layout: true, visual: false, theme: false },
    parseDepth: 2,
  };

  /** Files uploaded via the local file picker (not stored in Meiosis state). */
  public uploadedFiles: RawFile[] = [];

  /** Cached graph entries fetched from the backend cache endpoint. */
  public cachedGraphs: CachedEntry[] | null = null;

  /** GitHub auth status from the backend's /auth/github endpoint. */
  public githubAuthStatus: { source: string; authenticated: boolean; token_prefix?: string } | null = null;

  /** Graphbase availability, saved bookmarks, snapshots, and history. */
  public graphbaseAvailable = false;
  public graphbaseBookmarks: GraphbaseBookmark[] = [];
  public graphbaseSnapshots: GraphbaseSnapshotMeta[] = [];
  public graphbaseHistory: GraphbaseHistoryMeta[] = [];
  /** When true, every completed render appends an entry to the history collection. */
  public graphbaseTrackHistory = false;

  /** Dock panels that have been closed and can be restored. */
  public hiddenDockPanels: DockPanelId[] = [];

  // Streaming lifecycle refs
  private _cancelStream: (() => void) | null = null;
  private _streamingRenderer: StreamingGraphRenderer | null = null;

  // ── rad ────────────────────────────────────────────────────────────────────
  // The radial menu is mounted here rather than inside the renderer because
  // intents have to reach the state layer, and the renderer does not know
  // about it. Integration standard §5.1.
  private _rad: RadExtension | null = null;
  private _nodeViewState: NodeViewState = EMPTY_VIEW_STATE;
  private _radSelection = new Set<GraphNode>();
  private _lastPlotAction: (() => Promise<void> | void) | null = null;

  public readonly panelCallbacks: ControlPanelCallbacks;

  constructor(initialCell: ICell) {
    this.appState = new StateController(initialCell);
    this.actions = createActions(this.appState);
    this.panelCallbacks = this._buildCallbacks();
  }

  // ── Public helpers ─────────────────────────────────────────────────────────

  /** Shallow-merge updates into panelState then trigger a Mithril redraw. */
  public updatePanelState(updates: Partial<ControlPanelState>): void {
    this.panelState = { ...this.panelState, ...updates };
    m.redraw();
  }

  /** Attach the live Golden Layout manager for add/restore operations. */
  public attachLayoutManager(layoutManager: LayoutManager | null): void {
    this._layoutManager = layoutManager;
  }

  public hideDockPanel(panelId: DockPanelId): void {
    if (!this.hiddenDockPanels.includes(panelId)) {
      this.hiddenDockPanels = [...this.hiddenDockPanels, panelId];
      m.redraw();
    }
  }

  public showDockPanel(panelId: DockPanelId): void {
    if (this.hiddenDockPanels.includes(panelId)) {
      this.hiddenDockPanels = this.hiddenDockPanels.filter((id) => id !== panelId);
      m.redraw();
    }
  }

  /** Re-open a closed dock panel, or add it fresh if it isn't in the layout at all. */
  public restoreDockPanel(panelId: DockPanelId): void {
    if (!this._layoutManager) return;
    const def = PanelRegistry.get(panelId);
    if (!def) return;

    if (this._layoutManager.findFirstComponentItemById(panelId)) {
      this.showDockPanel(panelId);
      return;
    }

    this._layoutManager.newItemAtLocation(def.config, LayoutManager.defaultLocationSelectors);
    this.showDockPanel(panelId);
    this._layoutManager.updateRootSize(true);
  }

  /** Ids of every registered panel currently present in the live layout. */
  public openPanelIds(): DockPanelId[] {
    if (!this._layoutManager) return [];
    return PanelRegistry.all()
      .map((def) => def.id)
      .filter((id) => !!this._layoutManager!.findFirstComponentItemById(id));
  }

  /** Registered panels not currently in the layout — what the add-window menu offers. */
  public addablePanels() {
    const open = new Set(this.openPanelIds());
    return PanelRegistry.all().filter((def) => !open.has(def.id));
  }

  // ── Layout persistence ─────────────────────────────────────────────────────

  /** The saved layout if one exists and parses cleanly, else the built-in default. */
  public loadInitialLayoutConfig(): LayoutConfig {
    try {
      const raw = localStorage.getItem(SAVED_LAYOUT_KEY);
      if (raw) return JSON.parse(raw) as LayoutConfig;
    } catch {
      /* corrupt/old-format entry — fall through to built-in default */
    }
    return DEFAULT_LAYOUT_CONFIG;
  }

  /** Persist the live layout (panel arrangement + sizes) as the local default. */
  public saveLayoutAsDefault(): void {
    if (!this._layoutManager) return;
    try {
      localStorage.setItem(SAVED_LAYOUT_KEY, JSON.stringify(this._layoutManager.toConfig()));
      ToastManager.show('Layout saved as default');
    } catch {
      ToastManager.show('Could not save layout');
    }
  }

  /** Drop the saved default and reload the built-in layout. */
  public resetLayoutToBuiltinDefault(): void {
    localStorage.removeItem(SAVED_LAYOUT_KEY);
    this._layoutManager?.loadLayout(DEFAULT_LAYOUT_CONFIG);
    this.hiddenDockPanels = [];
    ToastManager.show('Layout reset to built-in default');
  }

  /** Build the ControlPanelContent object from the current cell state. */
  public getControlPanelContent(): ControlPanelContent {
    const s = this.appState.state;
    return {
      repoDirectory: s.repo.content,
      uploadedFiles: this.uploadedFiles,
      graphStyling: s.graphStyling,
      parserOptions: s.parserOptions,
      selectedRenderer: s.selectedRenderer,
      availableLanguages: s.availableLanguages ?? null,
      availableLexiconLanguages: s.availableLexiconLanguages ?? [],
      cachedGraphs: this.cachedGraphs,
    };
  }

  /** Cancel any in-flight SSE stream. */
  public cancel(): void {
    if (this._cancelStream) {
      this._cancelStream();
      this._cancelStream = null;
    }
    this.updatePanelState({ isLoading: false, statusMessage: 'Cancelled', progress: null });
  }

  /** Fetch and cache the GitHub auth status from the backend. */
  public async refreshGithubAuthStatus(): Promise<void> {
    try {
      const r = await fetch(this.appState.api.authGithub);
      if (r.ok) {
        this.githubAuthStatus = await r.json();
        m.redraw();
      }
    } catch { /* non-fatal */ }
  }

  /** Check graphbase availability and refresh the bookmark list. */
  public async refreshGraphbase(): Promise<void> {
    const dbBase = this.appState.api.db;
    this.graphbaseAvailable = await GraphbaseService.isAvailable(dbBase);
    if (this.graphbaseAvailable) {
      [this.graphbaseBookmarks, this.graphbaseSnapshots] = await Promise.all([
        GraphbaseService.listBookmarks(dbBase),
        GraphbaseService.listSnapshots(dbBase),
      ]);
      // Refresh history for the current URL if one is loaded
      if (this.panelState.repoUrl) {
        this.graphbaseHistory = await GraphbaseService.listHistory(dbBase, this.panelState.repoUrl);
      }
    } else {
      this.graphbaseBookmarks = [];
      this.graphbaseSnapshots = [];
      this.graphbaseHistory = [];
    }
    m.redraw();
  }

  /**
   * Save a named graphbase bookmark.
   * When called from the "promote from cache" flow, pass an explicit `url`
   * override; otherwise uses the current repo URL from panelState.
   */
  public async saveGraphbaseBookmark(name: string, urlOverride?: string): Promise<void> {
    const url = urlOverride ?? this.panelState.repoUrl;
    if (!name.trim() || !url) return;
    const opts = this.appState.state.parserOptions;
    const layout = this.appState.state.graphStyling.layout ?? 'compound_layout';
    const ok = await GraphbaseService.saveBookmark(
      this.appState.api.db,
      name.trim(),
      url,
      layout,
      this.panelState.parseDepth,
      opts.fileExtensions,
    );
    if (ok) {
      ToastManager.show(`Saved "${name.trim()}"`);
      await this.refreshGraphbase();
    } else {
      ToastManager.show('Could not save — is graphbase available?');
    }
  }

  /** Delete a named graphbase bookmark. */
  public async deleteGraphbaseBookmark(name: string): Promise<void> {
    const ok = await GraphbaseService.deleteBookmark(this.appState.api.db, name);
    if (ok) await this.refreshGraphbase();
  }

  /** Load a graphbase bookmark: stream the URL with the saved settings. */
  public loadGraphbaseBookmark(bookmark: GraphbaseBookmark): void {
    this.updatePanelState({ repoUrl: bookmark.url, codeSourceMode: 'repo' });
    this._startStreamFromUrl(bookmark.url);
    this.actions.repo.fetchRepository(bookmark.url)
      .then(() => m.redraw())
      .catch(() => { /* graph still renders */ });
  }

  /** Save the current rendered graph as a full snapshot (instant replay later). */
  public async saveGraphbaseSnapshot(name: string): Promise<void> {
    if (!name.trim()) return;
    const gd = this.appState.state.graphData as any;
    if (!gd?.graph?.nodes) {
      ToastManager.show('No graph loaded — render one first');
      return;
    }
    // Reconstruct flat node array from the gJGF {id: {metadata: {...}}} shape
    const nodes = Object.entries(gd.graph.nodes as Record<string, { metadata: Record<string, unknown> }>)
      .map(([id, val]) => ({ id, ...val.metadata }));
    const edges: Array<{ source: string; target: string }> = gd.graph.edges ?? [];
    const meta = {
      url: this.panelState.repoUrl || '',
      layout: this.appState.state.graphStyling.layout,
      nodeCount: nodes.length,
    };
    const ok = await GraphbaseService.saveSnapshot(
      this.appState.api.db, name.trim(), nodes, edges, meta,
    );
    if (ok) {
      ToastManager.show(`Snapshot "${name.trim()}" saved`);
      await this.refreshGraphbase();
    } else {
      ToastManager.show('Could not save snapshot');
    }
  }

  /** Replay a stored snapshot instantly — no re-streaming needed. */
  public async loadGraphbaseSnapshot(snapshotName: string): Promise<void> {
    const snap = await GraphbaseService.loadSnapshot(this.appState.api.db, snapshotName);
    if (!snap) { ToastManager.show('Snapshot not found'); return; }

    const styling = this.appState.state.graphStyling;
    this.updatePanelState({ isLoading: true, statusMessage: 'Loading snapshot…', progress: null });

    this._mountAndStream((renderer) => {
      renderer.setTotal(snap.nodes.length);
      // Feed stored nodes/edges synchronously — no network call
      for (const node of snap.nodes) renderer.addNode(node as any);
      for (const edge of snap.edges) renderer.addEdge(edge as any);
      renderer.finalize();
      this.updatePanelState({ isLoading: false, statusMessage: `Snapshot: ${snapshotName}`, progress: null });
      return () => {}; // no-op cancel
    }, `Loading "${snapshotName}"…`);

    // If the snapshot has a URL, also populate the file tree
    if (snap.meta?.url) {
      this.updatePanelState({ repoUrl: snap.meta.url, codeSourceMode: 'repo' });
      this.actions.repo.fetchRepository(snap.meta.url)
        .then(() => m.redraw())
        .catch(() => {});
    }
  }

  /** Delete a named snapshot. */
  public async deleteGraphbaseSnapshot(name: string): Promise<void> {
    const ok = await GraphbaseService.deleteSnapshot(this.appState.api.db, name);
    if (ok) await this.refreshGraphbase();
  }

  // ── History ──────────────────────────────────────────────────────────────

  /** Replay a specific history entry by url_hash + captured_at timestamp. */
  public async loadGraphbaseHistoryEntry(urlHash: string, capturedAt: number): Promise<void> {
    const entry = await GraphbaseService.getHistoryEntry(this.appState.api.db, urlHash, capturedAt);
    if (!entry) { ToastManager.show('History entry not found'); return; }

    this.updatePanelState({ isLoading: true, statusMessage: 'Replaying history…', progress: null });
    this._mountAndStream((renderer) => {
      renderer.setTotal(entry.nodes.length);
      for (const node of entry.nodes) renderer.addNode(node as any);
      for (const edge of entry.edges) renderer.addEdge(edge as any);
      renderer.finalize();
      const ts = new Date(capturedAt * 1000).toLocaleString();
      this.updatePanelState({ isLoading: false, statusMessage: `History: ${ts}`, progress: null });
      return () => {};
    }, 'Replaying history entry…');
  }

  /** Delete a history entry. */
  public async deleteGraphbaseHistoryEntry(urlHash: string, capturedAt: number): Promise<void> {
    const ok = await GraphbaseService.deleteHistoryEntry(this.appState.api.db, urlHash, capturedAt);
    if (ok) await this.refreshGraphbase();
  }

  /** Fetch and refresh the backend graph-cache list. */
  public async refreshCache(): Promise<void> {
    try {
      const resp = await fetch(`${this.appState.api.parse}/cache`);
      if (resp.ok) {
        const data = await resp.json();
        this.cachedGraphs = (data?.results?.entries as CachedEntry[]) ?? [];
        m.redraw();
      }
    } catch {
      /* non-fatal */
    }
  }

  // ── Private streaming helpers ──────────────────────────────────────────────

  private _buildGraphData(
    nodes: { id: string; [k: string]: unknown }[],
    edges: { source: string; target: string; [k: string]: unknown }[],
    meta: { nodeCount: number; edgeCount: number; layout: string },
  ): unknown {
    const graphNodes: Record<string, unknown> = {};
    for (const node of nodes) {
      const { id, ...rest } = node;
      graphNodes[id] = { metadata: rest };
    }
    return {
      graph: { nodes: graphNodes, edges },
      metadata: {
        nodeCount: meta.nodeCount,
        edgeCount: meta.edgeCount,
        layout: meta.layout,
        type: 'd3',
      },
    };
  }

  // ── rad integration ────────────────────────────────────────────────────────

  /**
   * `POST /parse/expand` answers in gJGF, where `nodes` is an id-keyed map of
   * `{metadata}` records — while the streaming path deals in flat node
   * objects. Both shapes are accepted rather than assumed, because the two
   * conventions already coexist in this codebase and a wrong guess here fails
   * silently as an empty expansion.
   */
  private _normaliseGraph(payload: unknown): { nodes: GraphNode[]; edges: GraphEdge[] } {
    const graph = (payload as { graph?: unknown })?.graph as
      | { nodes?: unknown; edges?: unknown }
      | undefined;
    if (!graph) return { nodes: [], edges: [] };

    const rawNodes = graph.nodes;
    let nodes: GraphNode[] = [];
    if (Array.isArray(rawNodes)) {
      nodes = rawNodes as GraphNode[];
    } else if (rawNodes && typeof rawNodes === 'object') {
      nodes = Object.entries(rawNodes as Record<string, { metadata?: Record<string, unknown> }>)
        .map(([id, v]) => ({ id, ...(v?.metadata ?? v) }) as GraphNode);
    }

    const rawEdges = Array.isArray(graph.edges) ? graph.edges : [];
    const edges = (rawEdges as Array<Record<string, unknown>>).map(
      (e) => ({ ...(e.metadata as object ?? {}), ...e }) as unknown as GraphEdge,
    );

    return { nodes, edges };
  }

  /** Facts the resolver needs that only this host can know. */
  private _radFacts(context: MenuContext) {
    const r = this._streamingRenderer;
    const id = context.targetIds[0];
    const node = id ? r?.getNodes().find((n) => n.id === id) : undefined;
    return {
      depth: node?.depth as number | undefined,
      kind: node?.kind as string | undefined,
      hasRenderedChildren: id ? (r?.childIdsOf(id).length ?? 0) > 0 : false,
      pinned: !!(id && this._nodeViewState[id]?.pinned),
      hasSource: !!node?.file,
      hasGroup: (node?.depth as number | undefined) !== undefined && (node!.depth as number) < 2,
      selectionCount: this._radSelection.size,
      anyHidden: anyHidden(this._nodeViewState),
      // The streaming renderer has no force simulation; positions come from
      // the backend layout. The verb stays in the ring, disabled, rather
      // than disappearing — a missing wedge would move every other index.
      physicsAvailable: false,
    };
  }

  /** Fold a view-state change in and repaint. §5.1: state, then projection. */
  private _setViewState(next: NodeViewState): void {
    this._nodeViewState = next;
    this._rad?.applyViewState();
  }

  private _radOps(): GraphOps {
    const renderer = () => this._streamingRenderer;
    return {
      hide: (ids) => this._setViewState(viewActions.hide(this._nodeViewState, ids)),
      showHidden: () => this._setViewState(viewActions.showAll(this._nodeViewState)),
      togglePin: (ids) => this._setViewState(viewActions.togglePin(this._nodeViewState, ids)),
      colour: (ids, token) =>
        this._setViewState(viewActions.colour(this._nodeViewState, ids, token)),

      remove: (ids) => {
        renderer()?.removeNodes(ids);
        this._setViewState(viewActions.forget(this._nodeViewState, ids));
      },

      /**
       * M2. Everything this needs already existed and was never joined:
       * the endpoint, PlotService.expandNode, and `parseDirectory` on the
       * live GraphState — whose docstring has said for months that it is
       * stored "so that subsequent expand-node calls can reuse the same
       * directory context".
       */
      expand: async (ids) => {
        const directory = this.appState.state.parseDirectory;
        const r = renderer();
        if (!directory || !r || !ids.length) return;

        this.updatePanelState({ statusMessage: `Expanding ${ids.length} node(s)…` });
        for (const id of ids) {
          const payload = await PlotService.expandNode(this.appState.api.parse, directory, id, 3);
          const { nodes, edges } = this._normaliseGraph(payload);
          // The subgraph includes the node that was expanded; mergeGraph
          // skips ids already on the canvas, so this is idempotent.
          r.mergeGraph(nodes, edges);
        }
        this._rad?.applyViewState();
        this.updatePanelState({ statusMessage: 'Expanded' });
      },

      collapse: (ids) => {
        const r = renderer();
        if (!r) return;
        // Breadth-first over the containment map, so collapsing a directory
        // takes its files and their symbols with it.
        const doomed: string[] = [];
        const queue = [...ids.flatMap((id) => r.childIdsOf(id))];
        while (queue.length) {
          const next = queue.shift()!;
          if (doomed.includes(next)) continue;
          doomed.push(next);
          queue.push(...r.childIdsOf(next));
        }
        r.removeNodes(doomed);
        this._setViewState(viewActions.forget(this._nodeViewState, doomed));
      },

      fit: () => renderer()?.fitView(),
      relayout: () => this._lastPlotAction?.(),
      spread: () => renderer()?.fitView(),
      cluster: () => renderer()?.fitView(),
      togglePhysics: () => {},

      selectNeighbors: (ids) => {
        const r = renderer();
        if (!r) return;
        const want = new Set<string>(ids);
        for (const e of r.getEdges()) {
          const s = String(e.source);
          const t = String(e.target);
          if (want.has(s)) want.add(t);
          else if (want.has(t)) want.add(s);
        }
        this._radSelection = new Set(r.getNodes().filter((n) => want.has(n.id)));
      },
      clearSelection: () => {
        this._radSelection = new Set();
      },
      focusGroup: (id) => {
        void id;
        renderer()?.fitView();
      },

      viewSource: (id) => {
        const node = renderer()?.getNodes().find((n) => n.id === id);
        if (node?.file) ToastManager.hint('rad-source', String(node.file));
      },
      showInfo: (id) => {
        const node = renderer()?.getNodes().find((n) => n.id === id);
        if (node) {
          ToastManager.hint('rad-info', `${node.label ?? node.id} · ${node.kind ?? 'node'}`);
        }
      },
    };
  }

  /**
   * Mount rad against the streaming renderer.
   *
   * Called after `finalize()` — the graph has to exist before a menu can
   * resolve anything about it. This one call is the whole of M1: the rich
   * interaction layer was never missing, it was attached to a renderer no
   * code-map path mounts.
   */
  private _mountRad(renderer: StreamingGraphRenderer): void {
    this._rad?.destroy();
    this._radSelection = new Set();
    this._nodeViewState = EMPTY_VIEW_STATE;

    const rad = new RadExtension({
      ops: this._radOps(),
      viewState: () => this._nodeViewState,
      facts: (context) => this._radFacts(context),
      onError: (verb, err) => {
        this.updatePanelState({ statusMessage: `${verb} failed: ${String(err)}` });
      },
    });

    rad.initialize(renderer.buildExtensionContext(this._radSelection, () => m.redraw()));
    rad.apply();
    this._rad = rad;
  }

  /** Core SSE render loop (shared by all stream starters). */
  private _mountAndStream(
    startFn: (renderer: StreamingGraphRenderer) => () => void,
    statusMsg: string,
  ): void {
    if (this._cancelStream) {
      this._cancelStream();
      this._cancelStream = null;
    }
    this._streamingRenderer = null;

    const styling = this.appState.state.graphStyling;

    this.updatePanelState({
      isLoading: true,
      statusMessage: statusMsg,
      progress: { loaded: 0, total: 0, phase: 'parsing' },
    });

    const canvasVnode = m('div.graph_content.graphRenderer', {
      key: `stream-${Date.now()}`,
      oncreate: (vnode: m.VnodeDOM) => {
        const el = vnode.dom as HTMLElement;
        el.style.height = '100%';
        el.style.width = '100%';
        this._streamingRenderer = new StreamingGraphRenderer(el, styling);
        this._cancelStream = startFn(this._streamingRenderer);
      },
    });

    this.appState.updatePlotFrame([canvasVnode]);
  }

  private _updateProgress(progress: LoadingProgress | null): void {
    this.panelState.progress = progress;
    m.redraw();
  }

  /** Stream a pre-fetched Directory via /parse/stream. */
  private _startStream(directory: Directory, statusMsg: string): void {
    const opts = this.appState.state.parserOptions;
    const layout = convertLayout(this.appState.state.graphStyling.layout);
    const exts = opts.fileExtensions.length > 0 ? opts.fileExtensions : null;
    const depth = this.panelState.parseDepth;

    const accNodes: { id: string; [k: string]: unknown }[] = [];
    const accEdges: { source: string; target: string; [k: string]: unknown }[] = [];
    let nodeCount = 0;

    this._mountAndStream((renderer) =>
      PlotService.streamUnified(
        this.appState.api.parse,
        directory,
        { depth, extensions: exts, layout, annotateLexicon: opts.annotateLexicon },
        {
          onMeta: (meta) => {
            renderer.setTotal(meta.nodeCount);
            this._updateProgress({ loaded: 0, total: meta.nodeCount, phase: 'streaming' });
          },
          onNode: (node) => {
            nodeCount++;
            accNodes.push(node as any);
            if (nodeCount % 5 === 0)
              this._updateProgress({
                loaded: nodeCount,
                total: this.panelState.progress?.total ?? 0,
                phase: 'streaming',
              });
            renderer.addNode(node as any);
          },
          onEdge: (edge) => {
            accEdges.push(edge as any);
            renderer.addEdge(edge as any);
          },
          onDone: (elapsed_ms, from_cache) => {
            this._cancelStream = null;
            renderer.finalize();
            // Keep the renderer: rad mounts against it, and its ops need a
            // live handle for the whole session, not just the stream.
            this._mountRad(renderer);
            this.appState.update({
              parseDirectory: directory,
              graphData: this._buildGraphData(accNodes, accEdges, {
                nodeCount,
                edgeCount: accEdges.length,
                layout,
              }) as any,
            });
            if (this.appState.state.selectedRenderer !== 'd3') {
              this.actions.plot.createGraphVnode();
            }
            const msg = from_cache
              ? `Served from cache (${nodeCount} nodes)`
              : `Done in ${elapsed_ms}ms (${nodeCount} nodes)`;
            this.updatePanelState({ isLoading: false, statusMessage: msg, progress: null });
            ToastManager.hint('first-graph', 'Scroll to zoom, drag to pan, hover nodes for details');
            this.refreshCache();
            if (this.graphbaseAvailable && this.graphbaseTrackHistory && accNodes.length > 0) {
              const histUrl = this.panelState.repoUrl || 'local';
              GraphbaseService.appendHistory(
                this.appState.api.db, histUrl,
                accNodes as any, accEdges as any, { layout, nodeCount },
              ).then(() => this.refreshGraphbase());
            }
          },
          onError: (msg) => {
            this._cancelStream = null;
            this._streamingRenderer = null;
            this.updatePanelState({ isLoading: false, statusMessage: `Error: ${msg}`, progress: null });
          },
        },
      ),
      statusMsg,
    );
  }

  /** Stream directly from a GitHub URL via /parse/stream-url. */
  private _startStreamFromUrl(githubUrl: string): void {
    const opts = this.appState.state.parserOptions;
    const layout = convertLayout(this.appState.state.graphStyling.layout);
    const exts = opts.fileExtensions.length > 0 ? opts.fileExtensions : null;
    const depth = this.panelState.parseDepth;

    const accNodes: { id: string; [k: string]: unknown }[] = [];
    const accEdges: { source: string; target: string; [k: string]: unknown }[] = [];
    let nodeCount = 0;

    this._mountAndStream((renderer) =>
      PlotService.streamFromUrl(
        this.appState.api.parse,
        githubUrl,
        { depth, extensions: exts, layout, annotateLexicon: opts.annotateLexicon },
        {
          onFetching: (msg) => this.updatePanelState({ statusMessage: msg }),
          onMeta: (meta) => {
            renderer.setTotal(meta.nodeCount);
            this._updateProgress({ loaded: 0, total: meta.nodeCount, phase: 'streaming' });
          },
          onNode: (node) => {
            nodeCount++;
            accNodes.push(node as any);
            if (nodeCount % 5 === 0)
              this._updateProgress({
                loaded: nodeCount,
                total: this.panelState.progress?.total ?? 0,
                phase: 'streaming',
              });
            renderer.addNode(node as any);
          },
          onEdge: (edge) => {
            accEdges.push(edge as any);
            renderer.addEdge(edge as any);
          },
          onDone: (elapsed_ms, from_cache) => {
            this._cancelStream = null;
            renderer.finalize();
            // Keep the renderer: rad mounts against it, and its ops need a
            // live handle for the whole session, not just the stream.
            this._mountRad(renderer);
            this.appState.update({
              graphData: this._buildGraphData(accNodes, accEdges, {
                nodeCount,
                edgeCount: accEdges.length,
                layout,
              }) as any,
            });
            if (this.appState.state.selectedRenderer !== 'd3') {
              this.actions.plot.createGraphVnode();
            }
            const msg = from_cache
              ? `Served from cache (${nodeCount} nodes)`
              : `Done in ${elapsed_ms}ms (${nodeCount} nodes)`;
            this.updatePanelState({ isLoading: false, statusMessage: msg, progress: null });
            ToastManager.hint('first-graph', 'Scroll to zoom, drag to pan, hover nodes for details');
            this.refreshCache();
            if (this.graphbaseAvailable && this.graphbaseTrackHistory && accNodes.length > 0) {
              GraphbaseService.appendHistory(
                this.appState.api.db, githubUrl,
                accNodes as any, accEdges as any, { layout, nodeCount },
              ).then(() => this.refreshGraphbase());
            }
          },
          onError: (msg) => {
            this._cancelStream = null;
            this._streamingRenderer = null;
            this.updatePanelState({ isLoading: false, statusMessage: `Error: ${msg}`, progress: null });
          },
        },
      ),
      'Connecting to GitHub\u2026',
    );
  }

  // ── Callback builder ───────────────────────────────────────────────────────

  private _buildCallbacks(): ControlPanelCallbacks {
    return {
      onDemo: async () => {
        this.updatePanelState({ isLoading: true, statusMessage: 'Loading demo...' });
        this._lastPlotAction = async () => { await this.actions.plot.loadDemo(); };
        try {
          await this._lastPlotAction();
          this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: 'Error loading demo' });
        }
      },

      onLoadLexicon: async (language: string) => {
        this.updatePanelState({ isLoading: true, statusMessage: `Loading ${language} lexicon...` });
        this._lastPlotAction = async () => { await this.actions.plot.loadLexicon(language); };
        try {
          await this._lastPlotAction();
          this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: `Error loading ${language} lexicon` });
        }
      },

      onRepoSubmit: (url: string) => {
        this.panelState.repoUrl = url;
        this._lastPlotAction = () => { this.panelCallbacks.onRepoSubmit(url); };
        this._startStreamFromUrl(url);
        this.actions.repo.fetchRepository(url)
          .then(() => {
            const dir = this.appState.repo.content;
            if (dir?.is_partial)
              ToastManager.hint('stub-folders', 'Large repo: click a folder ▶ to expand it, or use "Expand All"');
            m.redraw();
          })
          .catch(() => { /* sidebar still works */ });
      },

      onRepoFileClick: async (url: string) => {
        const repoContent = this.appState.repo.content;
        if (!repoContent) return;
        const file = findFileByUrl(repoContent.root, url);
        if (!file) return;
        let rawContent = file.raw;
        if (!rawContent) {
          try {
            const resp = await fetch(url);
            rawContent = resp.ok ? await resp.text() : '';
          } catch { rawContent = ''; }
        }
        const singleFileDir = new Directory(
          repoContent.info,
          1,
          new RawFolder('', 0, [new RawFile(file.name, file.size, rawContent, url)]),
        );
        this._lastPlotAction = () => { this.panelCallbacks.onRepoFileClick(url); };
        this._startStream(singleFileDir, `Plotting ${file.name}\u2026`);
      },

      onPlotWholeRepo: () => {
        if (this.panelState.codeSourceMode === 'repo' && this.panelState.repoUrl) {
          this._lastPlotAction = () => { this.panelCallbacks.onPlotWholeRepo(); };
          this._startStreamFromUrl(this.panelState.repoUrl);
          return;
        }
        const repoContent = this.appState.repo.content;
        if (!repoContent || repoContent.size === 0) return;
        this._lastPlotAction = () => { this.panelCallbacks.onPlotWholeRepo(); };
        this._startStream(repoContent, 'Streaming graph\u2026');
      },

      onFileUpload: (files: FileList) => {
        this.updatePanelState({ isLoading: true, statusMessage: 'Processing files...' });
        const newFiles: RawFile[] = [];
        let processed = 0;
        Array.from(files).forEach((file) => {
          if (this.uploadedFiles.some((f) => f.name === file.name)) {
            processed++;
            if (processed === files.length)
              this.updatePanelState({ isLoading: false, statusMessage: `${newFiles.length} new file(s) added` });
            return;
          }
          const reader = new FileReader();
          reader.onload = (e) => {
            const content = e.target?.result as string;
            const newFile = new RawFile(file.name, file.size, content, file.webkitRelativePath || file.name);
            newFiles.push(newFile);
            this.uploadedFiles.push(newFile);
            processed++;
            if (processed === files.length) {
              this.appState.update({
                local: {
                  content: new Directory(
                    new RepoInfo(),
                    this.uploadedFiles.length,
                    new RawFolder('uploads', 0, this.uploadedFiles),
                  ),
                },
              });
              this.updatePanelState({ isLoading: false, statusMessage: `${newFiles.length} file(s) added` });
            }
          };
          reader.readAsText(file);
        });
      },

      onUploadedFileClick: async (file: RawFile) => {
        this.updatePanelState({ isLoading: true, statusMessage: 'Plotting file...' });
        this._lastPlotAction = async () => { await this.actions.plot.plotUploadedFile(file); };
        try {
          await this._lastPlotAction();
          this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: 'Error plotting file' });
        }
      },

      onPlotAllUploads: async () => {
        if (this.uploadedFiles.length > 0) {
          this.updatePanelState({ isLoading: true, statusMessage: 'Plotting all files...' });
          this._lastPlotAction = async () => {
            if (this.uploadedFiles.length > 0)
              await this.actions.plot.plotUploadedFile(this.uploadedFiles[0]);
          };
          try {
            await this._lastPlotAction();
            this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
          } catch {
            this.updatePanelState({ isLoading: false, statusMessage: 'Error plotting files' });
          }
        }
      },

      onThemeChange: (theme: string) => {
        if (this.appState.state.selectedRenderer === 'notebook' && this.appState.state.graphData)
          this.actions.plot.createGraphVnode();
      },

      onGraphStylingChange: async (options) => {
        const current = this.appState.state;
        const oldLayout = current.graphStyling.layout;
        const oldPhysics = current.graphStyling.enablePhysics;
        this.appState.update({ graphStyling: { ...current.graphStyling, ...options } });
        if (this._streamingRenderer) {
          this._streamingRenderer.updateStyling(options);
        }
        if (options.layout && options.layout !== oldLayout && this._lastPlotAction) {
          this.updatePanelState({ isLoading: true, statusMessage: 'Applying new layout...' });
          try {
            await this._lastPlotAction();
            this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
          } catch {
            this.updatePanelState({ isLoading: false, statusMessage: 'Error applying layout' });
          }
          return;
        }
        if (options.enablePhysics !== undefined && options.enablePhysics !== oldPhysics && this.appState.state.graphData) {
          this.actions.plot.createGraphVnode();
          return;
        }
        if (this.appState.state.graphData || this.appState.state.selectedRenderer === 'system')
          this.actions.plot.createGraphVnode();
      },

      onParserOptionsChange: (options) => {
        const current = this.appState.state;
        this.appState.update({ parserOptions: { ...current.parserOptions, ...options } });
      },

      onFolderExpand: async (path: string) => {
        const content = this.appState.repo.content;
        if (!content?.is_partial) return;
        this.updatePanelState({ isLoading: true, statusMessage: `Loading ${path}...` });
        try {
          await this.actions.repo.expandPath(this.panelState.repoUrl, path);
          this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: `Error expanding ${path}` });
        }
      },

      onExpandAll: async () => {
        const content = this.appState.repo.content;
        if (!content?.is_partial) return;
        this.updatePanelState({ isLoading: true, statusMessage: 'Expanding all folders...' });
        try {
          await this.actions.repo.expandAll(this.panelState.repoUrl);
          this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: 'Error expanding tree' });
        }
      },

      onLoadFromCache: async (key: string) => {
        const entry = this.cachedGraphs?.find((e) => e.key === key);
        if (!entry) return;
        // Streaming from the URL will hit the backend cache and replay instantly.
        this.updatePanelState({ repoUrl: entry.url, codeSourceMode: 'repo' });
        this._startStreamFromUrl(entry.url);
        // fetchRepository populates state.repo.content, which the Files panel
        // reads — without this the recalled graph renders but the tree stays empty.
        this.actions.repo.fetchRepository(entry.url)
          .then(() => m.redraw())
          .catch(() => { /* graph still renders from the stream above */ });
      },

      onClearRepo: () => {
        this.appState.clearRepoData();
        this.uploadedFiles = [];
        this.updatePanelState({ repoUrl: '', codeSourceMode: 'repo' });
      },

      onEvictCache: async (key: string) => {
        try {
          await fetch(`${this.appState.api.parse}/cache/${key}`, { method: 'DELETE' });
          await this.refreshCache();
        } catch { /* non-fatal */ }
      },

      onCancel: () => { this.cancel(); },

      onRendererChange: (renderer) => {
        this.appState.update({ selectedRenderer: renderer });
        if (renderer === 'system' || this.appState.state.graphData) {
          this.updatePanelState({ statusMessage: `Switching to ${renderer} renderer...` });
          this.actions.plot.createGraphVnode();
          this.updatePanelState({ statusMessage: 'Ready' });
        } else {
          this.updatePanelState({ statusMessage: `Renderer: ${renderer}. Load source to apply.` });
        }
      },
    };
  }
}
