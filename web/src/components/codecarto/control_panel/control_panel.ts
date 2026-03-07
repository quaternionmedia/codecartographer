import m from 'mithril';
import { animations } from '../../../core/animations';
import { Directory, RawFile } from '../../models/source';
import { DirectoryContent } from '../../qm_comp_lib/directory/directory';
import { SystemDefinitionRegistry } from '../../../features/graph/services/system_renderer';
import './control_panel.css';

export type TabId = 'source' | 'graph';
export type CodeSourceMode = 'upload' | 'repo';
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'system';

export interface Tab {
  id: TabId;
  label: string;
  icon?: string;
  helpText?: string;
}

export interface GraphStylingOptions {
  // Layout Algorithm
  layout: string;

  // Physics Simulation
  enablePhysics: boolean;
  chargeStrength: number;      // in pixels (repulsion force)
  linkDistance: number;         // in pixels (target edge length)

  // Node Appearance
  nodeSize: number;            // in pixels (radius)
  nodeOpacity: number;         // 0.0 to 1.0
  nodeBorderWidth: number;     // in pixels

  // Edge Appearance
  edgeWidth: number;           // in pixels
  edgeOpacity: number;         // 0.0 to 1.0

  // Label Appearance
  showNodeLabels: boolean;
  showEdgeLabels: boolean;
  labelSize: number;           // in pixels (font size)
  labelColor: string;          // hex color

  // Interactions
  interactionProfile: string;  // Profile ID (default, cad, gaming, touch)

  // System renderer — selects which SystemDefinition to render
  systemId?: string;
}

export interface ParserOptions {
  fileExtensions: string[];    // File extensions to parse (e.g., ['.py', '.js'])
}

export interface LoadingProgress {
  loaded: number;
  total: number;
  phase: 'parsing' | 'layout' | 'streaming' | 'done';
}

export interface ControlPanelState {
  isOpen: boolean;
  activeTab: TabId;
  codeSourceMode: CodeSourceMode;
  repoUrl: string;
  currentTheme: string;
  isLoading: boolean;
  statusMessage: string;
  progress: LoadingProgress | null;
  panelHeight: number;
  graphSections: { layout: boolean; visual: boolean; theme: boolean };
  parseDepth: number;  // 1 = files only, 2 = symbols, 3 = sub-symbols
}

export interface ControlPanelCallbacks {
  onDemo: () => void;
  onRepoSubmit: (url: string) => void;
  onRepoFileClick: (url: string) => void;
  onPlotWholeRepo: () => void;
  onFileUpload: (files: FileList) => void;
  onUploadedFileClick: (file: RawFile) => void;
  onPlotAllUploads: () => void;
  onThemeChange: (theme: string) => void;
  onGraphStylingChange: (options: Partial<GraphStylingOptions>) => void;
  onParserOptionsChange: (options: Partial<ParserOptions>) => void;
  onRendererChange: (renderer: GraphRendererType) => void;
  onCParserGithub: (repoUrl: string) => void;
  onFolderExpand: (path: string) => void;
  onExpandAll?: () => Promise<void>;
  onCancel?: () => void;
  onLoadFromCache?: (key: string) => void;
  onEvictCache?: (key: string) => void;
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
  cachedGraphs: CachedEntry[] | null;
}

const TABS: Tab[] = [
  { id: 'source', label: 'Source', icon: '📁', helpText: 'Load code and configure parsing' },
  { id: 'graph',  label: 'Graph',  icon: '◈',  helpText: 'Renderer, layout, visual style and theme' },
];

const LAYOUT_OPTIONS = [
  { value: 'spring_layout', label: 'Spring' },
  { value: 'spectral_layout', label: 'Spectral' },
  { value: 'kamada_kawai_layout', label: 'Kamada-Kawai' },
  { value: 'circular_layout', label: 'Circular' },
  { value: 'spiral_layout', label: 'Spiral' },
  { value: 'random_layout', label: 'Random' },
  { value: 'shell_layout', label: 'Shell' },
  { value: 'sorted_square_layout', label: 'Sorted Square' },
];

