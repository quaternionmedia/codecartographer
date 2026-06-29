/**
 * LayoutContext
 *
 * Central state-management hub for the Golden Layout integration.
 * Mirrors the logic inside the original `CodeCarto` closure component so that
 * every GL panel can share the same actions, streaming state, and callbacks
 * without duplicating business logic.
 *
 * Usage:
 *   const ctx = new LayoutContext(initialCell, getCell);
 *   // pass ctx to each panel factory function
 */

import m from 'mithril';

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

// ── Layout helpers ───────────────────────────────────────────────────────────

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

  // Reactive UI-only state for the control panel; mutating this then calling
  // m.redraw() is the same pattern used in the original CodeCarto component.
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

  // Streaming lifecycle refs
  private _cancelStream: (() => void) | null = null;
  private _streamingRenderer: StreamingGraphRenderer | null = null;
  private _lastPlotAction: (() => Promise<void> | void) | null = null;

  public readonly panelCallbacks: ControlPanelCallbacks;

  constructor(initialCell: ICell, private readonly getCell: () => ICell) {
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
        { depth, extensions: exts, layout },
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
            this._streamingRenderer = null;
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
        { depth, extensions: exts, layout },
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
            this._streamingRenderer = null;
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

  /** Stream a C/C++ GitHub repo via /c-parser/stream-github. */
  private _startStreamCGithub(githubUrl: string, maxFiles: number): void {
    const _AVG_C_NODES_PER_FILE = 40;
    this.appState.update({ selectedRenderer: 'd3' });
    const layout = convertLayout(this.appState.state.graphStyling.layout);

    const accNodes: { id: string; [k: string]: unknown }[] = [];
    const accEdges: { source: string; target: string; [k: string]: unknown }[] = [];
    let nodeCount = 0;

    this._mountAndStream((renderer) =>
      PlotService.streamCGithub(
        this.appState.api.cParser,
        githubUrl,
        maxFiles,
        layout,
        {
          onFetching: (msg) => this.updatePanelState({ statusMessage: msg }),
          onMeta: () => { /* unused — see onFileCount */ },
          onFileCount: (fileCount) => {
            const estimatedTotal = fileCount * _AVG_C_NODES_PER_FILE;
            renderer.setTotal(estimatedTotal);
            this.updatePanelState({ statusMessage: `Parsing ${fileCount} files…` });
            this._updateProgress({ loaded: 0, total: estimatedTotal, phase: 'streaming' });
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
          onReposition: (positions) => {
            for (const node of accNodes) {
              const pos = positions[node.id];
              if (pos) { node.x = pos.x; node.y = pos.y; }
            }
            renderer.repositionAll(positions);
          },
          onDone: (elapsed_ms) => {
            this._cancelStream = null;
            renderer.finalize();
            this._streamingRenderer = null;
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
            this.updatePanelState({
              isLoading: false,
              statusMessage: `Done in ${elapsed_ms}ms (${nodeCount} nodes)`,
              progress: null,
            });
            ToastManager.hint('first-graph', 'Scroll to zoom, drag to pan, hover nodes for details');
          },
          onError: (msg) => {
            this._cancelStream = null;
            this._streamingRenderer = null;
            this.updatePanelState({ isLoading: false, statusMessage: `Error: ${msg}`, progress: null });
          },
        },
      ),
      `Fetching & parsing C repo: ${githubUrl}`,
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

      onCParserGithub: (repoUrl: string) => {
        this._lastPlotAction = () => { this.panelCallbacks.onCParserGithub(repoUrl); };
        this._startStreamCGithub(repoUrl, 200);
      },

      onLoadFromCache: async (key: string) => {
        const entry = this.cachedGraphs?.find((e) => e.key === key);
        if (!entry) return;
        this.updatePanelState({ isLoading: true, statusMessage: 'Loading from cache\u2026', progress: null });
        try {
          const resp = await fetch(`${this.appState.api.parse}/unified`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              directory: {
                info: { url: entry.url, owner: '', name: entry.label },
                size: 0,
                root: { name: '', size: 0, files: [], folders: [] },
                is_partial: false,
              },
              depth: 2,
              layout: entry.layout,
              mode: entry.mode,
            }),
          });
          const json = await resp.json();
          if (json?.data) this.actions.plot.handlePlotData(json.data);
          this.updatePanelState({ isLoading: false, statusMessage: `Loaded from cache: ${entry.label}` });
        } catch {
          this.updatePanelState({ isLoading: false, statusMessage: 'Error loading from cache' });
        }
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
