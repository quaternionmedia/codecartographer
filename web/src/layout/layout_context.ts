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
import type { ContentItem, LayoutConfig, Stack } from 'golden-layout';

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
import { SHOW_OPEN_EVENT, StreamingGraphRenderer } from '../features/graph/services/streaming_renderer';
import { ToastManager } from '../components/codecarto/help/toast';
import { infoLine } from '../features/graph/services/node_info';
import type { BundledExample } from '../features/examples/examples';
import { notesTail } from '../features/graph/services/parse_notes';
import { plotTarget } from '../features/repository/plot_target';
import { DockPanelId, PanelRegistry } from './panel_registry';
import { DEFAULT_LAYOUT_CONFIG } from './default_layout';
import { readSavedLayout } from './saved_layout';
import { stackForNewPanel, stackOfTabClicked } from './new_panel_stack';
import { GraphbaseService, GraphbaseBookmark, GraphbaseSnapshotMeta, GraphbaseHistoryMeta } from '../services/graphbase_service';
import { RadExtension } from '../features/graph/rad/host/rad_extension';
import { GraphSurface } from '../features/graph/services/graph_surface';
import { LegendExtension } from '../features/graph/extensions';
import { viewActions, EMPTY_VIEW_STATE, anyHidden } from '../features/graph/rad/host/view_state';
import type { NodeViewState } from '../features/graph/rad/host/view_state';
import type { GraphOps } from '../features/graph/rad/host/graph_intents';
import type { MenuContext } from '../features/graph/rad/core/types';
import { DEEPEST_DEPTH } from '../features/graph/rad/host/resolve';
import type { GraphNode, GraphEdge } from '../features/graph/services/graph_types';
import { backendLayoutName } from '../features/graph/services/layout_names';
import { formatShow, fromNode, parseShow, sameShow } from '../features/show/show_address';
import type { ShowAddress } from '../features/show/show_address';
import { SystemDefinitionRegistry } from '../features/graph/services/system_core';
import { DerivedSystemDefinition } from '../features/graph/services/derived_system';

export type { DockPanelId } from './panel_registry';

// ── Layout helpers ───────────────────────────────────────────────────────────

/** localStorage key for the user-saved default Golden Layout configuration. */
const SAVED_LAYOUT_KEY = 'cc:gl-layout:default';

