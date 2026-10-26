import m from 'mithril';
import { exampleGroups } from '../../../features/examples/examples';
import type { BundledExample, Example } from '../../../features/examples/examples';
import { animations } from '../../../core/animations';
import { Directory, RawFile } from '../../models/source';
import { SystemDefinitionRegistry } from '../../../features/graph/services/system_renderer';
import { rendererControls } from '../../../features/graph/services/renderer_controls';
import { hasTree } from '../../../features/repository/repo_tree';
import { plotTarget } from '../../../features/repository/plot_target';
import { pressable } from './pressable';
import { GraphStylingOptions, ParserOptions, GraphRendererType } from '../../../state/types';
import './control_panel.css';

export type { GraphStylingOptions, ParserOptions, GraphRendererType };

export interface LoadingProgress {
  loaded: number;
  total: number;
  phase: 'parsing' | 'layout' | 'streaming' | 'done';
}

export interface ControlPanelState {
  repoUrl: string;
  currentTheme: string;
  isLoading: boolean;
  statusMessage: string;
  progress: LoadingProgress | null;
  graphSections: { layout: boolean; visual: boolean; theme: boolean };
  parseDepth: number;  // 1 = files only, 2 = symbols, 3 = sub-symbols
  /** Whether the Open panel's parse options are shown or folded to one line. */
  parseOptionsOpen: boolean;
}

export interface ControlPanelCallbacks {
  onDemo: () => void;
  onLoadLexicon?: (language: string) => void;
  onRepoSubmit: (url: string) => void;
  onRepoFileClick: (url: string) => void;
  /** Plot the loaded repository, else every added file, else the URL in the field. */
  onPlot: () => void;
  onFileUpload: (files: FileList) => void;
  onUploadedFileClick: (file: RawFile) => void;
  onThemeChange: (theme: string) => void;
  onGraphStylingChange: (options: Partial<GraphStylingOptions>) => void;
  onParserOptionsChange: (options: Partial<ParserOptions>) => void;
  onRendererChange: (renderer: GraphRendererType) => void;
  /** Read an unread folder; true when its contents reached the tree. */
  onFolderExpand: (path: string) => Promise<boolean>;
  onExpandAll?: () => Promise<void>;
  onCancel?: () => void;
  onLoadFromCache?: (key: string) => void;
  /** A bundled example: plot it, and read a Cargo workspace's records into the Cargo panel. */
  onBundledExample?: (example: Example) => void;
  onEvictCache?: (key: string) => void;
  /** Keep a recent graph as a Graphbase bookmark. */
  onSaveRecent?: (entry: CachedEntry) => void;
  onClearRepo?: () => void;
}

export interface CachedEntry {
  key: string;
  label: string;
  url: string;
  mode: string;
  layout: string;
  ts: number;
  age_seconds: number;
  size_bytes: number;
}

export interface ControlPanelContent {
  repoDirectory: Directory | null;
  uploadedFiles: RawFile[];
  // Settings from cell.state (single source of truth)
  graphStyling: GraphStylingOptions;
  parserOptions: ParserOptions;
  selectedRenderer: GraphRendererType;
  availableLanguages: Record<string, string[]> | null;
  availableLexiconLanguages: string[];
  cachedGraphs: CachedEntry[] | null;
  /** What `GET /repo/examples` offers; empty before it answers, or in an installed package. */
  bundledExamples: BundledExample[];
  /** Whether Graphbase answered, so a recent graph can be saved there. */
  graphbaseAvailable: boolean;
  /** The URLs Graphbase holds a bookmark for. */
  savedUrls: string[];
}

/** Which docked panel this renders: Open or Graph Settings. */
export type ControlPanelMode = 'open' | 'graph';

/** How many recent graphs the Open panel lists. */
const RECENT_SHOWN = 8;

const PARSE_DEPTHS = [
  { value: 1, label: 'Files', title: 'Depth 1: directory + file nodes' },
  { value: 2, label: 'Symbols', title: 'Depth 2: + top-level symbols (classes, functions)' },
  { value: 3, label: 'Deep', title: 'Depth 3: + sub-symbols (args, fields)' },
];

export interface ControlPanelRenderOptions {
  mode: ControlPanelMode;
}

