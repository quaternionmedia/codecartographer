/**
 * PanelRegistry
 *
 * Single source of truth for every dockable Golden Layout panel: its GL
 * component config, display title, and Mithril mount function. Generalizes
 * what used to be a fixed DOCK_PANEL_CONFIGS map (in layout_context.ts) plus
 * five duplicated registerComponentFactoryFunction calls (in
 * golden_layout_shell.ts) into one list, so a new panel is a registration
 * here rather than an edit in three files — the same pattern already used
 * by ParserRegistry (backend) and the D3/Gravis/Notebook renderer registry
 * (frontend) elsewhere in this codebase.
 *
 * See ADR 0005 (docs/adr/) for why this generalization exists.
 */

import m from 'mithril';
import type { ComponentItemConfig } from 'golden-layout';

import type { LayoutContext } from './layout_context';
import { createGraphPanel } from './panels/graph_panel';
import { createFileTreePanel } from './panels/file_tree_panel';
import { createUploadPanel } from './panels/upload_panel';
import { createRepoPanel } from './panels/repo_panel';
import { createGraphSettingsPanel } from './panels/graph_settings_panel';
import { createActionsPanel } from './panels/actions_panel';

export type DockPanelId = 'graph' | 'file-tree' | 'upload-panel' | 'repo-panel' | 'graph-settings-panel' | 'plotbar';

export interface PanelDefinition {
  readonly id: DockPanelId;
  /** Short label for menus (add-window list, restore buttons). */
  readonly menuLabel: string;
  readonly config: ComponentItemConfig;
  readonly overflow: 'hidden' | 'auto';
  readonly mount: (ctx: LayoutContext, element: HTMLElement) => void;
}

const PANEL_DEFINITIONS: readonly PanelDefinition[] = [
  {
    id: 'graph',
    menuLabel: 'Graph',
    config: { type: 'component', componentType: 'graph', id: 'graph', title: '◈ Graph', isClosable: true },
    overflow: 'hidden',
    mount: (ctx, el) => m.mount(el, createGraphPanel(ctx)),
  },
  {
    id: 'file-tree',
    menuLabel: 'Files',
    config: { type: 'component', componentType: 'file-tree', id: 'file-tree', title: '◉ Files', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createFileTreePanel(ctx)),
  },
  {
    id: 'upload-panel',
    menuLabel: 'Upload',
    config: { type: 'component', componentType: 'upload-panel', id: 'upload-panel', title: '↑ Upload', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createUploadPanel(ctx)),
  },
  {
    id: 'repo-panel',
    menuLabel: 'Repository',
    config: { type: 'component', componentType: 'repo-panel', id: 'repo-panel', title: '⬇ Repository', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createRepoPanel(ctx)),
  },
  {
    id: 'graph-settings-panel',
    menuLabel: 'Graph Settings',
    config: { type: 'component', componentType: 'graph-settings-panel', id: 'graph-settings-panel', title: 'Graph Settings', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createGraphSettingsPanel(ctx)),
  },
  {
    id: 'plotbar',
    menuLabel: 'Actions',
    config: { type: 'component', componentType: 'plotbar', id: 'plotbar', title: '▶ Actions', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createActionsPanel(ctx)),
  },
];

export const PanelRegistry = {
  all: (): readonly PanelDefinition[] => PANEL_DEFINITIONS,
  get: (id: DockPanelId): PanelDefinition | undefined => PANEL_DEFINITIONS.find((p) => p.id === id),
};
