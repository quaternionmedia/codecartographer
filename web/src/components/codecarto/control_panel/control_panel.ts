import m from 'mithril';
import { animate } from 'animejs';
import { animations } from '../../../core/animations';
import { Directory, RawFile } from '../../models/source';
import { DirectoryContent } from '../../qm_comp_lib/directory/directory';
import './control_panel.css';

export type TabId = 'source' | 'parse' | 'layout' | 'visual' | 'theme';
export type CodeSourceMode = 'upload' | 'repo';
export type ParserMode = 'ast' | 'directory' | 'dependencies';
export type GraphRendererType = 'd3' | 'gravis' | 'notebook';

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
}

export interface ParserOptions {
  mode: ParserMode;            // Parser type (ast, directory, dependencies)
  fileExtensions: string[];    // File extensions to parse (e.g., ['.py', '.js'])
}

export interface ControlPanelState {
  isOpen: boolean;
  activeTab: TabId;
  codeSourceMode: CodeSourceMode;
  repoUrl: string;
  currentTheme: string;
  isLoading: boolean;
  statusMessage: string;
  panelHeight: number;
  // Note: graphStyling, parserOptions, selectedRenderer are now in ControlPanelContent
  // They come from cell.state (single source of truth)
}

export interface ControlPanelCallbacks {
  onDemo: () => void;
  onRepoSubmit: (url: string) => void;
  onRepoFileClick: (url: string) => void;
  onPlotWholeRepo: () => void;
  onPlotRepoDeps: () => void;
  onFileUpload: (files: FileList) => void;
  onUploadedFileClick: (file: RawFile) => void;
  onPlotAllUploads: () => void;
  onThemeChange: (theme: string) => void;
  onGraphStylingChange: (options: Partial<GraphStylingOptions>) => void;
  onParserOptionsChange: (options: Partial<ParserOptions>) => void;
  onRendererChange: (renderer: GraphRendererType) => void;
}

export interface ControlPanelContent {
  repoDirectory: Directory | null;
  uploadedFiles: RawFile[];
  // Settings from cell.state (single source of truth)
  graphStyling: GraphStylingOptions;
  parserOptions: ParserOptions;
  selectedRenderer: GraphRendererType;
}

const TABS: Tab[] = [
  { id: 'source', label: '1. Source', icon: '📁', helpText: 'Choose where to get your code' },
  { id: 'parse', label: '2. Parse', icon: '🔍', helpText: 'Define how to analyze the code' },
  { id: 'layout', label: '3. Layout', icon: '◈', helpText: 'Arrange nodes in space' },
  { id: 'visual', label: '4. Visual', icon: '✦', helpText: 'Style the appearance' },
  { id: 'theme', label: '5. Theme', icon: '🎨', helpText: 'Overall color scheme' },
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
  { id: 'terminal', label: 'Terminal', preview: '#00ff41' },
  { id: 'light', label: 'Light', preview: '#2196f3' },
  { id: 'cyberpunk', label: 'Cyberpunk', preview: '#ff00ff' },
  { id: 'ocean', label: 'Ocean', preview: '#00d4ff' },
  { id: 'sunset', label: 'Sunset', preview: '#ff6b35' },
  { id: 'forest', label: 'Forest', preview: '#52b788' },
  { id: 'noir', label: 'Noir', preview: '#ffffff' },
  { id: 'candy', label: 'Candy', preview: '#ff69eb' },
];

