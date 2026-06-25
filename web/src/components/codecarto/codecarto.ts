import m from 'mithril';

import { ICell } from '../../state/cell_state';
import { StateController } from '../../state/state_controller';
import { createActions, AppActions } from '../../state/actions';
import { Directory, RawFile, RawFolder, RepoInfo } from '../models/source';

import { ControlPanel, ControlPanelState, ControlPanelCallbacks, ControlPanelContent, LoadingProgress, CachedEntry } from './control_panel';
import { Plot } from '../../features/graph';
import { PlotService } from '../../services/plot_service';
import { StreamingGraphRenderer } from '../../features/graph/services/streaming_renderer';
import { HelpModal, HelpModalComponent } from './help/help_modal';
import { ToastContainer, ToastManager } from './help/toast';

import './codecarto.css';
import './help/help_modal.css';

/** Convert frontend layout name (snake_case) to backend format (PascalCase) */
function _convertLayout(frontendLayout: string): string {
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

/** The Code Cartographer app component - returns a Mithril closure component */
export const CodeCarto = (getCell: () => ICell): m.Component => {
  // Get initial cell for setting up actions (they need cell.update)
  const initialCell = getCell();
  const appState = new StateController(initialCell);
  const actions: AppActions = createActions(appState);

  // Local uploaded files storage (not in global state yet)
  let uploadedFiles: RawFile[] = [];

  // Track last plot action for re-executing when layout changes
  let lastPlotAction: (() => Promise<void> | void) | null = null;

  // Cancel function for in-flight SSE streams
  let cancelStream: (() => void) | null = null;

  // Live streaming renderer (active during SSE stream)
  let streamingRenderer: StreamingGraphRenderer | null = null;

  // Cached graph entries (fetched from backend)
  let cachedGraphs: CachedEntry[] | null = null;

  async function refreshCache(): Promise<void> {
    try {
      const resp = await fetch(`${appState.api.parse}/cache`);
      if (resp.ok) {
        const data = await resp.json();
        cachedGraphs = (data?.results?.entries as CachedEntry[]) ?? [];
        m.redraw();
      }
    } catch { /* non-fatal */ }
  }

  // Control panel local state - UI-only state, persists across redraws
  // Note: graphStyling, parserOptions, selectedRenderer come from cell.state (single source of truth)
  let panelState: ControlPanelState = {
    isOpen: false,
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

  // Helper to update panel state and trigger redraw
  const updatePanelState = (updates: Partial<ControlPanelState>) => {
    panelState = { ...panelState, ...updates };
    m.redraw();
  };

  // Helper to update progress without a full state copy
  const updateProgress = (progress: LoadingProgress | null) => {
    panelState.progress = progress;
    m.redraw();
  };

  // ── Helpers ────────────────────────────────────────────────────────────────

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

  /**
   * Build a gJGF-shaped graphData object from accumulated stream nodes/edges.
   * Stored in state so renderer switching works after a stream completes.
   */
  function _buildGraphData(
    nodes: { id: string; [k: string]: unknown }[],
    edges: { source: string; target: string; [k: string]: unknown }[],
    meta: { nodeCount: number; edgeCount: number; layout: string }
  ): unknown {
    const graphNodes: Record<string, unknown> = {};
    for (const node of nodes) {
      const { id, ...rest } = node;
      graphNodes[id] = { metadata: rest };
    }
    return {
      graph: { nodes: graphNodes, edges },
      metadata: { nodeCount: meta.nodeCount, edgeCount: meta.edgeCount, layout: meta.layout, type: 'd3' },
    };
  }

  /** Core SSE render loop shared by _startStream and _startStreamFromUrl. */
  function _mountAndStream(
    startFn: (renderer: StreamingGraphRenderer) => (() => void),
    statusMsg: string,
  ): void {
    if (cancelStream) { cancelStream(); cancelStream = null; }
    streamingRenderer = null;

    const styling = appState.state.graphStyling;

    updatePanelState({
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
        streamingRenderer = new StreamingGraphRenderer(el, styling);
        cancelStream = startFn(streamingRenderer);
      },
    });

    appState.updatePlotFrame([canvasVnode]);
  }

  /** Stream a pre-fetched Directory via /parse/stream. */
  function _startStream(directory: Directory, statusMsg: string): void {
    const opts = appState.state.parserOptions;
    const layout = _convertLayout(appState.state.graphStyling.layout);
    const exts = opts.fileExtensions.length > 0 ? opts.fileExtensions : null;
    const depth = panelState.parseDepth;

    const accNodes: { id: string; [k: string]: unknown }[] = [];
    const accEdges: { source: string; target: string; [k: string]: unknown }[] = [];
    let nodeCount = 0;

    _mountAndStream(
      (renderer) => PlotService.streamUnified(
        appState.api.parse, directory, { depth, extensions: exts, layout },
        {
          onMeta: (meta) => {
            renderer.setTotal(meta.nodeCount);
            updateProgress({ loaded: 0, total: meta.nodeCount, phase: 'streaming' });
          },
          onNode: (node) => {
            nodeCount++;
            accNodes.push(node as any);
            if (nodeCount % 5 === 0)
              updateProgress({ loaded: nodeCount, total: panelState.progress?.total ?? 0, phase: 'streaming' });
            renderer.addNode(node as any);
          },
          onEdge: (edge) => { accEdges.push(edge as any); renderer.addEdge(edge as any); },
          onDone: (elapsed_ms, from_cache) => {
            cancelStream = null;
            renderer.finalize();
            streamingRenderer = null;
            appState.update({
              parseDirectory: directory,
              graphData: _buildGraphData(accNodes, accEdges, { nodeCount, edgeCount: accEdges.length, layout }) as any,
            });
            // Switch to the selected renderer if it isn't d3 (streaming IS the d3 experience)
            if (appState.state.selectedRenderer !== 'd3') {
              actions.plot.createGraphVnode();
            }
            const msg = from_cache ? `Served from cache (${nodeCount} nodes)` : `Done in ${elapsed_ms}ms (${nodeCount} nodes)`;
            updatePanelState({ isLoading: false, statusMessage: msg, progress: null });
            ToastManager.hint('first-graph', 'Scroll to zoom, drag to pan, hover nodes for details');
            refreshCache();
          },
          onError: (msg) => {
            cancelStream = null;
            streamingRenderer = null;
            updatePanelState({ isLoading: false, statusMessage: `Error: ${msg}`, progress: null });
          },
        }
      ),
      statusMsg,
    );
  }

  /** Stream directly from a GitHub URL via /parse/stream-url (two-phase, no pre-fetch wait). */
  function _startStreamFromUrl(githubUrl: string): void {
    const opts = appState.state.parserOptions;
    const layout = _convertLayout(appState.state.graphStyling.layout);
    const exts = opts.fileExtensions.length > 0 ? opts.fileExtensions : null;
    const depth = panelState.parseDepth;

    const accNodes: { id: string; [k: string]: unknown }[] = [];
    const accEdges: { source: string; target: string; [k: string]: unknown }[] = [];
    let nodeCount = 0;

    _mountAndStream(
      (renderer) => PlotService.streamFromUrl(
        appState.api.parse, githubUrl, { depth, extensions: exts, layout },
        {
          onFetching: (msg) => updatePanelState({ statusMessage: msg }),
          onMeta: (meta) => {
            renderer.setTotal(meta.nodeCount);
            updateProgress({ loaded: 0, total: meta.nodeCount, phase: 'streaming' });
          },
          onNode: (node) => {
            nodeCount++;
            accNodes.push(node as any);
            if (nodeCount % 5 === 0)
              updateProgress({ loaded: nodeCount, total: panelState.progress?.total ?? 0, phase: 'streaming' });
            renderer.addNode(node as any);
          },
          onEdge: (edge) => { accEdges.push(edge as any); renderer.addEdge(edge as any); },
          onDone: (elapsed_ms, from_cache) => {
            cancelStream = null;
            renderer.finalize();
            streamingRenderer = null;
            appState.update({
              graphData: _buildGraphData(accNodes, accEdges, { nodeCount, edgeCount: accEdges.length, layout }) as any,
            });
            // Switch to the selected renderer if it isn't d3 (streaming IS the d3 experience)
            if (appState.state.selectedRenderer !== 'd3') {
              actions.plot.createGraphVnode();
            }
            const msg = from_cache ? `Served from cache (${nodeCount} nodes)` : `Done in ${elapsed_ms}ms (${nodeCount} nodes)`;
            updatePanelState({ isLoading: false, statusMessage: msg, progress: null });
            ToastManager.hint('first-graph', 'Scroll to zoom, drag to pan, hover nodes for details');
            refreshCache();
          },
          onError: (msg) => {
            cancelStream = null;
            streamingRenderer = null;
            updatePanelState({ isLoading: false, statusMessage: `Error: ${msg}`, progress: null });
          },
        }
      ),
      'Connecting to GitHub\u2026',
    );
  }

  // Control panel callbacks - fully wired
  const panelCallbacks: ControlPanelCallbacks = {
    // Demo
    onDemo: async () => {
      updatePanelState({ isLoading: true, statusMessage: 'Loading demo...' });

      // Store this action for re-execution when layout changes
      lastPlotAction = async () => {
        await actions.plot.loadDemo();
      };

      try {
        await lastPlotAction();
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error loading demo' });
      }
    },
    
    // Repository - start streaming graph immediately; populate sidebar tree in background
    onRepoSubmit: (url: string) => {
      panelState.repoUrl = url;
      lastPlotAction = () => { panelCallbacks.onRepoSubmit(url); };

      // Start graph stream NOW — no waiting for the repo fetch
      _startStreamFromUrl(url);

      // Populate the sidebar tree in parallel (non-blocking)
      actions.repo.fetchRepository(url)
        .then(() => {
          const repoDir = appState.repo.content;
          if (repoDir?.is_partial) {
            ToastManager.hint('stub-folders', 'Large repo: click a folder ▶ to expand it, or use "Expand All"');
          }
          m.redraw();
        })
        .catch(() => { /* sidebar won't show tree, but graph still works */ });
    },
    
    // Repository - click file in tree → stream a single-file parse
    onRepoFileClick: async (url: string) => {
      const repoContent = appState.repo.content;
      if (!repoContent) return;
      const file = findFileByUrl(repoContent.root, url);
      if (!file) return;

      // Fetch raw content if not available (large repos return files with raw='')
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
        new RawFolder('', 0, [new RawFile(file.name, file.size, rawContent, url)])
      );

      lastPlotAction = () => { panelCallbacks.onRepoFileClick(url); };
      _startStream(singleFileDir, `Plotting ${file.name}\u2026`);
    },
    
    // Repository - plot whole directory (SSE streaming with live canvas)
    onPlotWholeRepo: () => {
      // Always stream directly from the URL so file content is fetched on demand.
      // This makes parse depth effective (symbols require file content) and avoids
      // depending on the pre-fetched repo content which has raw='' for most files.
      if (panelState.codeSourceMode === 'repo' && panelState.repoUrl) {
        lastPlotAction = () => { panelCallbacks.onPlotWholeRepo(); };
        _startStreamFromUrl(panelState.repoUrl);
        return;
      }
      // Uploads: use pre-fetched content (uploads always have full content)
      const repoContent = appState.repo.content;
      if (!repoContent || repoContent.size === 0) return;
      lastPlotAction = () => { panelCallbacks.onPlotWholeRepo(); };
      _startStream(repoContent, 'Streaming graph\u2026');
    },
    
    // Upload - file upload handler
    onFileUpload: (files: FileList) => {
      updatePanelState({ isLoading: true, statusMessage: 'Processing files...' });
      
      const newFiles: RawFile[] = [];
      let processed = 0;
      
      Array.from(files).forEach(file => {
        // Check if file already exists
        const exists = uploadedFiles.some(f => f.name === file.name);
        if (exists) {
          processed++;
          if (processed === files.length) {
            updatePanelState({ isLoading: false, statusMessage: `${newFiles.length} new file(s) added` });
          }
          return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
          const content = e.target?.result as string;
          const newFile = new RawFile(file.name, file.size, content, file.webkitRelativePath || file.name);
          newFiles.push(newFile);
          uploadedFiles.push(newFile);
          processed++;
          
          // Update state when all files are processed
          if (processed === files.length) {
            // Also update the global state for consistency
            appState.update({
              local: {
                content: new Directory(
                  new RepoInfo(),
                  uploadedFiles.length,
                  new RawFolder('uploads', 0, uploadedFiles)
                ),
              },
            });
            updatePanelState({ isLoading: false, statusMessage: `${newFiles.length} file(s) added` });
          }
        };
        reader.readAsText(file);
      });
    },
    
    // Upload - click uploaded file
    onUploadedFileClick: async (file: RawFile) => {
      updatePanelState({ isLoading: true, statusMessage: 'Plotting file...' });

      // Store this action for re-execution when layout changes
      lastPlotAction = async () => {
        await actions.plot.plotUploadedFile(file);
      };

      try {
        await lastPlotAction();
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error plotting file' });
      }
    },

    // Upload - plot all uploaded files
    onPlotAllUploads: async () => {
      if (uploadedFiles.length > 0) {
        updatePanelState({ isLoading: true, statusMessage: 'Plotting all files...' });

        // Store this action for re-execution when layout changes
        lastPlotAction = async () => {
          if (uploadedFiles.length > 0) {
            // For now, plot the first file - TODO: implement multi-file plotting
            await actions.plot.plotUploadedFile(uploadedFiles[0]);
          }
        };

        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: 'Error plotting files' });
        }
      }
    },
    
    // Settings - theme change
    onThemeChange: (theme: string) => {
      // Theme is handled by CSS variables via data-theme attribute in control panel
      if (appState.state.selectedRenderer === 'notebook' && appState.state.graphData) {
        actions.plot.createGraphVnode();
      }
    },

    // Graph styling change - use appState for consistent updates
    onGraphStylingChange: async (options) => {
      console.log('[VISUAL] onGraphStylingChange called with options:', JSON.stringify(options));

      // Read old values from appState (single source of truth)
      const currentState = appState.state;
      const oldLayout = currentState.graphStyling.layout;
      const newLayout = options.layout;
      const oldPhysics = currentState.graphStyling.enablePhysics;
      const newPhysics = options.enablePhysics;

      console.log('[VISUAL] Before update - appState.state.graphStyling:', JSON.stringify(currentState.graphStyling));

      // Update through appState (single source of truth)
      appState.update({
        graphStyling: { ...currentState.graphStyling, ...options }
      });

      console.log('[VISUAL] After update - appState.state.graphStyling:', JSON.stringify(appState.state.graphStyling));

      // If layout changed, trigger a re-fetch from backend
      if (newLayout && newLayout !== oldLayout && lastPlotAction) {
        updatePanelState({ isLoading: true, statusMessage: 'Applying new layout...' });
        try {
          await lastPlotAction();
          updatePanelState({ isLoading: false, statusMessage: 'Ready' });
        } catch (error) {
          updatePanelState({ isLoading: false, statusMessage: 'Error applying layout' });
        }
        return;
      }

      // If physics toggle changed, re-render graph with new physics setting
      if (newPhysics !== undefined && newPhysics !== oldPhysics && appState.state.graphData) {
        console.log(`Physics ${newPhysics ? 'enabled' : 'disabled'} - re-rendering graph`);
        actions.plot.createGraphVnode();
        return;
      }

      // For other styling changes, just re-render with existing data
      if (appState.state.graphData || appState.state.selectedRenderer === 'system') {
        console.log('[VISUAL] Calling createGraphVnode() for non-layout styling change');
        actions.plot.createGraphVnode();
      } else {
        console.log('[VISUAL] No graphData in state - skipping createGraphVnode()');
      }
    },

    // Parser options change (file extensions)
    onParserOptionsChange: (options) => {
      const currentState = appState.state;
      appState.update({
        parserOptions: { ...currentState.parserOptions, ...options }
      });
    },

    // Repository - lazily expand a stub folder (large repo shallow mode)
    onFolderExpand: async (path: string) => {
      updatePanelState({ isLoading: true, statusMessage: `Loading ${path}...` });
      try {
        await actions.repo.expandPath(panelState.repoUrl, path);
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: `Error expanding ${path}` });
      }
    },

    // Repository - expand all stub folders (structure only, no file content)
    onExpandAll: async () => {
      updatePanelState({ isLoading: true, statusMessage: 'Expanding all folders...' });
      try {
        await actions.repo.expandAll(panelState.repoUrl);
        updatePanelState({ isLoading: false, statusMessage: 'Ready' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error expanding tree' });
      }
    },

    // C Parser - download GitHub repo and parse C/C++ files
    onCParserGithub: async (repoUrl: string) => {
      updatePanelState({ isLoading: true, statusMessage: `Fetching & parsing C repo: ${repoUrl}` });
      appState.update({ selectedRenderer: 'd3' });

      lastPlotAction = async () => {
        await actions.plot.plotCGithub(repoUrl);
      };

      try {
        await lastPlotAction();
        updatePanelState({ isLoading: false, statusMessage: 'C repo parsed' });
      } catch (error) {
        updatePanelState({ isLoading: false, statusMessage: 'Error: ' + String(error) });
      }
    },

    // Cache - load a cached graph (uses /parse/unified which checks cache first)
    onLoadFromCache: async (key: string) => {
      const entry = cachedGraphs?.find(e => e.key === key);
      if (!entry) return;

      updatePanelState({ isLoading: true, statusMessage: `Loading from cache…`, progress: null });
      try {
        const resp = await fetch(`${appState.api.parse}/unified`, {
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
        if (json?.data) {
          actions.plot.handlePlotData(json.data);
        }
        updatePanelState({ isLoading: false, statusMessage: `Loaded from cache: ${entry.label}` });
      } catch {
        updatePanelState({ isLoading: false, statusMessage: 'Error loading from cache' });
      }
    },

    // Cache - evict a cached graph
    onEvictCache: async (key: string) => {
      try {
        await fetch(`${appState.api.parse}/cache/${key}`, { method: 'DELETE' });
        await refreshCache();
      } catch { /* non-fatal */ }
    },

    // Cancel in-flight stream
    onCancel: () => {
      if (cancelStream) {
        cancelStream();
        cancelStream = null;
      }
      updatePanelState({ isLoading: false, statusMessage: 'Cancelled', progress: null });
    },

    // Renderer change - use appState for consistent updates
    onRendererChange: (renderer) => {
      // Update through appState (single source of truth)
      appState.update({ selectedRenderer: renderer });

      console.log('Renderer changed to:', renderer, '- current state:', appState.state.selectedRenderer);

      // System renderer has its own built-in demo — no graph data required
      if (renderer === 'system' || appState.state.graphData) {
        updatePanelState({ statusMessage: `Switching to ${renderer} renderer...` });
        actions.plot.createGraphVnode();
        updatePanelState({ statusMessage: 'Ready' });
      } else {
        // No data loaded yet - provide feedback that renderer is set
        updatePanelState({ statusMessage: `Renderer: ${renderer}. Load source to apply.` });
      }
    },
  };

  // Return a closure component - view is called on each redraw, but closures are preserved
  return {
    oncreate: async () => {
      // Apply default theme on initial load
      const theme = panelState.currentTheme;
      document.documentElement.setAttribute('data-theme', theme === 'terminal' ? '' : theme);
      // Fetch available languages from backend (non-fatal)
      try { await actions.plot.initializeLanguages(); m.redraw(); } catch { /* non-fatal */ }
      // Load cached graphs list
      await refreshCache();
      // Show first-time help modal
      HelpModal.maybeShowFirstTime();
    },
    view: () => {
      // Use appState for consistent state access (single source of truth)
      const currentState = appState.state;

      // Build header
      const header = m('div.codecarto__header', [
        m('h1.codecarto__title', [
          m('span.codecarto__title-icon', '◈'),
          'Code Cartographer',
        ]),
        m('p.codecarto__subtitle', 'Visualize code architecture and dependencies'),
      ]);

      // Main content area - use fresh graphContent from current state
      const mainContent = m('div.codecarto__main', [
        m(Plot, { graphs: currentState.graphContent }),
        // E-stop: large red kill button overlaid on graph area while a stream is active
        panelState.isLoading ? m('div.graph-estop', [
          m('button.graph-estop__btn', {
            onclick: panelCallbacks.onCancel,
            title: 'Emergency stop — cancel stream',
          }, '⏹'),
        ]) : null,
      ]);

      // Control panel - pass fresh state values (single source of truth)
      const content: ControlPanelContent = {
        repoDirectory: currentState.repo.content,
        uploadedFiles: uploadedFiles,
        graphStyling: currentState.graphStyling,
        parserOptions: currentState.parserOptions,
        selectedRenderer: currentState.selectedRenderer,
        availableLanguages: currentState.availableLanguages ?? null,
        cachedGraphs: cachedGraphs,
      };

      const controlPanel = ControlPanel(
        panelState,
        panelCallbacks,
        updatePanelState,
        content
      );

      return m('div.codecarto', [
        header,
        mainContent,
        controlPanel,
        // Persistent help button
        m('button.cc-help-btn', {
          onclick: () => HelpModal.open(),
          title: 'Help & walkthrough',
        }, '?'),
        // Overlays (modal + toasts — rendered on top of everything)
        m(HelpModalComponent),
        m(ToastContainer),
      ]);
    },
  };
};