const LAYOUT_OPTIONS = [
  { value: 'spring_layout', label: 'Spring' },
  { value: 'compound_layout', label: 'Compound' },
  { value: 'map_layout', label: 'Map' },
  { value: 'spectral_layout', label: 'Spectral' },
  { value: 'kamada_kawai_layout', label: 'Kamada-Kawai' },
  { value: 'circular_layout', label: 'Circular' },
  { value: 'spiral_layout', label: 'Spiral' },
  { value: 'random_layout', label: 'Random' },
  { value: 'shell_layout', label: 'Shell' },
  { value: 'sorted_square_layout', label: 'Sorted Square' },
];

const THEMES = [
  { id: 'qm',        label: 'QM',        preview: '#f2aa4c' },
  { id: 'terminal',  label: 'Terminal',  preview: '#00ff41' },
  { id: 'light',     label: 'Light',     preview: '#2196f3' },
  { id: 'cyberpunk', label: 'Cyberpunk', preview: '#ff00ff' },
  { id: 'ocean',     label: 'Ocean',     preview: '#00d4ff' },
  { id: 'sunset',    label: 'Sunset',    preview: '#ff6b35' },
  { id: 'forest',    label: 'Forest',    preview: '#52b788' },
  { id: 'noir',      label: 'Noir',      preview: '#ffffff' },
  { id: 'candy',     label: 'Candy',     preview: '#ff69eb' },
];

/**
 * The body of a docked control panel: Open or Graph Settings, by
 * `options.mode`. Each panel in `layout/panels/` mounts one mode.
 */