const PARSER_MODES = [
  {
    value: 'ast',
    label: 'AST (Code Structure)',
    icon: '🔍',
    description: 'Full Python abstract syntax tree analysis - shows classes, functions, imports, calls'
  },
  {
    value: 'directory',
    label: 'Directory Tree',
    icon: '📁',
    description: 'Filesystem hierarchy - shows folder and file structure'
  },
  {
    value: 'dependencies',
    label: 'Dependencies',
    icon: '◈',
    description: 'Import relationships - shows how files depend on each other'
  },
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
    const height = Math.ceil(element.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--control-panel-height', `${height}px`);
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
      // Remove height limits - allow panel to be any size
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
    const newState = !state.isOpen;
    onStateChange({ isOpen: newState });
  };

  const setActiveTab = (tabId: TabId) => {
    // If clicking the already-active tab, toggle panel open/closed
    if (state.activeTab === tabId) {
      onStateChange({ isOpen: !state.isOpen });
    } else {
      // Switching to a different tab - ensure panel is open
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
    if (e.key === 'Enter') {
      handleRepoSubmit();
    }
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

  // Unified Code tab - combines upload, repository, and demo
  const renderCodeTab = () => {
    const hasRepo = content.repoDirectory && content.repoDirectory.size > 0;
    const hasUploads = content.uploadedFiles.length > 0;
    const repoInfo = content.repoDirectory?.info;
    const mode = state.codeSourceMode;

    // Count files ready for plotting
    const uploadedPythonFiles = content.uploadedFiles.filter(f => f.name.endsWith('.py'));
    const loadedFileCount = hasRepo
      ? content.repoDirectory!.size
      : uploadedPythonFiles.length;

    return m('div.panel-section.panel-source', { class: state.activeTab === 'source' ? 'panel-section--active' : '' }, [
      // Quick Start section
      m('div.panel-source__quickstart', [
        m('span.panel-settings__label-compact', 'Quick Start'),
        m('button.panel-settings__button-option', {
          onclick: (e: MouseEvent) => {
            animations.buttonPress(e.currentTarget as Element);
            // Load demo data - will use current parser mode and renderer
            callbacks.onDemo();
          },
          style: 'width: 100%;'
        }, [
          m('span', '⚡'),
          m('span', 'Load Demo'),
        ]),
      ]),

      // Status feedback
      m('div.panel-source__status', [
        m('span.panel-source__status-indicator', {
          class: loadedFileCount > 0 ? 'panel-source__status-indicator--ready' : '',
        }),
        m('span.panel-source__status-text',
          loadedFileCount > 0
            ? `${loadedFileCount} file(s) ready`
            : mode === 'upload' ? 'Drop Python files or browse' : 'Enter a GitHub URL'
        ),
        // Add plot button when files are ready
        loadedFileCount > 0 ? m('button.panel-source__plot-btn', {
          onclick: (e: MouseEvent) => {
            animations.buttonPress(e.currentTarget as Element);
            if (hasRepo) {
              callbacks.onPlotWholeRepo();
            } else if (hasUploads) {
              callbacks.onPlotAllUploads();
            }
          }
        }, [
          m('span', '▶'),
          m('span', 'Plot'),
        ]) : null,
      ]),

      // Mode toggle (Upload/Repository)
      m('div.panel-source__header-row', [
        // Source mode toggle
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
      ]),
      
      // Upload mode content
      mode === 'upload' ? m('div.panel-source__upload', [
        // Dropzone
        m('div.panel-upload__dropzone', {
          ondrop: handleDrop,
          ondragover: handleDragOver,
          ondragleave: handleDragLeave,
          onclick: () => document.getElementById('file-upload-input')?.click(),
        }, [
          m('span.panel-upload__icon', '📁'),
          m('span.panel-upload__text', 'Drop .py files here or click to browse'),
          m('input#file-upload-input[type=file][multiple][accept=.py]', {
            style: { display: 'none' },
            onchange: handleFileInput,
          }),
        ]),
        
        // Uploaded files list
        hasUploads ? m('div.panel-source__files', [
          m('div.panel-source__files-header', [
            m('span', `${uploadedPythonFiles.length} Python file(s)`),
            uploadedPythonFiles.length > 0 ? m('button', {
              onclick: (e: MouseEvent) => {
                animations.buttonPress(e.currentTarget as Element);
                callbacks.onPlotAllUploads();
              }
            }, '◇ Plot All') : null,
          ]),
          m('div.panel-source__file-list', [
            content.uploadedFiles.map((file: RawFile) => {
              const ext = file.name.split('.').pop() || '';
              const isPython = ext === 'py';
              
              return m('div.panel-source__file', {
                class: isPython ? '' : 'panel-source__file--disabled',
                onclick: (e: MouseEvent) => {
                  if (isPython) {
                    animations.buttonPress(e.currentTarget as Element);
                    callbacks.onUploadedFileClick(file);
                  }
                },
              }, [
                m('span.panel-source__file-icon', isPython ? '🐍' : '📄'),
                m('span.panel-source__file-name', file.name),
                m('span.panel-source__file-size', `${Math.round(file.size / 1024) || '<1'}kb`),
              ]);
            }),
          ]),
        ]) : null,
      ]) : null,
      
      // Repository mode content
      mode === 'repo' ? m('div.panel-source__repo', [
        // URL Input
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
            disabled: !state.repoUrl.trim() || state.isLoading 
          }, state.isLoading ? '...' : '→ Fetch'),
        ]),
        
        // Loaded repository
        hasRepo ? m('div.panel-source__repo-content', [
          m('div.panel-source__repo-header', [
            m('span.panel-source__repo-name', `${repoInfo?.owner}/${repoInfo?.name}`),
            m('span.panel-source__repo-size', `${content.repoDirectory?.size} files`),
          ]),
          m('div.panel-source__repo-actions', [
            m('button', { 
              onclick: (e: MouseEvent) => {
                animations.buttonPress(e.currentTarget as Element);
                callbacks.onPlotWholeRepo();
              }
            }, '◇ Directory Tree'),
            m('button', { 
              onclick: (e: MouseEvent) => {
                animations.buttonPress(e.currentTarget as Element);
                callbacks.onPlotRepoDeps();
              }
            }, '◈ Dependencies'),
          ]),
          // Directory tree (compact)
          m('div.panel-source__directory', [
            m(DirectoryContent, {
              folderName: repoInfo ? `${repoInfo.owner}/${repoInfo.name}` : 'Repository',
              folders: content.repoDirectory?.root.folders || [],
              files: content.repoDirectory?.root.files || [],
              onUrlFileClicked: callbacks.onRepoFileClick,
            }),
          ]),
        ]) : m('p.panel-source__empty', 
          'Enter a GitHub repository URL to fetch and visualize its structure.'
        ),
      ]) : null,
    ]);
  };

  // Parser Tab - Parser mode and file extensions
  const renderParserTab = () => {
    const parser = content.parserOptions;

    return m('div.panel-section.panel-parse', { class: state.activeTab === 'parse' ? 'panel-section--active' : '' }, [
      m('div.panel-settings__group', [
        m('span.panel-settings__label-compact', 'Parse Mode'),
        m('div.panel-settings__button-group',
          PARSER_MODES.map(mode =>
            m('button.panel-settings__button-option', {
              class: parser.mode === mode.value ? 'panel-settings__button-option--active' : '',
              onclick: () => callbacks.onParserOptionsChange({ mode: mode.value as ParserMode }),
              title: mode.description,
            }, [
              m('span', mode.icon),
              m('span', mode.label),
            ])
          )
        ),
      ]),

      m('div.panel-settings__group', [
        m('span.panel-settings__label-compact', 'File Extensions'),
        m('input.panel-settings__input-compact[type=text]', {
          value: parser.fileExtensions.join(', '),
          placeholder: '.py, .js, .ts',
          onchange: (e: Event) => {
            const value = (e.target as HTMLInputElement).value;
            const extensions = value.split(',').map(ext => ext.trim()).filter(ext => ext.length > 0);
            callbacks.onParserOptionsChange({ fileExtensions: extensions });
          },
        }),
      ]),
    ]);
  };

  // Layout Tab - Layout algorithms and physics
  const renderLayoutTab = () => {
    const styling = content.graphStyling;
    const selectedRenderer = content.selectedRenderer;

    return m('div.panel-section.panel-layout', { class: state.activeTab === 'layout' ? 'panel-section--active' : '' }, [
      // Renderer selection (TOP - this is the first choice)
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
        ]),
      ]),

      // Layout algorithm (only show if NOT notebook renderer)
      selectedRenderer !== 'notebook' ? m('div.panel-settings__group', [
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
      ]) : null,

      // Physics settings (only show if NOT notebook renderer)
      selectedRenderer !== 'notebook' ? m('div.panel-settings__group', [
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

      // Repulsion force slider (only if physics enabled AND not notebook)
      selectedRenderer !== 'notebook' && styling.enablePhysics ? m('div.panel-settings__group', [
        m('span.panel-settings__label-compact', 'Repulsion Force'),
        m('div.panel-settings__slider-group', [
          m('input.panel-settings__slider[type=range]', {
            min: -500,
            max: -10,
            step: 10,
            value: styling.chargeStrength,
            oninput: (e: Event) => {
              const value = parseFloat((e.target as HTMLInputElement).value);
              callbacks.onGraphStylingChange({ chargeStrength: value });
            },
          }),
          m('span.panel-settings__slider-value', `${styling.chargeStrength}px`),
        ]),
      ]) : null,

      // Link distance slider (only if physics enabled AND not notebook)
      selectedRenderer !== 'notebook' && styling.enablePhysics ? m('div.panel-settings__group', [
        m('span.panel-settings__label-compact', 'Link Distance'),
        m('div.panel-settings__slider-group', [
          m('input.panel-settings__slider[type=range]', {
            min: 10,
            max: 300,
            step: 5,
            value: styling.linkDistance,
            oninput: (e: Event) => {
              const value = parseFloat((e.target as HTMLInputElement).value);
              callbacks.onGraphStylingChange({ linkDistance: value });
            },
          }),
          m('span.panel-settings__slider-value', `${styling.linkDistance}px`),
        ]),
      ]) : null,
    ]);
  };

  // Style Tab - Visual appearance (nodes, edges, labels)
  const renderStyleTab = () => {
    const styling = content.graphStyling;

    return m('div.panel-section.panel-visual', { class: state.activeTab === 'visual' ? 'panel-section--active' : '' }, [
      // 2-column grid layout for nodes/edges/labels
      m('div.panel-visual__2col', [
        // Left column: Node settings
        m('div.panel-visual__column', [
          m('div.panel-settings__group', [
            m('div.panel-settings__toggle-row', [
              m('span.panel-settings__label-compact', 'Node Labels'),
              m('label.panel-settings__toggle-compact.panel-settings__toggle', [
                m('input[type=checkbox]', {
                  checked: styling.showNodeLabels,
                  onchange: (e: Event) => {
                    const checked = (e.target as HTMLInputElement).checked;
                    callbacks.onGraphStylingChange({ showNodeLabels: checked });
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
                min: 2,
                max: 30,
                step: 1,
                value: styling.nodeSize,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ nodeSize: value });
                },
              }),
              m('span.panel-settings__slider-value', `${styling.nodeSize}px`),
            ]),
          ]),

          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Node Opacity'),
            m('div.panel-settings__slider-group', [
              m('input.panel-settings__slider[type=range]', {
                min: 0.1,
                max: 1,
                step: 0.05,
                value: styling.nodeOpacity,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ nodeOpacity: value });
                },
              }),
              m('span.panel-settings__slider-value', `${Math.round(styling.nodeOpacity * 100)}%`),
            ]),
          ]),

          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Border Width'),
            m('div.panel-settings__slider-group', [
              m('input.panel-settings__slider[type=range]', {
                min: 0,
                max: 8,
                step: 0.5,
                value: styling.nodeBorderWidth,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ nodeBorderWidth: value });
                },
              }),
              m('span.panel-settings__slider-value', `${styling.nodeBorderWidth}px`),
            ]),
          ]),
        ]),

        // Right column: Edge and Label settings
        m('div.panel-visual__column', [
          m('div.panel-settings__group', [
            m('div.panel-settings__toggle-row', [
              m('span.panel-settings__label-compact', 'Edge Labels'),
              m('label.panel-settings__toggle-compact.panel-settings__toggle', [
                m('input[type=checkbox]', {
                  checked: styling.showEdgeLabels,
                  onchange: (e: Event) => {
                    const checked = (e.target as HTMLInputElement).checked;
                    callbacks.onGraphStylingChange({ showEdgeLabels: checked });
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
                min: 0.5,
                max: 10,
                step: 0.5,
                value: styling.edgeWidth,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ edgeWidth: value });
                },
              }),
              m('span.panel-settings__slider-value', `${styling.edgeWidth}px`),
            ]),
          ]),

          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Edge Opacity'),
            m('div.panel-settings__slider-group', [
              m('input.panel-settings__slider[type=range]', {
                min: 0.1,
                max: 1,
                step: 0.05,
                value: styling.edgeOpacity,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ edgeOpacity: value });
                },
              }),
              m('span.panel-settings__slider-value', `${Math.round(styling.edgeOpacity * 100)}%`),
            ]),
          ]),

          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Label Size'),
            m('div.panel-settings__slider-group', [
              m('input.panel-settings__slider[type=range]', {
                min: 6,
                max: 24,
                step: 1,
                value: styling.labelSize,
                oninput: (e: Event) => {
                  const value = parseFloat((e.target as HTMLInputElement).value);
                  callbacks.onGraphStylingChange({ labelSize: value });
                },
              }),
              m('span.panel-settings__slider-value', `${styling.labelSize}px`),
            ]),
          ]),

          m('div.panel-settings__group', [
            m('span.panel-settings__label-compact', 'Label Color'),
            m('input.panel-settings__color[type=color]', {
              value: styling.labelColor,
              oninput: (e: Event) => {
                const value = (e.target as HTMLInputElement).value;
                callbacks.onGraphStylingChange({ labelColor: value });
              },
            }),
          ]),
        ]),
      ]),
    ]);
  };

  // Theme Tab - Color themes
  const renderThemeTab = () => {
    return m('div.panel-section.panel-theme', { class: state.activeTab === 'theme' ? 'panel-section--active' : '' }, [
      m('div.panel-settings__group', [
        m('span.panel-settings__label', 'Color Theme'),
        m('div.panel-settings__options',
          THEMES.map(theme =>
            m('button.panel-settings__option', {
              class: state.currentTheme === theme.id ? 'panel-settings__option--active' : '',
              onclick: () => handleThemeChange(theme.id),
              style: { borderColor: theme.preview },
            }, theme.label)
          )
        ),
      ]),

      m('div.panel-settings__group', { style: { marginTop: 'var(--spacing-lg)' } }, [
        m('span.panel-settings__label', 'About'),
        m('p', { style: { color: 'var(--c-font-muted)', fontSize: '0.85em', margin: 0 } },
          'Code Cartographer — Visualize code architecture and dependencies'
        ),
      ]),
    ]);
  };

  return m('div.control-panel', {
    oncreate: (vnode: m.VnodeDOM) => updatePanelHeightVar(vnode.dom as HTMLElement),
    onupdate: (vnode: m.VnodeDOM) => updatePanelHeightVar(vnode.dom as HTMLElement),
  }, [
    // Resize handle at top (only when open)
    state.isOpen ? m('div.control-panel__resize', {
      onmousedown: handleResizeStart,
    }) : null,
    
    // Handle bar to toggle open/close
    m('div.control-panel__handle', { onclick: togglePanel }, [
      m('span.control-panel__handle-label', state.isOpen ? 'Close Panel' : 'Open Panel'),
      m('span.control-panel__handle-icon', { 
        class: state.isOpen ? 'control-panel__handle-icon--open' : '' 
      }, '▲'),
    ]),
    
    // Tabs
    m('div.control-panel__tabs',
      TABS.map(tab =>
        m('button.control-panel__tab', {
          class: state.activeTab === tab.id ? 'control-panel__tab--active' : '',
          onclick: () => setActiveTab(tab.id),
        }, [
          tab.icon ? m('span', tab.icon + ' ') : null,
          tab.label,
        ])
      )
    ),
    
    // Body (collapsible) - use inline style for dynamic height
    m('div.control-panel__body', {
      class: state.isOpen ? 'control-panel__body--open' : '',
      style: state.isOpen ? { height: `${state.panelHeight}px` } : { height: '0px' },
    }, [
      m('div.control-panel__content', [
        renderCodeTab(),
        renderParserTab(),
        renderLayoutTab(),
        renderStyleTab(),
        renderThemeTab(),
      ]),
    ]),
    
    // Status bar
    m('div.control-panel__status', [
      m('span.control-panel__status-item', [
        m('span.control-panel__status-dot', { 
          class: state.isLoading ? 'control-panel__status-dot--warning' : '' 
        }),
        state.isLoading ? state.statusMessage : 'Ready',
      ]),
      m('span.control-panel__status-item', `Theme: ${state.currentTheme}`),
    ]),
  ]);
}
