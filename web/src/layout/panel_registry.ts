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
 * See governance/qm/adr/DRAFT-panel-registry-and-add-window-menu.md for why
 * this generalization exists.
 */

import m from 'mithril';
import type { ComponentItemConfig } from 'golden-layout';

import type { LayoutContext } from './layout_context';
import { createGraphPanel } from './panels/graph_panel';
import { createFileTreePanel } from './panels/file_tree_panel';
import { createOpenPanel } from './panels/open_panel';
import { createGraphbasePanel } from './panels/graphbase_panel';
import { createGraphSettingsPanel } from './panels/graph_settings_panel';
import { createTopologyPanel } from './panels/topology_panel';
import { createEstatePanel } from './panels/estate_panel';
import { createCapabilitiesPanel } from './panels/capabilities_panel';
import { createOverviewPanel } from './panels/overview_panel';
import { createCargoPanel } from './panels/cargo_panel';
import { createChrestomathyPanel } from './panels/chrestomathy_panel';

export type DockPanelId =
  | 'graph' | 'open' | 'file-tree' | 'graphbase-panel' | 'graph-settings-panel'
  // The estate: what is up, and the three seams this window draws.
  | 'estate-panel' | 'topology-panel' | 'capabilities-panel' | 'overview-panel'
  // Code cartography past one parse: a Rust workspace, and one construct read
  // across every language.
  | 'cargo-panel' | 'chrestomathy-panel';

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
    id: 'open',
    menuLabel: 'Open',
    config: { type: 'component', componentType: 'open', id: 'open', title: '⬇ Open', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createOpenPanel(ctx)),
  },
  {
    id: 'estate-panel',
    menuLabel: 'Estate',
    config: { type: 'component', componentType: 'estate-panel', id: 'estate-panel', title: '⌂ Estate', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createEstatePanel(ctx)),
  },
  {
    id: 'topology-panel',
    menuLabel: 'Topology',
    config: { type: 'component', componentType: 'topology-panel', id: 'topology-panel', title: '⌁ Topology', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createTopologyPanel(ctx)),
  },
  {
    id: 'capabilities-panel',
    menuLabel: 'Capabilities',
    config: { type: 'component', componentType: 'capabilities-panel', id: 'capabilities-panel', title: '⊚ Capabilities', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createCapabilitiesPanel(ctx)),
  },
  {
    id: 'overview-panel',
    menuLabel: 'Overview',
    config: { type: 'component', componentType: 'overview-panel', id: 'overview-panel', title: '▤ Overview', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createOverviewPanel(ctx)),
  },
  {
    id: 'cargo-panel',
    menuLabel: 'Cargo',
    config: { type: 'component', componentType: 'cargo-panel', id: 'cargo-panel', title: '⚙ Cargo', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createCargoPanel(ctx)),
  },
  {
    id: 'chrestomathy-panel',
    menuLabel: 'Chrestomathy',
    config: { type: 'component', componentType: 'chrestomathy-panel', id: 'chrestomathy-panel', title: '⇄ Chrestomathy', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createChrestomathyPanel(ctx)),
  },
  {
    id: 'file-tree',
    menuLabel: 'Files',
    config: { type: 'component', componentType: 'file-tree', id: 'file-tree', title: '◉ Files', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createFileTreePanel(ctx)),
  },
  {
    id: 'graphbase-panel',
    menuLabel: 'Graphbase',
    config: { type: 'component', componentType: 'graphbase-panel', id: 'graphbase-panel', title: '▦ Graphbase', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createGraphbasePanel(ctx)),
  },
  {
    id: 'graph-settings-panel',
    menuLabel: 'Graph Settings',
    config: { type: 'component', componentType: 'graph-settings-panel', id: 'graph-settings-panel', title: 'Graph Settings', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createGraphSettingsPanel(ctx)),
  },
];

export const PanelRegistry = {
  all: (): readonly PanelDefinition[] => PANEL_DEFINITIONS,
  get: (id: DockPanelId): PanelDefinition | undefined => PANEL_DEFINITIONS.find((p) => p.id === id),
};