export function ControlPanel(
  state: ControlPanelState,
  callbacks: ControlPanelCallbacks,
  onStateChange: (updates: Partial<ControlPanelState>) => void,
  content: ControlPanelContent,
  options: ControlPanelRenderOptions,
): m.Vnode {
  const { mode } = options;

  const handleRepoUrlChange = (e: Event) => {
    const input = e.target as HTMLInputElement;
    onStateChange({ repoUrl: input.value });
  };

  const handleRepoSubmit = () => {
    if (state.repoUrl.trim()) {
      onStateChange({ isLoading: true, statusMessage: 'Fetching repository...' });
      callbacks.onRepoSubmit(state.repoUrl.trim());
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter') handleRepoSubmit();
  };

  const handleThemeChange = (themeId: string) => {
    document.documentElement.setAttribute('data-theme', themeId === 'terminal' ? '' : themeId);
    onStateChange({ currentTheme: themeId });
    callbacks.onThemeChange(themeId);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const dropzone = e.currentTarget as HTMLElement;
    dropzone.classList.remove('panel-upload__dropzone--active');
    if (e.dataTransfer?.files.length) {
      callbacks.onFileUpload(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    (e.currentTarget as HTMLElement).classList.add('panel-upload__dropzone--active');
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    (e.currentTarget as HTMLElement).classList.remove('panel-upload__dropzone--active');
  };

  const handleFileInput = (e: Event) => {
    const input = e.target as HTMLInputElement;
    if (input.files?.length) {
      callbacks.onFileUpload(input.files);
    }
  };

  const toggleGraphSection = (section: keyof ControlPanelState['graphSections']) => {
    onStateChange({
      graphSections: {
        ...state.graphSections,
        [section]: !state.graphSections[section],
      },
    });
  };

  // ─── Open ──────────────────────────────────────────────────────────────────
  // Every source a graph is opened from, the parse options once, and the one
  // Plot / Cancel bar. Browsing what was opened is the Files panel's.

  /** A GitHub URL or a local path, and what is loaded from one. */
  const renderUrlSection = () => {
    // Loaded when the Files panel shows the tree, as it asks: an Expand All
    // tree's size is its root's own file count, 0 with only folders there.
    const hasRepo = hasTree(content.repoDirectory);
    const repoInfo = content.repoDirectory?.info;

    return m('div.panel-source__repo', [
      m('div.panel-source__url-input', [
        m('input[type=text]', {
          placeholder: 'https://github.com/user/repository, or a local path',
          value: state.repoUrl,
          oninput: handleRepoUrlChange,
          onkeydown: handleKeyDown,
          disabled: state.isLoading,
        }),
        m('button.primary', {
          onclick: handleRepoSubmit,
          disabled: !state.repoUrl.trim() || state.isLoading,
        }, state.isLoading ? '...' : '→ Fetch'),
      ]),

      // What is loaded, in one line; the tree is the Files panel's.
      hasRepo ? m('div.panel-source__repo-loaded', [
        m('div.panel-source__repo-header', [
          m('span.panel-source__repo-name', `${repoInfo?.owner}/${repoInfo?.name}`),
          m('span.panel-source__repo-size', `${content.repoDirectory?.size} files`),
          callbacks.onClearRepo ? m('button.panel-source__repo-clear', {
            onclick: callbacks.onClearRepo,
            title: 'Clear the repository',
          }, '✕') : null,
        ]),
      ]) : null,
    ]);
  };

  /**
   * The project selector: each language's examples, Rust first, the bundled
   * ones (no network, no toolchain) leading their group. Shown with a
   * repository loaded too, so another is one click away.
   */
  const renderExamples = () =>
    m('div.panel-source__examples', exampleGroups(content.bundledExamples).flatMap((group) => [
      m('span.panel-settings__label-compact', group.language),
      m('div.panel-source__example-chips', { 'data-language': group.language.toLowerCase() },
        group.examples.map((ex) =>
          m('button.panel-source__example-chip', {
            class: ex.bundled ? 'panel-source__example-chip--bundled' : '',
            title: ex.title,
            'data-example': ex.label,
            onclick: (e: MouseEvent) => {
              animations.buttonPress(e.currentTarget as Element);
              onStateChange({ repoUrl: ex.url });
              if (ex.bundled && callbacks.onBundledExample) callbacks.onBundledExample(ex);
              else callbacks.onRepoSubmit(ex.url);
            },
            disabled: state.isLoading,
          }, ex.label),
        )),
    ]));

  /** Local files, added to what Plot draws; each is listed in the Files panel. */
  const renderLocalFiles = () => {
    const activeExts = content.parserOptions.fileExtensions;
    const browse = () => document.getElementById('file-upload-input')?.click();

    return m('div.panel-source__upload', [
      m('span.panel-settings__label-compact', 'Local files'),
      // A drop target that holds its hidden file input, so not a <button>:
      // `pressable` gives it a button's place in the tab order, its role, and
      // Enter and Space, so files are added from the keyboard too.
      m('div.panel-upload__dropzone', {
        ondrop: handleDrop,
        ondragover: handleDragOver,
        ondragleave: handleDragLeave,
        onclick: browse,
        ...pressable(browse),
      }, [
        m('span.panel-upload__icon', { 'aria-hidden': 'true' }, '📁'),
        m('span.panel-upload__text', 'Drop source files here or click to browse'),
        m('input#file-upload-input[type=file][multiple]', {
          style: { display: 'none' },
          attrs: activeExts.length > 0 ? { accept: activeExts.join(',') } : {},
          onchange: handleFileInput,
        }),
      ]),
      content.uploadedFiles.length > 0
        ? m('div.panel-source__upload-summary', `${content.uploadedFiles.length} file(s) added — see the Files panel`)
        : null,
    ]);
  };

  /** The demo, and one button per language with a Lexicon. */
  const renderQuickStart = () =>
    m('div.panel-source__quickstart', [
      m('span.panel-settings__label-compact', 'Demo and lexicons'),
      m('button.panel-settings__button-option', {
        onclick: (e: MouseEvent) => {
          animations.buttonPress(e.currentTarget as Element);
          callbacks.onDemo();
        },
        style: 'width: 100%;',
      }, [m('span', '⚡'), m('span', 'Load Demo')]),

      // Lexicon: one button per language with an abstraction-layer ontology
      // (see docs/architecture.md, Lexicons and the construct vocabulary); a
      // language gains one when it gains a lexicon YAML.
      content.availableLexiconLanguages.length > 0 && callbacks.onLoadLexicon
        ? m('div.panel-source__lexicon-picker', { style: 'display: flex; gap: 4px; margin-top: 4px;' },
            content.availableLexiconLanguages.map((lang) =>
              m('button.panel-settings__button-option', {
                key: lang,
                onclick: (e: MouseEvent) => {
                  animations.buttonPress(e.currentTarget as Element);
                  callbacks.onLoadLexicon!(lang);
                },
                style: 'flex: 1;',
                title: `Load the ${lang} Lexicon (abstraction-layer ontology)`,
              }, [m('span', '📖'), m('span', `${lang} Lexicon`)])
            )
          )
        : null,
    ]);

  /**
   * The graphs the server's cache holds, newest first: the one Recent list.
   * A chip replays one; ☆ keeps it in Graphbase when Graphbase is up; ✕
   * drops it from the cache.
   */
  const renderRecent = () => {
    const entries = content.cachedGraphs ?? [];
    const saved = new Set(content.savedUrls);
    const ago = (seconds: number) => {
      const mins = Math.round(seconds / 60);
      return mins < 60 ? `${mins}m ago` : `${Math.round(mins / 60)}h ago`;
    };

    return m('div.panel-source__cached', [
      m('span.panel-settings__label-compact', `Recent (${entries.length})`),
      entries.length > 0
        ? m('div.panel-source__cached-list', entries.slice(0, RECENT_SHOWN).map((entry) =>
            m('div.panel-source__cached-entry', { key: entry.key }, [
              m('button.panel-source__cached-chip', {
                onclick: () => callbacks.onLoadFromCache?.(entry.key),
                title: `${entry.url}\n${entry.mode} · ${entry.layout}`,
                disabled: state.isLoading,
              }, [
                m('span.panel-source__cached-label', entry.label || entry.url.replace('https://github.com/', '')),
                m('span.panel-source__cached-age', ago(entry.age_seconds)),
              ]),
              content.graphbaseAvailable
                ? saved.has(entry.url)
                  ? m('span.panel-source__cached-saved', { title: 'Saved in Graphbase' }, '★')
                  : m('button.panel-source__cached-save', {
                      onclick: () => callbacks.onSaveRecent?.(entry),
                      title: 'Save in Graphbase',
                    }, '☆')
                : null,
              m('button.panel-source__cached-evict', {
                onclick: () => callbacks.onEvictCache?.(entry.key),
                title: 'Remove from cache',
                disabled: state.isLoading,
              }, '✕'),
            ]),
          ))
        : m('p.panel-settings__hint', 'A repository drawn once is kept here, and replays without parsing.'),
    ]);
  };

  /** Extensions, depth and Lexicon annotation: what every plot is parsed with. */
  const renderParseOptions = () => {
    const parser = content.parserOptions;
    const depth = PARSE_DEPTHS.find((d) => d.value === state.parseDepth);
    const summary = [
      depth ? depth.label : `depth ${state.parseDepth}`,
      parser.fileExtensions.length ? parser.fileExtensions.join(', ') : 'every language',
      parser.annotateLexicon ? 'Lexicon' : null,
    ].filter(Boolean).join(' · ');

    return m('div.panel-open__parse', [
      m('div.panel-graph__section-header.panel-open__parse-toggle', {
        onclick: () => onStateChange({ parseOptionsOpen: !state.parseOptionsOpen }),
        'aria-expanded': String(state.parseOptionsOpen),
      }, [
        m('span.panel-graph__section-label', 'Parse options'),
        m('span.panel-open__parse-summary', summary),
        m('span.panel-graph__section-chevron', {
          class: state.parseOptionsOpen ? 'panel-graph__section-chevron--open' : '',
        }, '▶'),
      ]),
      state.parseOptionsOpen ? m('div.panel-graph__section-content', [
        m('div.panel-settings__group', [
          m('span.panel-settings__label-compact', 'Extensions'),
          content.availableLanguages ? m('div.panel-settings__chips',
            Object.entries(content.availableLanguages).map(([lang, exts]) => {
              const active = exts.length > 0 && exts.every(e => parser.fileExtensions.includes(e));
              return m('button.panel-settings__chip', {
                class: active ? 'panel-settings__chip--active' : '',
                onclick: () => {
                  const cur = parser.fileExtensions;
                  callbacks.onParserOptionsChange({
                    fileExtensions: active
                      ? cur.filter(e => !exts.includes(e))
                      : [...new Set([...cur, ...exts])],
                  });
                },
              }, lang);
            })
          ) : null,
          m('input.panel-settings__input-compact[type=text]', {
            value: parser.fileExtensions.join(', '),
            placeholder: 'Leave empty for all languages',
            onchange: (e: Event) => {
              const value = (e.target as HTMLInputElement).value;
              const extensions = value.split(',').map(ext => ext.trim()).filter(ext => ext.length > 0);
              callbacks.onParserOptionsChange({ fileExtensions: extensions });
            },
          }),
        ]),

        m('div.panel-settings__group', [
          m('span.panel-settings__label-compact', 'Parse Depth'),
          m('div.panel-settings__chips',
            PARSE_DEPTHS.map(opt =>
              m('button.panel-settings__chip', {
                class: state.parseDepth === opt.value ? 'panel-settings__chip--active' : '',
                onclick: () => onStateChange({ parseDepth: opt.value }),
                title: opt.title,
              }, opt.label)
            )
          ),
        ]),

        // Lexicon annotation stamps abstraction-layer data onto parsed nodes
        // whose language has a Lexicon (see docs/architecture.md, Lexicons
        // and the construct vocabulary); Color By: Abstraction Layer shows it.
        m('div.panel-settings__group', [
          m('div.panel-settings__toggle-row', [
            m('span.panel-settings__label-compact', 'Annotate Lexicon'),
            m('label.panel-settings__toggle-compact.panel-settings__toggle', [
              m('input[type=checkbox]', {
                checked: parser.annotateLexicon,
                title: 'Stamp abstraction-layer data onto real parsed nodes (currently c, python) — pair with Color By: Abstraction Layer to see it',
                onchange: (e: Event) => {
                  const checked = (e.target as HTMLInputElement).checked;
                  callbacks.onParserOptionsChange({ annotateLexicon: checked });
                },
              }),
              m('span.panel-settings__toggle-slider'),
            ]),
          ]),
        ]),
      ]) : null,
    ]);
  };

  /**
   * The one Plot / Cancel bar. Plot draws the loaded repository when there is
   * one, else every added file, else the URL in the field; Cancel stops a
   * stream in flight.
   */
  const renderPlotBar = () => {
    // What Plot draws, decided where `onPlot` decides it.
    const plotted = plotTarget(content.repoDirectory, content.uploadedFiles.length, state.repoUrl);
    const target = !plotted ? null
      : plotted.kind === 'files' ? `the ${plotted.count} added file(s)`
      : plotted.kind === 'fetch' ? plotted.url
      : 'the loaded repository';
    const progress = state.progress;
    const pct = progress && progress.total > 0 ? Math.round((progress.loaded / progress.total) * 100) : 0;

    return m('div.panel-plotbar', [
      m('button.panel-plotbar__plot', {
        disabled: !target || state.isLoading,
        title: target ? `Plot ${target}` : 'Fetch a repository or add files first',
        onclick: (e: MouseEvent) => {
          animations.buttonPress(e.currentTarget as Element);
          callbacks.onPlot();
        },
      }, [m('span', '▶'), m('span', 'Plot')]),
      m('button.panel-plotbar__cancel', {
        disabled: !state.isLoading,
        onclick: () => callbacks.onCancel?.(),
        title: 'Cancel the stream',
      }, [m('span', '⏹'), m('span', 'Cancel')]),
      m('div.panel-plotbar__status', [
        state.isLoading
          ? m('div.panel-plotbar__progress-wrap', [
              progress && progress.total > 0
                ? m('div.panel-plotbar__progress', { style: { width: `${pct}%` } })
                : m('div.panel-plotbar__progress.panel-plotbar__progress--indeterminate'),
            ])
          : null,
        m('span.panel-plotbar__status-text', [
          m('span.panel-plotbar__status-dot', {
            class: state.isLoading ? 'panel-plotbar__status-dot--active' : '',
          }),
          state.isLoading && progress && progress.phase === 'streaming'
            ? `Streaming ${progress.loaded}/${progress.total} nodes`
            : state.isLoading && progress
              ? `${progress.phase.charAt(0).toUpperCase() + progress.phase.slice(1)}…`
              : state.statusMessage || 'Ready',
        ]),
      ]),
    ]);
  };

  // The quick starts lead the left column and the examples close it: in the
  // default dock the Open panel is a short stack under the canvas, and the
  // empty canvas sends a first-time reader to ⚡ Load Demo, so the URL, the
  // local files and the demo are drawn above the column's fold.
  const renderOpenTab = () =>
    m('div.panel-section.panel-source.panel-open.panel-section--active', [
      m('div.panel-source__2col', [
        m('div.panel-source__left', [
          renderUrlSection(),
          renderLocalFiles(),
          renderQuickStart(),
          renderExamples(),
        ]),
        // The parse options lead the right column, folded to one line: under a
        // full Recent list they would sit below the fold of the default dock's
        // short Open panel. Opened, they push Recent down.
        m('div.panel-source__right', [
          renderParseOptions(),
          renderRecent(),
        ]),
      ]),
      renderPlotBar(),
    ]);

  // ─── Graph Settings (accordion) ────────────────────────────────────────────

  const renderGraphTab = () => {
    const styling = content.graphStyling;
    const selectedRenderer = content.selectedRenderer;
    const isSystem = selectedRenderer === 'system';
    const {
      layout: supportsLayout,
      physics: supportsPhysics,
      visual: supportsVisual,
    } = rendererControls(selectedRenderer);
    const sections = state.graphSections;

    const renderSectionHeader = (label: string, key: keyof typeof sections) =>
      m('div.panel-graph__section-header', {
        onclick: () => toggleGraphSection(key),
      }, [
        m('span.panel-graph__section-label', label),
        m('span.panel-graph__section-chevron', {
          class: sections[key] ? 'panel-graph__section-chevron--open' : '',
        }, '▶'),
      ]);

    const renderLabelColorGroup = () => m('div.panel-settings__group', [
      m('span.panel-settings__label-compact', 'Label Color'),
      m('input.panel-settings__color[type=color]', {
        value: styling.labelColor,
        oninput: (e: Event) => {
          const value = (e.target as HTMLInputElement).value;
          callbacks.onGraphStylingChange({ labelColor: value });
        },
      }),
    ]);

    return m('div.panel-section.panel-graph.panel-section--active', [
      // Renderer selector — always visible at top
      m('div.panel-settings__group', [
        m('span.panel-settings__label-compact', 'Renderer'),
        m('select.panel-settings__select', {
          value: selectedRenderer,
          onchange: (e: Event) => {
            const renderer = (e.target as HTMLSelectElement).value as GraphRendererType;
            callbacks.onRendererChange(renderer);
          },
        }, [
          m('option', { value: 'd3' }, 'D3.js (server layout)'),
          m('option', { value: 'gravis' }, 'Gravis (vis-network)'),
          m('option', { value: 'notebook' }, 'Notebook (Static HTML)'),
          m('option', { value: 'system' }, 'System Monitor'),
        ]),
      ]),

      // System renderer controls (only visible when system renderer is active)
      isSystem ? m('div.panel-settings__group', [
        // Definition selector — only show when more than one definition is registered
        SystemDefinitionRegistry.all().length > 1 ? m('div.panel-settings__group', [
          m('span.panel-settings__label-compact', 'System'),
          m('select.panel-settings__select', {
            value: styling.systemId ?? 'moat',
            onchange: (e: Event) => {
              callbacks.onGraphStylingChange({ systemId: (e.target as HTMLSelectElement).value });
            },
          }, SystemDefinitionRegistry.all().map(def =>
            m('option', { value: def.id }, def.name)
          )),
        ]) : null,

        // Mode (demo / live) — always shown for system renderer
        m('span.panel-settings__label-compact', 'Mode'),
        m('div', { style: { display: 'flex', gap: '6px', marginTop: '6px' } }, [
          m('button.panel-settings__option', {
            class: (styling as Record<string, unknown>).systemMode !== 'live' ? 'panel-settings__option--active' : '',
            onclick: () => callbacks.onGraphStylingChange({ systemMode: 'demo' }),
          }, 'Demo'),
          m('button.panel-settings__option', {
            class: (styling as Record<string, unknown>).systemMode === 'live' ? 'panel-settings__option--active' : '',
            onclick: () => callbacks.onGraphStylingChange({ systemMode: 'live' }),
          }, 'Live'),
        ]),
        m('p.panel-settings__hint',
          'Demo replays the derived history on a loop. Live streams over the '
          + "definition's WebSocket — the PAM feed tails auth.log; a derived "
          + 'system replays its clone once, labelled as a replay.'),
      ]) : null,

      // Layout section
      renderSectionHeader('Layout', 'layout'),
      sections.layout ? m('div.panel-graph__section-content', [
        supportsLayout ? m('div.panel-settings__group', [
          m('span.panel-settings__label-compact', 'Algorithm'),
          m('select.panel-settings__select', {
            value: styling.layout,
            onchange: (e: Event) => {
              const value = (e.target as HTMLSelectElement).value;
              callbacks.onGraphStylingChange({ layout: value });
            },
          }, LAYOUT_OPTIONS.map(opt =>
            m('option', { value: opt.value }, opt.label)
          )),
        ]) : m('p.panel-settings__hint', 'Layout algorithm is only available for the D3 renderer.'),

        supportsPhysics ? m('div.panel-settings__group', [
          m('div.panel-settings__toggle-row', [
            m('span.panel-settings__label-compact', 'Physics'),
            m('label.panel-settings__toggle-compact.panel-settings__toggle', [
              m('input[type=checkbox]', {
                checked: styling.enablePhysics,
                onchange: (e: Event) => {
                  const checked = (e.target as HTMLInputElement).checked;
                  callbacks.onGraphStylingChange({ enablePhysics: checked });
                },
              }),
              m('span.panel-settings__toggle-slider'),
            ]),
          ]),
        ]) : null,

        supportsLayout ? m('div.panel-settings__group', [
          m('div.panel-settings__toggle-row', [
            m('span.panel-settings__label-compact', 'Group Outlines'),
            m('label.panel-settings__toggle-compact.panel-settings__toggle', [
              m('input[type=checkbox]', {
                checked: styling.showCompoundGroups !== false,
                onchange: (e: Event) => {
                  const checked = (e.target as HTMLInputElement).checked;
                  callbacks.onGraphStylingChange({ showCompoundGroups: checked });
                },
              }),
              m('span.panel-settings__toggle-slider'),
            ]),
          ]),
        ]) : null,

        supportsPhysics && styling.enablePhysics ? m('div.panel-graph__slider-row', [
          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Repulsion'),
            m('div.panel-settings__slider-group', [
              m('input.panel-settings__slider[type=range]', {
                min: -500, max: -10, step: 10,
                value: styling.chargeStrength,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ chargeStrength: value });
                },
              }),
              m('span.panel-settings__slider-value', `${styling.chargeStrength}px`),
            ]),
          ]),
          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Link Distance'),
            m('div.panel-settings__slider-group', [
              m('input.panel-settings__slider[type=range]', {
                min: 10, max: 300, step: 5,
                value: styling.linkDistance,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ linkDistance: value });
                },
              }),
              m('span.panel-settings__slider-value', `${styling.linkDistance}px`),
            ]),
          ]),
        ]) : null,
      ]) : null,

      // Visual section
      renderSectionHeader('Visual', 'visual'),
      sections.visual ? m('div.panel-graph__section-content', [
        !supportsVisual
          ? m('div.panel-settings__group', [
              renderLabelColorGroup(),
              m('div.panel-settings__help-text', 'Notebook renderer only supports label color.'),
            ])
          : m('div.panel-visual__2col', [
              // Left column: Node settings
              m('div.panel-visual__column', [
                m('div.panel-settings__group', [
                  m('div.panel-settings__toggle-row', [
                    m('span.panel-settings__label-compact', 'Node Labels'),
                    m('label.panel-settings__toggle-compact.panel-settings__toggle', [
                      m('input[type=checkbox]', {
                        checked: styling.showNodeLabels,
                        onchange: (e: Event) => {
                          callbacks.onGraphStylingChange({ showNodeLabels: (e.target as HTMLInputElement).checked });
                        },
                      }),
                      m('span.panel-settings__toggle-slider'),
                    ]),
                  ]),
                  // Per-depth label toggles (override the global setting per depth)
                  m('div.panel-settings__depth-labels', [
                    m('span.panel-settings__sublabel', 'Per depth:'),
                    ...([
                      { depth: 0, label: 'Dir' },
                      { depth: 1, label: 'File' },
                      { depth: 2, label: 'Sym' },
                      { depth: 3, label: 'Sub' },
                    ].map(({ depth, label }) => {
                      const perDepth = styling.showLabelsByDepth ?? {};
                      const isSet = depth in perDepth;
                      const val = isSet ? perDepth[depth] : styling.showNodeLabels;
                      return m('label.panel-settings__depth-label-chip', {
                        title: `Labels for depth ${depth} (${label} nodes)`,
                        class: val ? 'panel-settings__depth-label-chip--on' : 'panel-settings__depth-label-chip--off',
                      }, [
                        m('input[type=checkbox]', {
                          checked: val,
                          onchange: (e: Event) => {
                            const checked = (e.target as HTMLInputElement).checked;
                            const current = { ...(styling.showLabelsByDepth ?? {}) };
                            current[depth] = checked;
                            callbacks.onGraphStylingChange({ showLabelsByDepth: current });
                          },
                        }),
                        label,
                      ]);
                    })),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Node Size'),
                  m('div.panel-settings__slider-group', [
                    m('input.panel-settings__slider[type=range]', {
                      min: 2, max: 30, step: 1, value: styling.nodeSize,
                      oninput: (e: Event) => callbacks.onGraphStylingChange({ nodeSize: parseFloat((e.target as HTMLInputElement).value) }),
                    }),
                    m('span.panel-settings__slider-value', `${styling.nodeSize}px`),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Color By'),
                  m('select.panel-settings__select', {
                    value: styling.colorBy ?? 'auto',
                    title: 'Layer mode colors nodes by Lexicon abstraction layer where present (see docs/architecture.md, Lexicons and the construct vocabulary); Construct mode by what each node is, alike across languages (codecarto/data/constructs.yaml). A node without one keeps its own colour.',
                    onchange: (e: Event) => {
                      callbacks.onGraphStylingChange({ colorBy: (e.target as HTMLSelectElement).value });
                    },
                  }, [
                    m('option', { value: 'auto' }, 'Auto (depth/kind)'),
                    m('option', { value: 'layer' }, 'Abstraction Layer'),
                    m('option', { value: 'construct' }, 'Construct (across languages)'),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Node Opacity'),
                  m('div.panel-settings__slider-group', [
                    m('input.panel-settings__slider[type=range]', {
                      min: 0.1, max: 1, step: 0.05, value: styling.nodeOpacity,
                      oninput: (e: Event) => callbacks.onGraphStylingChange({ nodeOpacity: parseFloat((e.target as HTMLInputElement).value) }),
                    }),
                    m('span.panel-settings__slider-value', `${Math.round(styling.nodeOpacity * 100)}%`),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Border Width'),
                  m('div.panel-settings__slider-group', [
                    m('input.panel-settings__slider[type=range]', {
                      min: 0, max: 8, step: 0.5, value: styling.nodeBorderWidth,
                      oninput: (e: Event) => callbacks.onGraphStylingChange({ nodeBorderWidth: parseFloat((e.target as HTMLInputElement).value) }),
                    }),
                    m('span.panel-settings__slider-value', `${styling.nodeBorderWidth}px`),
                  ]),
                ]),
              ]),
              // Right column: Edge + Label settings
              m('div.panel-visual__column', [
                m('div.panel-settings__group', [
                  m('div.panel-settings__toggle-row', [
                    m('span.panel-settings__label-compact', 'Edge Labels'),
                    m('label.panel-settings__toggle-compact.panel-settings__toggle', [
                      m('input[type=checkbox]', {
                        checked: styling.showEdgeLabels,
                        onchange: (e: Event) => {
                          callbacks.onGraphStylingChange({ showEdgeLabels: (e.target as HTMLInputElement).checked });
                        },
                      }),
                      m('span.panel-settings__toggle-slider'),
                    ]),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Edge Width'),
                  m('div.panel-settings__slider-group', [
                    m('input.panel-settings__slider[type=range]', {
                      min: 0.5, max: 10, step: 0.5, value: styling.edgeWidth,
                      oninput: (e: Event) => callbacks.onGraphStylingChange({ edgeWidth: parseFloat((e.target as HTMLInputElement).value) }),
                    }),
                    m('span.panel-settings__slider-value', `${styling.edgeWidth}px`),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Edge Opacity'),
                  m('div.panel-settings__slider-group', [
                    m('input.panel-settings__slider[type=range]', {
                      min: 0.1, max: 1, step: 0.05, value: styling.edgeOpacity,
                      oninput: (e: Event) => callbacks.onGraphStylingChange({ edgeOpacity: parseFloat((e.target as HTMLInputElement).value) }),
                    }),
                    m('span.panel-settings__slider-value', `${Math.round(styling.edgeOpacity * 100)}%`),
                  ]),
                ]),
                m('div.panel-settings__group', [
                  m('span.panel-settings__label-compact', 'Label Size'),
                  m('div.panel-settings__slider-group', [
                    m('input.panel-settings__slider[type=range]', {
                      min: 6, max: 24, step: 1, value: styling.labelSize,
                      oninput: (e: Event) => callbacks.onGraphStylingChange({ labelSize: parseFloat((e.target as HTMLInputElement).value) }),
                    }),
                    m('span.panel-settings__slider-value', `${styling.labelSize}px`),
                  ]),
                ]),
                renderLabelColorGroup(),
              ]),
            ]),
      ]) : null,

      // Theme section
      renderSectionHeader('Theme', 'theme'),
      sections.theme ? m('div.panel-graph__section-content', [
        m('div.panel-settings__options',
          THEMES.map(theme =>
            m('button.panel-settings__option', {
              class: state.currentTheme === theme.id ? 'panel-settings__option--active' : '',
              onclick: () => handleThemeChange(theme.id),
              style: { borderColor: theme.preview },
            }, theme.label)
          )
        ),
      ]) : null,
    ]);
  };

  // ─── Main render ───────────────────────────────────────────────────────────

  const body = mode === 'open' ? renderOpenTab() : renderGraphTab();

  return m('div.control-panel.control-panel--embedded', [
    m('div.control-panel__body.control-panel__body--open', {
      style: { height: '100%' },
    }, [
      m('div.control-panel__content', [body]),
    ]),
  ]);
}