const THEMES = [
  { id: 'terminal',  label: 'Terminal',  preview: '#00ff41' },
  { id: 'light',     label: 'Light',     preview: '#2196f3' },
  { id: 'cyberpunk', label: 'Cyberpunk', preview: '#ff00ff' },
  { id: 'ocean',     label: 'Ocean',     preview: '#00d4ff' },
  { id: 'sunset',    label: 'Sunset',    preview: '#ff6b35' },
  { id: 'forest',    label: 'Forest',    preview: '#52b788' },
  { id: 'noir',      label: 'Noir',      preview: '#ffffff' },
  { id: 'candy',     label: 'Candy',     preview: '#ff69eb' },
];

/** Creates the slide-up control panel */
export function ControlPanel(
  state: ControlPanelState,
  callbacks: ControlPanelCallbacks,
  onStateChange: (updates: Partial<ControlPanelState>) => void,
  content: ControlPanelContent
): m.Vnode {

  // Resize drag state
  let isDragging = false;
  let startY = 0;
  let startHeight = 0;

  const updatePanelHeightVar = (element?: HTMLElement) => {
    if (!element) return;
    const totalHeight = Math.ceil(element.getBoundingClientRect().height);
    let effectiveHeight = totalHeight;
    if (!state.isOpen) {
      // When the panel is closed the body may still be mid-transition (CSS
      // `height 0.3s ease-out`). Measuring total − body gives the persistent
      // chrome (handle + tab bar + status bar) regardless of transition state,
      // because both values are read in the same synchronous layout flush.
      const bodyEl = element.querySelector('.control-panel__body') as HTMLElement | null;
      if (bodyEl) {
        effectiveHeight = Math.max(0, totalHeight - Math.ceil(bodyEl.getBoundingClientRect().height));
      }
    }
    document.documentElement.style.setProperty('--control-panel-height', `${effectiveHeight}px`);
  };

  const handleResizeStart = (e: MouseEvent) => {
    if (!state.isOpen) return;
    isDragging = true;
    startY = e.clientY;
    startHeight = state.panelHeight;
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';

    const handleMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const delta = startY - e.clientY;
      const newHeight = Math.max(150, startHeight + delta);
      onStateChange({ panelHeight: newHeight });
    };

    const handleEnd = () => {
      isDragging = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleEnd);
    };

    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleEnd);
  };

  const togglePanel = () => {
    onStateChange({ isOpen: !state.isOpen });
  };

  const setActiveTab = (tabId: TabId) => {
    if (state.activeTab === tabId) {
      onStateChange({ isOpen: !state.isOpen });
    } else {
      onStateChange({ activeTab: tabId, isOpen: true });
    }
  };

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
    if (e.dataTransfer?.files.length) callbacks.onFileUpload(e.dataTransfer.files);
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
    if (input.files?.length) callbacks.onFileUpload(input.files);
  };

  const toggleGraphSection = (section: keyof ControlPanelState['graphSections']) => {
    onStateChange({
      graphSections: {
        ...state.graphSections,
        [section]: !state.graphSections[section],
      },
    });
  };

  // ─── Source Tab (two-column) ───────────────────────────────────────────────

  const renderSourceLeft = () => {
    const hasRepo = !!(content.repoDirectory && content.repoDirectory.size > 0);
    const hasUploads = content.uploadedFiles.length > 0;
    const repoInfo = content.repoDirectory?.info;
    const mode = state.codeSourceMode;
    const activeExts = content.parserOptions.fileExtensions;
    const supportedFiles = activeExts.length > 0
      ? content.uploadedFiles.filter(f => activeExts.some(e => f.name.toLowerCase().endsWith(e.replace(/^\./, ''))))
      : content.uploadedFiles;

    return m('div.panel-source__left', [
      // Mode toggle
      m('div.panel-source__mode-toggle', [
        m('button.panel-source__mode-btn', {
          class: mode === 'upload' ? 'panel-source__mode-btn--active' : '',
          onclick: () => onStateChange({ codeSourceMode: 'upload' }),
        }, [m('span', '↑'), ' Upload']),
        m('button.panel-source__mode-btn', {
          class: mode === 'repo' ? 'panel-source__mode-btn--active' : '',
          onclick: () => onStateChange({ codeSourceMode: 'repo' }),
        }, [m('span', '⬇'), ' Repository']),
      ]),

      // Upload mode
      mode === 'upload' ? m('div.panel-source__upload', [
        m('div.panel-upload__dropzone', {
          ondrop: handleDrop,
          ondragover: handleDragOver,
          ondragleave: handleDragLeave,
          onclick: () => document.getElementById('file-upload-input')?.click(),
        }, [
          m('span.panel-upload__icon', '📁'),
          m('span.panel-upload__text', 'Drop source files here or click to browse'),
          m('input#file-upload-input[type=file][multiple]', {
            style: { display: 'none' },
            attrs: activeExts.length > 0 ? { accept: activeExts.join(',') } : {},
            onchange: handleFileInput,
          }),
        ]),
        hasUploads ? m('div.panel-source__files', [
          m('div.panel-source__files-header', [
            m('span', `${supportedFiles.length} file(s)`),
          ]),
          m('div.panel-source__file-list', [
            content.uploadedFiles.map((file: RawFile) => {
              const isSupported = activeExts.length === 0 ||
                activeExts.some(e => file.name.toLowerCase().endsWith(e.replace(/^\./, '')));
              return m('div.panel-source__file', {
                class: isSupported ? '' : 'panel-source__file--disabled',
                onclick: (e: MouseEvent) => {
                  if (isSupported) {
                    animations.buttonPress(e.currentTarget as Element);
                    callbacks.onUploadedFileClick(file);
                  }
                },
              }, [
                m('span.panel-source__file-icon', isSupported ? '◈' : '📄'),
                m('span.panel-source__file-name', file.name),
                m('span.panel-source__file-size', `${Math.round(file.size / 1024) || '<1'}kb`),
              ]);
            }),
          ]),
        ]) : null,
      ]) : null,

      // Repository mode
      mode === 'repo' ? m('div.panel-source__repo', [
        // URL input
        m('div.panel-source__url-input', [
          m('input[type=text]', {
            placeholder: 'https://github.com/user/repository',
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

        // Recent cached graphs (when no repo loaded and cache exists)
        !hasRepo && content.cachedGraphs && content.cachedGraphs.length > 0
          ? m('div.panel-source__cached', [
              m('span.panel-settings__label-compact', 'Recent'),
              m('div.panel-source__cached-list',
                content.cachedGraphs.slice(0, 5).map(entry => {
                  const ageMins = Math.round(entry.age_seconds / 60);
                  const ageStr = ageMins < 60
                    ? `${ageMins}m ago`
                    : `${Math.round(ageMins / 60)}h ago`;
                  return m('div.panel-source__cached-entry', [
                    m('button.panel-source__cached-chip', {
                      onclick: () => callbacks.onLoadFromCache?.(entry.key),
                      title: `${entry.url}\n${entry.mode} · ${entry.layout}`,
                      disabled: state.isLoading,
                    }, [
                      m('span.panel-source__cached-label', entry.label),
                      m('span.panel-source__cached-age', ageStr),
                    ]),
                    m('button.panel-source__cached-evict', {
                      onclick: () => callbacks.onEvictCache?.(entry.key),
                      title: 'Remove from cache',
                      disabled: state.isLoading,
                    }, '✕'),
                  ]);
                })
              ),
            ])
          : null,

        // Example chips (when no repo loaded)
        !hasRepo ? m('div.panel-source__examples', [
          m('span.panel-settings__label-compact', 'Examples'),
          m('div.panel-source__example-chips', [
            ...[
              { label: 'requests', url: 'https://github.com/psf/requests',    title: 'requests — small repo (~2 MB), full content' },
              { label: 'Flask',    url: 'https://github.com/pallets/flask',   title: 'Flask — medium repo (~8 MB), structure only' },
              { label: 'React',    url: 'https://github.com/facebook/react',  title: 'React — large repo (~25 MB), structure only' },
              { label: 'CPython',  url: 'https://github.com/python/cpython',  title: 'CPython — xlarge repo (~200 MB), shallow root' },
              { label: 'Linux',    url: 'https://github.com/torvalds/linux',  title: 'Linux — xxlarge repo (~1 GB+), shallow root' },
            ].map(ex =>
              m('button.panel-source__example-chip', {
                title: ex.title,
                onclick: (e: MouseEvent) => {
                  animations.buttonPress(e.currentTarget as Element);
                  onStateChange({ repoUrl: ex.url });
                  callbacks.onRepoSubmit(ex.url);
                },
                disabled: state.isLoading,
              }, ex.label)
            ),
          ]),
        ]) : null,

        // Loaded repo — header + tree fills remaining height
        hasRepo ? m('div.panel-source__repo-loaded', [
          m('div.panel-source__repo-header', [
            m('span.panel-source__repo-name', `${repoInfo?.owner}/${repoInfo?.name}`),
            m('span.panel-source__repo-size', `${content.repoDirectory?.size} files`),
          ]),
          content.repoDirectory?.is_partial ? m('div.panel-source__partial-banner', [
            m('span', '⚠ Partial — click a folder ▶ to expand'),
            callbacks.onExpandAll ? m('button.panel-source__expand-all-btn', {
              onclick: (e: MouseEvent) => {
                animations.buttonPress(e.currentTarget as Element);
                callbacks.onExpandAll!();
              },
              title: 'Expand all folders (structure only, no file content)',
            }, '⊞ Expand All') : null,
          ]) : null,
          m('div.panel-source__directory', [
            m(DirectoryContent, {
              folderName: repoInfo ? `${repoInfo.owner}/${repoInfo.name}` : 'Repository',
              folders: content.repoDirectory?.root.folders || [],
              files: content.repoDirectory?.root.files || [],
              onUrlFileClicked: callbacks.onRepoFileClick,
              onFolderExpand: callbacks.onFolderExpand,
              allowedExtensions: content.availableLanguages
                ? Object.values(content.availableLanguages).flat()
                : null,
            }),
          ]),
        ]) : null,
      ]) : null,
    ]);
  };

  const renderSourceRight = () => {
    const hasRepo = !!(content.repoDirectory && content.repoDirectory.size > 0);
    const hasUploads = content.uploadedFiles.length > 0;
    const hasSource = hasRepo || hasUploads;
    const parser = content.parserOptions;

    return m('div.panel-source__right', [
      // File Extensions
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

      // Parse Depth
      m('div.panel-settings__group', [
        m('span.panel-settings__label-compact', 'Parse Depth'),
        m('div.panel-settings__chips',
          [
            { value: 1, label: 'Files' },
            { value: 2, label: 'Symbols' },
            { value: 3, label: 'Deep' },
          ].map(opt =>
            m('button.panel-settings__chip', {
              class: state.parseDepth === opt.value ? 'panel-settings__chip--active' : '',
              onclick: () => onStateChange({ parseDepth: opt.value }),
              title: opt.value === 1 ? 'Depth 1: directory + file nodes'
                   : opt.value === 2 ? 'Depth 2: + top-level symbols (classes, functions)'
                   : 'Depth 3: + sub-symbols (args, fields)',
            }, opt.label)
          )
        ),
      ]),

      m('div.panel-source__divider'),

      m('div.panel-source__spacer'),

      // Plot button (when source loaded) — primary CTA
      hasSource ? m('button.panel-source__plot-primary', {
        onclick: (e: MouseEvent) => {
          animations.buttonPress(e.currentTarget as Element);
          if (hasRepo) callbacks.onPlotWholeRepo();
          else callbacks.onPlotAllUploads();
        },
      }, [m('span', '▶'), m('span', 'Plot')]) : null,

      m('div.panel-source__divider'),

      // Quick Start (when nothing loaded)
      m('div.panel-source__quickstart', [
        m('span.panel-settings__label-compact', 'Quick Start'),
        m('button.panel-settings__button-option', {
          onclick: (e: MouseEvent) => {
            animations.buttonPress(e.currentTarget as Element);
            callbacks.onDemo();
          },
          style: 'width: 100%;',
        }, [m('span', '⚡'), m('span', 'Load Demo')]),
      ]),
    ]);
  };

  const renderSourceTab = () => {
    return m('div.panel-section.panel-source', {
      class: state.activeTab === 'source' ? 'panel-section--active' : '',
    }, [
      m('div.panel-source__2col', [
        renderSourceLeft(),
        renderSourceRight(),
      ]),
    ]);
  };

  // ─── Graph Tab (accordion) ─────────────────────────────────────────────────

  const renderGraphTab = () => {
    const styling = content.graphStyling;
    const selectedRenderer = content.selectedRenderer;
    const isSystem = selectedRenderer === 'system';
    const supportsLayout  = selectedRenderer === 'd3';
    const supportsPhysics = !['notebook', 'system'].includes(selectedRenderer);
    const supportsVisual  = !['notebook', 'system'].includes(selectedRenderer);
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

    return m('div.panel-section.panel-graph', {
      class: state.activeTab === 'graph' ? 'panel-section--active' : '',
    }, [
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
          m('option', { value: 'd3' }, 'D3.js (Force-directed)'),
          m('option', { value: 'gravis' }, 'Gravis (vis-network)'),
          m('option', { value: 'notebook' }, 'Notebook (Static HTML)'),
          m('option', { value: 'system' }, 'System Monitor (PAM)'),
        ]),
      ]),

      // System renderer controls (only visible when system renderer is active)
      isSystem ? m('div.panel-settings__group', [
        // Definition selector — only show when more than one definition is registered
        SystemDefinitionRegistry.all().length > 1 ? m('div.panel-settings__group', [
          m('span.panel-settings__label-compact', 'System'),
          m('select.panel-settings__select', {
            value: styling.systemId ?? 'pam',
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
            class: (styling as Record<string, unknown>).pamMode !== 'live' ? 'panel-settings__option--active' : '',
            onclick: () => callbacks.onGraphStylingChange({ pamMode: 'demo' }),
          }, 'Demo'),
          m('button.panel-settings__option', {
            class: (styling as Record<string, unknown>).pamMode === 'live' ? 'panel-settings__option--active' : '',
            onclick: () => callbacks.onGraphStylingChange({ pamMode: 'live' }),
          }, 'Live'),
        ]),
        m('p.panel-settings__hint', 'Demo always works. Live streams system events via WebSocket.'),
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

  return m('div.control-panel', {
    oncreate: (vnode: m.VnodeDOM) => updatePanelHeightVar(vnode.dom as HTMLElement),
    onupdate: (vnode: m.VnodeDOM) => updatePanelHeightVar(vnode.dom as HTMLElement),
  }, [
    // Resize handle at top (only when open)
    state.isOpen ? m('div.control-panel__resize', {
      onmousedown: handleResizeStart,
    }) : null,

    // Handle bar — icon only
    m('div.control-panel__handle', {
      onclick: togglePanel,
      title: state.isOpen ? 'Close panel' : 'Open panel',
    }, [
      m('span.control-panel__handle-icon', {
        class: state.isOpen ? 'control-panel__handle-icon--open' : '',
      }, '▲'),
    ]),

    // Tab bar
    m('div.control-panel__tabs',
      TABS.map(tab =>
        m('button.control-panel__tab', {
          class: state.activeTab === tab.id ? 'control-panel__tab--active' : '',
          onclick: () => setActiveTab(tab.id),
          title: tab.helpText,
        }, [
          tab.icon ? m('span', tab.icon + ' ') : null,
          tab.label,
        ])
      )
    ),

    // Body (collapsible)
    m('div.control-panel__body', {
      class: state.isOpen ? 'control-panel__body--open' : '',
      style: state.isOpen ? { height: `${state.panelHeight}px` } : { height: '0px' },
    }, [
      m('div.control-panel__content', [
        renderSourceTab(),
        renderGraphTab(),
      ]),
    ]),

    // Status bar
    m('div.control-panel__status', [
      // Progress bar (thin line at top, visible during loading)
      state.isLoading && state.progress
        ? m('div.control-panel__progress-bar', {
            style: {
              width: state.progress.total > 0
                ? `${Math.round((state.progress.loaded / state.progress.total) * 100)}%`
                : '0%',
            },
          })
        : state.isLoading
          ? m('div.control-panel__progress-bar.control-panel__progress-bar--indeterminate')
          : null,

      m('span.control-panel__status-item', [
        m('span.control-panel__status-dot', {
          class: state.isLoading ? 'control-panel__status-dot--warning' : '',
        }),
        state.isLoading && state.progress && state.progress.phase === 'streaming'
          ? `Streaming ${state.progress.loaded}/${state.progress.total} nodes`
          : state.isLoading && state.progress
            ? `${state.progress.phase.charAt(0).toUpperCase() + state.progress.phase.slice(1)}…`
            : state.isLoading
              ? state.statusMessage
              : state.statusMessage || 'Ready',
      ]),

      state.isLoading && callbacks.onCancel
        ? m('button.control-panel__cancel-btn', {
            onclick: callbacks.onCancel,
            title: 'Cancel',
          }, '✕')
        : null,

      m('span.control-panel__status-context',
        `${content.selectedRenderer} · ${state.currentTheme}`
      ),
    ]),
  ]);
}