// The menu's registry name, as the backend spells it. One rule in
// `layout_names.ts`; this used to be a second private table that fell back to
// 'Spring' for any name it did not list, including `compound_layout`.
const convertLayout = backendLayoutName;

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
    repoUrl: '',
    currentTheme: 'forest',
    isLoading: false,
    statusMessage: 'Ready',
    progress: null,
    graphSections: { layout: true, visual: false, theme: false },
    parseDepth: 2,
    parseOptionsOpen: false,
  };

  /** Files uploaded via the local file picker (not stored in Meiosis state). */
  public uploadedFiles: RawFile[] = [];

  /** Cached graph entries fetched from the backend cache endpoint. */
  public cachedGraphs: CachedEntry[] | null = null;
  public bundledExamples: BundledExample[] = [];

  /** GitHub auth status from the backend's /auth/github endpoint. */
  public githubAuthStatus: { source: string; authenticated: boolean; token_prefix?: string } | null = null;

  /** Graphbase availability, saved bookmarks, snapshots, and history. */
  public graphbaseAvailable = false;
  public graphbaseBookmarks: GraphbaseBookmark[] = [];
  public graphbaseSnapshots: GraphbaseSnapshotMeta[] = [];
  public graphbaseHistory: GraphbaseHistoryMeta[] = [];
  /** When true, every completed render appends an entry to the history collection. */
  public graphbaseTrackHistory = false;

  // Streaming lifecycle refs
  private _cancelStream: (() => void) | null = null;
  private _streamingRenderer: StreamingGraphRenderer | null = null;

  // ── rad ────────────────────────────────────────────────────────────────────
  // The radial menu is mounted here rather than inside the renderer because
  // intents have to reach the state layer, and the renderer does not know
  // about it. Integration standard §5.1.
  private _rad: RadExtension | null = null;
  private _legend: LegendExtension | null = null;
  private _nodeViewState: NodeViewState = EMPTY_VIEW_STATE;
  private _radSelection = new Set<GraphNode>();
  /** Set by the `relayout` verb so the remount knows to keep view state. */
  private _radRelayoutPending = false;
  private _lastPlotAction: (() => Promise<void> | void) | null = null;

  public readonly panelCallbacks: ControlPanelCallbacks;

  constructor(initialCell: ICell) {
    this.appState = new StateController(initialCell);
    this.actions = createActions(this.appState);
    this.panelCallbacks = this._buildCallbacks();

    // **ONE PLACE THE MENU AND THE KEY ATTACH, WHICHEVER PATH DREW.** A repo
    // plot builds its renderer here; Load Demo and an uploaded file go through
    // the registry, which builds one inside a Mithril vnode this object never
    // sees. Both announce the finished canvas, so both get the same fittings.
    GraphSurface.subscribe((renderer) => {
      this._streamingRenderer = renderer;
      this._mountRad(renderer);
    });

    // A showgraph is a place to move through: a node double-clicked on the
    // canvas opens its own showgraph, and Back and Forward walk the drawings.
    if (typeof window !== 'undefined') {
      window.addEventListener(SHOW_OPEN_EVENT, (event) => {
        const address = fromNode((event as CustomEvent).detail);
        if (address) void this.openShow(address);
      });
      window.addEventListener('popstate', () => {
        const address = parseShow(window.location.search);
        if (address) void this.openShow(address, 'keep');
      });
    }
  }

  // ── Public helpers ─────────────────────────────────────────────────────────

  /** Shallow-merge updates into panelState then trigger a Mithril redraw. */
  /**
   * Run a plot and remember it as the one a layout change re-runs.
   *
   * **A LAYOUT CHOICE IS A CHOICE ABOUT THE GRAPH ON THE CANVAS**, whichever
   * seam drew it. `onGraphStylingChange` re-runs `_lastPlotAction` when the
   * layout changes, and rad's `relayout` verb does the same -- but only the
   * code-map paths ever set it. An estate graph drawn from the Topology,
   * Capabilities or Overview panel was never remembered, so choosing a
   * different layout in Graph Settings changed the setting and nothing else:
   * the selection was kept and not applied until somebody pressed draw again,
   * which nobody guesses. Every panel that draws goes through this.
   */
  public async plotWith<T>(action: () => Promise<T>): Promise<T> {
    this._lastPlotAction = async () => { await action(); };
    return action();
  }

  public updatePanelState(updates: Partial<ControlPanelState>): void {
    this.panelState = { ...this.panelState, ...updates };
    m.redraw();
  }

  /** Attach the live Golden Layout manager that panels are opened in. */
  public attachLayoutManager(layoutManager: LayoutManager | null): void {
    this._layoutManager = layoutManager;
  }

  /**
   * Bring a panel's tab to the front of its stack.
   *
   * A panel that draws calls this with 'graph' once it has drawn, so the
   * drawing is in view even when the reader has stacked the panel with the
   * canvas. A panel that is not in a stack has nothing to focus and is left.
   */
  public focusDockPanel(panelId: DockPanelId): void {
    const item = this._layoutManager?.findFirstComponentItemById(panelId);
    if (!item) return;
    // `ComponentItem.focus()` marks the item focused and leaves the stack's
    // active tab alone -- the first version called it and the graph stayed
    // behind. The stack is what shows one tab and hides the rest.
    const stack = item.parent as { setActiveComponentItem?: (i: typeof item, focus: boolean) => void } | null;
    if (stack && typeof stack.setActiveComponentItem === 'function') {
      stack.setActiveComponentItem(item, true);
    }
  }

  /**
   * Open a panel: bring it to the front when it is in the layout, add it when
   * it is not. The one way a window opens: the "+" menu, an Estate row, View ▸
   * Compare and a source that loads data for a panel all call this.
   *
   * An added panel joins the stack whose tab the reader last clicked, or else
   * the stack holding the most panels, and not the Graph panel's own stack
   * while another stack exists, so the canvas stays in view.
   */
  public openPanel(panelId: DockPanelId): void {
    const layout = this._layoutManager;
    if (!layout) return;
    const def = PanelRegistry.get(panelId);
    if (!def) return;

    if (layout.findFirstComponentItemById(panelId)) {
      this.focusDockPanel(panelId);
      return;
    }

    // Where: `new_panel_stack.ts`, which says why it is not Golden Layout's
    // focus. Null leaves it to Golden Layout's own placement.
    const canvas = layout.findFirstComponentItemById('graph')?.parent ?? null;
    const stack = stackForNewPanel<ContentItem>(layout.rootItem, canvas, this._tabStackClicked) as Stack | null;
    if (stack) stack.newItem(def.config);
    else layout.newItemAtLocation(def.config, LayoutManager.defaultLocationSelectors);
    layout.updateRootSize(true);
  }

  /** The `.lm_stack` element of the tab the reader last clicked; see `noteClick`. */
  private _tabStackClicked: unknown = null;

  /**
   * Hear a click in the dock, before Golden Layout does. A click on a tab
   * records that tab's stack, which is where `openPanel` adds a window next;
   * any other click records nothing.
   */
  public noteClick(target: EventTarget | null): void {
    const clicked = stackOfTabClicked(target);
    if (clicked) this._tabStackClicked = clicked;
  }

  /** Ids of every registered panel currently present in the live layout. */
  public openPanelIds(): DockPanelId[] {
    if (!this._layoutManager) return [];
    return PanelRegistry.all()
      .map((def) => def.id)
      .filter((id) => !!this._layoutManager!.findFirstComponentItemById(id));
  }

  /** Registered panels not in the layout, closed ones included — what the "+" menu offers. */
  public addablePanels() {
    const open = new Set(this.openPanelIds());
    return PanelRegistry.all().filter((def) => !open.has(def.id));
  }

  // ── Layout persistence ─────────────────────────────────────────────────────

  /**
   * The saved layout if it can be loaded, else the built-in default.
   *
   * A saved layout that names a window this version does not register is
   * dropped here, before Golden Layout reads it: Golden Layout throws on an
   * unregistered component type, and the page would boot with no windows.
   */
  public loadInitialLayoutConfig(): LayoutConfig {
    let raw: string | null = null;
    try {
      raw = localStorage.getItem(SAVED_LAYOUT_KEY);
    } catch {
      /* storage blocked: nothing saved to read */
    }
    const saved = readSavedLayout(raw, PanelRegistry.all().map((def) => def.id));
    if (saved.kind === 'usable') {
      if (saved.renamed.length) this._keepRenamedLayout(saved.config, saved.renamed);
      return saved.config as LayoutConfig;
    }
    if (saved.kind === 'unusable') this.dropSavedLayout(saved.why);
    return DEFAULT_LAYOUT_CONFIG;
  }

  /** Save a layout whose merged windows were renamed, and say so once. */
  private _keepRenamedLayout(config: object, renamed: string[]): void {
    try {
      localStorage.setItem(SAVED_LAYOUT_KEY, JSON.stringify(config));
    } catch {
      /* storage blocked: the renamed layout still loads this time */
    }
    const names = renamed.map((id) => `'${id}'`).join(', ');
    ToastManager.show(`The saved layout's ${names} window(s) are the Open window in this version.`, 8_000);
  }

  /** Forget the saved layout, and say why the default is showing instead. */
  public dropSavedLayout(why: string): void {
    try {
      localStorage.removeItem(SAVED_LAYOUT_KEY);
    } catch {
      /* storage blocked: there is nothing to remove */
    }
    ToastManager.show(`The saved layout was not loaded: ${why}. Showing the default.`, 8_000);
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
      bundledExamples: this.bundledExamples,
      graphbaseAvailable: this.graphbaseAvailable,
      savedUrls: this.graphbaseBookmarks.map((b) => b.url),
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
    this.updatePanelState({ repoUrl: bookmark.url });
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
      this.updatePanelState({ repoUrl: snap.meta.url });
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

  /** What examples this checkout bundles, for the project selector. */
  // ── The showgraphs ────────────────────────────────────────────────────────

  /**
   * Open a showgraph: the index, a family, or one of a project's three views.
   *
   * **ONE WAY IN, FROM EVERYWHERE.** The Show panel's rows, a `?show=` address
   * the page was opened at, and a node's own `show` attribute all call this, so
   * the address in the location bar is always the graph on the canvas.
   *
   * The estate view is the show seam's graph. The code view is the parse of
   * the project's default branch on the host at file depth -- the same stream
   * the Open panel starts, so it draws, caches and cancels like any parse. The
   * system view is the derived system monitor for that repository. A view the
   * server says cannot be drawn is a problem the panel shows, never a
   * different view drawn in its place.
   */
  /**
   * Open a showgraph, and write its address.
   *
   * `history` says what the location bar does: `push` a new entry, so Back
   * returns to the drawing before (a click in the panel or on the canvas);
   * `replace` the entry (an address the page opened with, or the default);
   * or `keep` it (Back and Forward, which have moved it already).
   *
   * **ONE REQUEST PER DRAWING.** At boot the page's address and the Show
   * panel's default both asked for the index, and a corpus measured twice
   * at once took more than twice as long. Asked again for the drawing it is
   * already opening, this returns that one.
   */
  public openShow(address: ShowAddress, history: 'push' | 'replace' | 'keep' = 'push'): Promise<void> {
    if (this._opening && sameShow(this._opening.address, address)) return this._opening.done;
    const done = this._openShow(address, history).finally(() => {
      if (this._opening?.done === done) this._opening = null;
    });
    this._opening = { address, done };
    return done;
  }

  private _opening: { address: ShowAddress; done: Promise<void> } | null = null;

  private async _openShow(address: ShowAddress, history: 'push' | 'replace' | 'keep'): Promise<void> {
    // Before the panel mounts: a Show panel opening onto nothing drawn draws
    // every family, and this address is what it is about to draw instead.
    this.appState.update({ showAddress: address, showProblem: null });
    this._setShowAddress(address, history);
    this.openPanel('show-panel');

    if (address.kind === 'project') {
      await this.actions.plot.loadShowViews(address.name);
    } else {
      this.appState.update({ showViews: null });
    }

    if (address.view === 'estate') {
      this._leaveSystemRenderer();
      this._compoundLayout();
      const drawn = await this.plotWith(() => this.actions.plot.drawShow(address));
      if (drawn) this.focusDockPanel('graph');
      return;
    }

    const views = this.appState.state.showViews;
    const view = views ? views[address.view] : null;
    if (!view || !view.available) {
      this.appState.update({
        showProblem: {
          kind: 'unreadable',
          problem: view?.problem ?? `the ${address.view} view of ${address.name} could not be asked for`,
          remedy: view?.remedy ?? '',
          where: `${this.appState.api.show}/project/${address.name}/views`,
        },
      });
      m.redraw();
      return;
    }

    if (address.view === 'code' && view.url) {
      this._leaveSystemRenderer();
      this._compoundLayout();
      // The coarse map: files, not symbols. The depth is read when the stream
      // starts, so the reader's own setting is put back straight after.
      const depth = this.panelState.parseDepth;
      this.panelState.parseDepth = view.depth ?? 1;
      const url = view.url;
      await this.plotWith(async () => this._startStreamFromUrl(url));
      this.panelState.parseDepth = depth;
    } else if (address.view === 'system') {
      if (!SystemDefinitionRegistry.get(address.name)) {
        SystemDefinitionRegistry.register(new DerivedSystemDefinition(address.name));
      }
      const styling = this.appState.state.graphStyling;
      this.appState.update({
        selectedRenderer: 'system',
        graphStyling: { ...styling, systemId: address.name },
      });
      // The frame is replaced in state; nothing repaints it until asked.
      this.actions.plot.createGraphVnode();
      m.redraw();
    }
    this.focusDockPanel('graph');
  }

  /** Open whatever showgraph the page's own address names, if it names one. */
  public async openShowFromLocation(): Promise<void> {
    const address = parseShow(window.location.search);
    if (address) await this.openShow(address, 'replace');
  }

  /** The location bar says which showgraph is drawn, without a new history entry. */
  private _setShowAddress(address: ShowAddress, how: 'push' | 'replace' | 'keep'): void {
    if (how === 'keep') return;
    const search = formatShow(address);
    try {
      // The same drawing asked for twice is one entry, not two.
      if (how === 'push' && window.location.search !== search) {
        window.history.pushState(null, '', `${window.location.pathname}${search}`);
      } else {
        window.history.replaceState(null, '', `${window.location.pathname}${search}`);
      }
    } catch {
      // A page that cannot rewrite its address still draws.
    }
  }

  /**
   * A showgraph is containment all the way down -- a family holds its
   * subfamilies, a subfamily its members, a folder its files -- so it opens in
   * the compound layout, which gathers each group around what holds it. Under
   * a layout that does not, two subfamilies whose members interleave draw two
   * outlines over one another. The reader's next choice of layout still
   * applies, as it does to any drawing.
   */
  private _compoundLayout(): void {
    const styling = this.appState.state.graphStyling;
    if (styling.layout !== 'compound_layout') {
      this.appState.update({ graphStyling: { ...styling, layout: 'compound_layout' } });
    }
  }

  /** A showgraph's estate and code views draw on the D3 canvas, not the system monitor. */
  private _leaveSystemRenderer(): void {
    if (this.appState.state.selectedRenderer === 'system') {
      this.appState.update({ selectedRenderer: 'd3' });
    }
  }

  public async refreshExamples(): Promise<void> {
    try {
      const resp = await fetch(`${this.appState.api.repoReader}/examples`);
      if (resp.ok) {
        const data = await resp.json();
        this.bundledExamples = (data?.results?.examples as BundledExample[]) ?? [];
        m.redraw();
      }
    } catch {
      /* non-fatal: the GitHub examples are still offered */
    }
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
      // Asked of the renderer that opens it, so offering and opening read one graph.
      hasSource: !!(id && r?.sourceTargetOf(id)),
      hasGroup: (node?.depth as number | undefined) !== undefined && (node!.depth as number) < 2,
      hasConstruct: typeof node?.construct === 'string',
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

  /**
   * Swap the selection's contents without swapping the Set.
   *
   * `ExtensionContext.selectedNodes` holds a reference captured at mount, so
   * assigning a fresh Set to the field leaves the extension reading the old
   * one. Mutating in place is what keeps the two views of the selection the
   * same object.
   */
  private _replaceSelection(nodes: GraphNode[]): void {
    this._radSelection.clear();
    for (const n of nodes) this._radSelection.add(n);
  }

  /**
   * The nodes on the canvas now, whichever panel or parse drew them: the
   * graph of record first, complete by the time it is set, and the renderer's
   * own when nothing is recorded.
   */
  public canvasNodes(): GraphNode[] {
    const recorded = this._normaliseGraph(this.appState.state.graphData).nodes;
    return recorded.length ? recorded : this._streamingRenderer?.getNodes() ?? [];
  }

  /**
   * Frame these nodes and make them the selection the radial menu's selection
   * ring acts on -- how the chrestomathy points back at the graph it read.
   * Returns how many were on the canvas; with none, the selection is left as
   * it was rather than emptied.
   */
  public showOnCanvas(ids: readonly string[]): number {
    const r = this._streamingRenderer;
    if (!r) return 0;
    const wanted = new Set(ids);
    const found = r.getNodes().filter((n) => wanted.has(n.id));
    if (!found.length) return 0;
    this._replaceSelection(found);
    r.fitTo(found.map((n) => n.id));
    this.focusDockPanel('graph');
    return found.length;
  }

  /** A verb the ring shows disabled, refused out loud if it ever commits. */
  private _radUnsupported(verb: string): void {
    this.updatePanelState({
      statusMessage: `${verb} is not available on this renderer`,
    });
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
        let added = 0;
        try {
          for (const id of ids) {
            const payload = await PlotService.expandNode(this.appState.api.parse, directory, id, DEEPEST_DEPTH);
            const { nodes, edges } = this._normaliseGraph(payload);
            // The subgraph includes the node that was expanded; mergeGraph
            // skips ids already on the canvas, so this is idempotent.
            const before = r.getNodes().length;
            r.mergeGraph(nodes, edges);
            added += r.getNodes().length - before;
          }
        } finally {
          // Whatever happened, the status line stops claiming work is in
          // flight. Without this a rejected expand leaves "Expanding…" up
          // for the rest of the session.
          this._rad?.applyViewState();
          this.updatePanelState({
            statusMessage: added > 0 ? `Expanded — ${added} new node(s)` : 'Nothing further to expand',
          });
        }
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

      /**
       * Re-runs the last plot, which re-streams and remounts. The flag is how
       * the remount below learns this is the same graph arriving again rather
       * than a new one, so view state is carried across.
       */
      relayout: () => {
        this._radRelayoutPending = true;
        void this._lastPlotAction?.();
      },

      // Disabled in the ring: this renderer's positions come from the backend
      // layout, and there is no force simulation to toggle. They are wired to
      // an explicit refusal rather than to `{}` or to a fit, so that if one
      // ever does commit it says so instead of looking like it worked.
      spread: () => this._radUnsupported('spread'),
      cluster: () => this._radUnsupported('cluster'),
      togglePhysics: () => this._radUnsupported('toggle-physics'),

      /**
       * One hop, and only one.
       *
       * The seed set is snapshotted before the scan: growing the set being
       * tested while iterating the edge list makes the result depend on edge
       * order, which reaches an arbitrary number of hops rather than a
       * defined one.
       */
      selectNeighbors: (ids) => {
        const r = renderer();
        if (!r) return;
        const seeds = new Set<string>(ids);
        const want = new Set<string>(ids);
        for (const e of r.getEdges()) {
          const s = String(e.source);
          const t = String(e.target);
          if (seeds.has(s)) want.add(t);
          if (seeds.has(t)) want.add(s);
        }
        this._replaceSelection(r.getNodes().filter((n) => want.has(n.id)));
      },
      clearSelection: () => this._replaceSelection([]),

      /** Frame the node and everything under it, not the whole graph. */
      focusGroup: (id) => {
        const r = renderer();
        if (!r) return;
        const subtree = [id];
        for (let i = 0; i < subtree.length; i++) {
          for (const kid of r.childIdsOf(subtree[i])) {
            if (!subtree.includes(kid)) subtree.push(kid);
          }
        }
        r.fitTo(subtree);
      },

      // The opener a double-click on the node uses, so the two cannot differ.
      viewSource: (id) => { renderer()?.openSource(id); },
      // `show`, not `hint`: a hint speaks once a session, and Info is a verb
      // a person uses again (node_info.ts says why that matters).
      showInfo: (id) => {
        const node = renderer()?.getNodes().find((n) => n.id === id);
        if (node) ToastManager.show(infoLine(node), 8_000);
      },
      // What this node is, beside every language that writes it. The panel
      // reads `constructChosen`, which loading sets, so it opens on it.
      compare: (id) => {
        const node = renderer()?.getNodes().find((n) => n.id === id);
        if (typeof node?.construct !== 'string') return;
        void this.actions.plot.cartography.loadChrestomathy(node.construct);
        this.openPanel('chrestomathy-panel');
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
  private _mountRad(renderer: StreamingGraphRenderer, keepViewState = false): void {
    const wasRelayout = this._radRelayoutPending;
    this._radRelayoutPending = false;
    keepViewState = keepViewState || wasRelayout;
    this._rad?.destroy();
    this._radSelection.clear();
    // A relayout re-streams the same graph, so hide/pin/colour have to
    // outlive it — §5.1 of the integration standard, and a claim this
    // record's ADR makes in as many words. A new plot target is a different
    // graph and starts clean. Keyed on ids, so nodes that come back get
    // their state back and nodes that do not are simply never painted.
    if (!keepViewState) this._nodeViewState = EMPTY_VIEW_STATE;

    const rad = new RadExtension({
      ops: this._radOps(),
      viewState: () => this._nodeViewState,
      facts: (context) => this._radFacts(context),
      onError: (verb, err) => {
        this.updatePanelState({ statusMessage: `${verb} failed: ${String(err)}` });
      },
    });

    const context = renderer.buildExtensionContext(this._radSelection, () => m.redraw());

    rad.initialize(context);
    rad.apply();
    this._rad = rad;

    // The key, on the same context and the same lifetime as the menu. It
    // reads the scene the renderer just finished, so it is mounted here
    // rather than during the stream, when the counts would be a snapshot
    // of a graph still arriving.
    this._legend?.destroy();
    const legend = new LegendExtension(() => this.appState.state.graphStyling.colorBy);
    legend.initialize(context);
    legend.apply();
    this._legend = legend;
  }

  /** Core SSE render loop (shared by all stream starters). */
  /**
   * What to append to a status line when the renderer had to place nodes
   * itself, and the empty string when it did not.
   *
   * **SILENCE IS THE NORMAL CASE AND HAS TO STAY SILENT.** Every backend
   * graph source lays its own nodes out, so this appends nothing on every
   * path that works. It exists so the one that stops doing so is visible
   * in the place a reader is already looking, rather than as a graph that
   * merely looks oddly circular.
   */
  private _fallbackNote(renderer: StreamingGraphRenderer): string {
    const { placed, total } = renderer.layoutFallback();
    if (placed === 0) return '';
    return ` — ${placed} of ${total} placed without backend positions`;
  }

  private _mountAndStream(
    startFn: (renderer: StreamingGraphRenderer) => () => void,
    statusMsg: string,
  ): void {
    if (this._cancelStream) {
      this._cancelStream();
      this._cancelStream = null;
    }
    // The stream is the latest plot: added files, the demo or a lexicon still
    // waiting for an answer are not drawn over it.
    this.actions.plot.supersedePlots();
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
    const notes: string[] = [];
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
          onNote: (message) => {
            notes.push(message);
            ToastManager.show(message, 15_000);
          },
          onDone: (elapsed_ms, from_cache) => {
            this._cancelStream = null;
            renderer.finalize();
            // Keep the renderer: rad mounts against it, and its ops need a
            // live handle for the whole session, not just the stream.
            // Announced rather than mounted here, so this path and the
            // registry's converge on the one subscription in the constructor.
            GraphSurface.publish(renderer);
            this.appState.update({ parseDirectory: directory });
            // Replaced, never merged: a plain patch is the union of this graph
            // and every one drawn before it, which the census then read as
            // the canvas -- a code map after the crate graph listed crates.
            this.appState.replaceGraphData(this._buildGraphData(accNodes, accEdges, {
              nodeCount,
              edgeCount: accEdges.length,
              layout,
            }) as any);
            if (this.appState.state.selectedRenderer !== 'd3') {
              this.actions.plot.createGraphVnode();
            }
            const msg = from_cache
              ? `Served from cache (${nodeCount} nodes)`
              : `Done in ${elapsed_ms}ms (${nodeCount} nodes)`;
            this.updatePanelState({
              isLoading: false,
              statusMessage: msg + this._fallbackNote(renderer) + notesTail(notes),
              progress: null,
            });
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
    const notes: string[] = [];
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
          onNote: (message) => {
            notes.push(message);
            ToastManager.show(message, 15_000);
          },
          onDone: (elapsed_ms, from_cache) => {
            this._cancelStream = null;
            renderer.finalize();
            // Keep the renderer: rad mounts against it, and its ops need a
            // live handle for the whole session, not just the stream.
            // Announced rather than mounted here, so this path and the
            // registry's converge on the one subscription in the constructor.
            GraphSurface.publish(renderer);
            // Replaced, never merged (see `_startStream`).
            this.appState.replaceGraphData(this._buildGraphData(accNodes, accEdges, {
              nodeCount,
              edgeCount: accEdges.length,
              layout,
            }) as any);
            if (this.appState.state.selectedRenderer !== 'd3') {
              this.actions.plot.createGraphVnode();
            }
            const msg = from_cache
              ? `Served from cache (${nodeCount} nodes)`
              : `Done in ${elapsed_ms}ms (${nodeCount} nodes)`;
            this.updatePanelState({
              isLoading: false,
              statusMessage: msg + this._fallbackNote(renderer) + notesTail(notes),
              progress: null,
            });
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

  /**
   * Plot added files, every one given, at the parse depth the Open panel
   * shows; one file clicked in the Files panel and Plot over all of them both
   * come here. A plot asked for before these answered owns the status line,
   * and their answer is dropped (`latest_plot.ts`).
   */
  private async _plotUploads(files: RawFile[]): Promise<void> {
    const many = files.length === 1 ? files[0].name : `${files.length} files`;
    this.updatePanelState({ isLoading: true, statusMessage: `Plotting ${many}\u2026` });
    // What the parse could not read is said as a stream says its `note`
    // events: each in a toast, and all of them after "Ready" (`notesTail`).
    let notes: string[] | null = [];
    this._lastPlotAction = async () => {
      notes = await this.actions.plot.plotUploads(files, this.panelState.parseDepth);
      for (const note of notes ?? []) ToastManager.show(note, 15_000);
    };
    try {
      await this._lastPlotAction();
      if (notes) this.updatePanelState({ isLoading: false, statusMessage: 'Ready' + notesTail(notes) });
    } catch {
      this.updatePanelState({ isLoading: false, statusMessage: `Error plotting ${many}` });
    }
  }

  // ── Callback builder ───────────────────────────────────────────────────────

  private _buildCallbacks(): ControlPanelCallbacks {
    return {
      onDemo: async () => {
        this.updatePanelState({ isLoading: true, statusMessage: 'Loading demo...' });
        let drawn = true;
        this._lastPlotAction = async () => { drawn = await this.actions.plot.loadDemo(); };
        try {
          await this._lastPlotAction();
          // Not drawn: a plot asked for since owns the status line.
          if (drawn) this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: 'Error loading demo' });
        }
      },

      onLoadLexicon: async (language: string) => {
        this.updatePanelState({ isLoading: true, statusMessage: `Loading ${language} lexicon...` });
        let drawn = true;
        this._lastPlotAction = async () => { drawn = await this.actions.plot.loadLexicon(language); };
        try {
          await this._lastPlotAction();
          if (drawn) this.updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: `Error loading ${language} lexicon` });
        }
      },

      onBundledExample: (example) => {
        this.panelCallbacks.onRepoSubmit(example.url);
        // Its recorded cargo documents are part of it. A source that loads
        // data for a panel brings that panel forward, as View ▸ Compare
        // brings the Chrestomathy panel.
        if (example.cargo) {
          void this.actions.plot.cartography.loadCargoReading(example.url);
          this.openPanel('cargo-panel');
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
              ToastManager.hint('stub-folders', 'Large repo: a folder marked … is unread; click it to read it, or use "Expand All" in the Files panel');
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

      /**
       * The Open panel's Plot: the loaded repository, by the URL its tree was
       * read from when it has one; else every added file; else the URL in the
       * field, fetched and drawn as → Fetch does (`plot_target.ts`). What was
       * drawn is what a layout change or Relayout draws again.
       */
      onPlot: () => {
        const repo = this.appState.repo.content;
        const target = plotTarget(repo, this.uploadedFiles.length, this.panelState.repoUrl);
        if (target?.kind === 'repository') {
          const { url } = target;
          this._lastPlotAction = () => { this._startStreamFromUrl(url); };
          this._startStreamFromUrl(url);
        } else if (target?.kind === 'tree' && repo) {
          this._lastPlotAction = () => { this._startStream(repo, 'Streaming graph\u2026'); };
          this._startStream(repo, 'Streaming graph\u2026');
        } else if (target?.kind === 'files') {
          void this._plotUploads([...this.uploadedFiles]);
        } else if (target?.kind === 'fetch') {
          this.panelCallbacks.onRepoSubmit(target.url);
        }
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
        await this._plotUploads([file]);
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
        // The renderer recolours in place; the key says what the colours now
        // mean. A streamed plot is not redrawn below, so without this its key
        // kept describing the colouring it was drawn with.
        if (options.colorBy !== undefined) this._legend?.apply();
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

      // **NEITHER READ TOUCHES THE PANEL'S LOADING STATE.** `isLoading` and
      // the status line are the stream's: the Open panel's plot bar shows
      // Cancel and the progress bar while it is set. These set it and cleared
      // it with "Ready" when they ended, so a folder opened mid-parse took
      // Cancel and the progress bar from a stream still running. The folder's
      // ↻ says it is being read; a toast says Expand All has begun, and either
      // failing.
      onFolderExpand: async (path: string) => {
        const content = this.appState.repo.content;
        if (!content?.is_partial) return false;
        try {
          // The tree's own repository, not the URL field's: that follows every
          // keystroke, and need not name the repository shown.
          return await this.actions.repo.expandPath(path);
        } catch {
          // The folder is left unread, so a click reads it again.
          ToastManager.show(`Could not read ${path}; click it to try again`);
          return false;
        }
      },

      onExpandAll: async () => {
        const content = this.appState.repo.content;
        if (!content?.is_partial) return;
        ToastManager.show('Expanding all folders…');
        try {
          await this.actions.repo.expandAll();
        } catch {
          ToastManager.show('Could not expand the tree');
        }
      },

      onLoadFromCache: async (key: string) => {
        const entry = this.cachedGraphs?.find((e) => e.key === key);
        if (!entry) return;
        // Streaming from the URL will hit the backend cache and replay instantly.
        this.updatePanelState({ repoUrl: entry.url });
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
        this.updatePanelState({ repoUrl: '' });
      },

      onSaveRecent: (entry) => {
        void this.saveGraphbaseBookmark(entry.label || entry.url.replace('https://github.com/', ''), entry.url);
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
