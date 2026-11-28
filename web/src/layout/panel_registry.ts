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
import type { PanelGroup } from './panel_groups';
import { createGraphPanel } from './panels/graph_panel';
import { createFileTreePanel } from './panels/file_tree_panel';
import { createOpenPanel } from './panels/open_panel';
import { createGraphbasePanel } from './panels/graphbase_panel';
import { createGraphSettingsPanel } from './panels/graph_settings_panel';
import { createTopologyPanel } from './panels/topology_panel';
import { createEstatePanel } from './panels/estate_panel';
import { createCapabilitiesPanel } from './panels/capabilities_panel';
import { createHarnessPanel } from './panels/harness_panel';
import { createInteractionsPanel } from './panels/interactions_panel';
import { createDesignerPanel } from './panels/designer_panel';
import { createComposePanel } from './panels/compose_panel';
import { createOverviewPanel } from './panels/overview_panel';
import { createShowPanel } from './panels/show_panel';
import { createCargoPanel } from './panels/cargo_panel';
import { createChrestomathyPanel } from './panels/chrestomathy_panel';

export type DockPanelId =
  | 'graph' | 'open' | 'file-tree' | 'graphbase-panel' | 'graph-settings-panel'
  // The estate: what is up, and the three seams this window draws.
  | 'estate-panel' | 'topology-panel' | 'capabilities-panel' | 'overview-panel'
  // What the harness is running and asking, read-only.
  | 'harness-panel'
  // Who did what at the harness, through which way in, read-only.
  | 'interactions-panel'
  // Every shape the harness declares, what each needs and which could run, read-only.
  | 'designer-panel'
  // A design composed here and saved to the harness.
  | 'compose-panel'
  // Every family and project the corpus names, drawn: the triplet's graph leg.
  | 'show-panel'
  // Code cartography past one parse: a Rust workspace, and one construct read
  // across every language.
  | 'cargo-panel' | 'chrestomathy-panel';

export interface PanelDefinition {
  readonly id: DockPanelId;
  /** Short label: the "+" menu's list, and an Estate row's "open" button. */
  readonly menuLabel: string;
  /** Whose data it shows, as the "+" menu's heading (`panel_groups.ts`). */
  readonly group: PanelGroup;
  /** What it answers and from which source, in one sentence under its label. */
  readonly answers: string;
  readonly config: ComponentItemConfig;
  readonly overflow: 'hidden' | 'auto';
  readonly mount: (ctx: LayoutContext, element: HTMLElement) => void;
}

const PANEL_DEFINITIONS: readonly PanelDefinition[] = [
  {
    id: 'graph',
    menuLabel: 'Graph',
    group: 'canvas',
    answers: 'The drawing: every other window sends its graph here.',
    config: { type: 'component', componentType: 'graph', id: 'graph', title: '◈ Graph', isClosable: true },
    overflow: 'hidden',
    mount: (ctx, el) => m.mount(el, createGraphPanel(ctx)),
  },
  {
    id: 'open',
    menuLabel: 'Open',
    group: 'code',
    answers: 'Where a graph starts: a repository address, a path, files or an example.',
    config: { type: 'component', componentType: 'open', id: 'open', title: '⬇ Open', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createOpenPanel(ctx)),
  },
  {
    id: 'estate-panel',
    menuLabel: 'Estate',
    group: 'organisation',
    answers: 'Which sources this window reads are answering, and what would bring up the rest.',
    config: { type: 'component', componentType: 'estate-panel', id: 'estate-panel', title: '⌂ Estate', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createEstatePanel(ctx)),
  },
  {
    id: 'topology-panel',
    menuLabel: 'Topology',
    group: 'harness',
    answers: 'The shapes of collaboration the harness knows, each drawn as a graph.',
    config: { type: 'component', componentType: 'topology-panel', id: 'topology-panel', title: '⌁ Topology', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createTopologyPanel(ctx)),
  },
  {
    id: 'harness-panel',
    menuLabel: 'Harness',
    group: 'harness',
    answers: 'What the harness is running, asking and holding as instructions now; an instruction is typed here.',
    config: { type: 'component', componentType: 'harness-panel', id: 'harness-panel', title: '⥁ Harness', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createHarnessPanel(ctx)),
  },
  {
    id: 'interactions-panel',
    menuLabel: 'Interactions',
    group: 'harness',
    answers: 'Who did what at the harness, through which way in, over time.',
    config: { type: 'component', componentType: 'interactions-panel', id: 'interactions-panel', title: '↹ Interactions', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createInteractionsPanel(ctx)),
  },
  {
    id: 'designer-panel',
    menuLabel: 'Designer',
    group: 'harness',
    answers: 'Every shape of work the harness declares: what each needs, and which could run now.',
    config: { type: 'component', componentType: 'designer-panel', id: 'designer-panel', title: '⬡ Designer', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createDesignerPanel(ctx)),
  },
  {
    id: 'compose-panel',
    menuLabel: 'Compose',
    group: 'harness',
    answers: 'A design composed here and saved to the harness, beside the designs it already holds.',
    config: { type: 'component', componentType: 'compose-panel', id: 'compose-panel', title: '✎ Compose', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createComposePanel(ctx)),
  },
  {
    id: 'capabilities-panel',
    menuLabel: 'Capabilities',
    group: 'organisation',
    answers: 'What each named capability has reached, as the registry in the corpus declares it.',
    config: { type: 'component', componentType: 'capabilities-panel', id: 'capabilities-panel', title: '⊚ Capabilities', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createCapabilitiesPanel(ctx)),
  },
  {
    id: 'overview-panel',
    menuLabel: 'Overview',
    group: 'organisation',
    answers: 'Every repository on the host as dossier last synced it, section by section.',
    config: { type: 'component', componentType: 'overview-panel', id: 'overview-panel', title: '▤ Overview', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createOverviewPanel(ctx)),
  },
  {
    id: 'show-panel',
    menuLabel: 'Show',
    group: 'organisation',
    answers: 'Every family and project the corpus names, each opened as a graph.',
    config: { type: 'component', componentType: 'show-panel', id: 'show-panel', title: '❖ Show', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createShowPanel(ctx)),
  },
  {
    id: 'cargo-panel',
    menuLabel: 'Cargo',
    group: 'code',
    answers: 'A Rust workspace on this disk: its crates, targets and last recorded build.',
    config: { type: 'component', componentType: 'cargo-panel', id: 'cargo-panel', title: '⚙ Cargo', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createCargoPanel(ctx)),
  },
  {
    id: 'chrestomathy-panel',
    menuLabel: 'Chrestomathy',
    group: 'code',
    answers: 'One construct set beside itself across every language read here.',
    config: { type: 'component', componentType: 'chrestomathy-panel', id: 'chrestomathy-panel', title: '⇄ Chrestomathy', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createChrestomathyPanel(ctx)),
  },
  {
    id: 'file-tree',
    menuLabel: 'Files',
    group: 'code',
    answers: 'What was opened, by path: the repository tree and the files added.',
    config: { type: 'component', componentType: 'file-tree', id: 'file-tree', title: '◉ Files', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createFileTreePanel(ctx)),
  },
  {
    id: 'graphbase-panel',
    menuLabel: 'Graphbase',
    group: 'code',
    answers: 'Graphs kept earlier in the database: snapshots, bookmarks and history.',
    config: { type: 'component', componentType: 'graphbase-panel', id: 'graphbase-panel', title: '▦ Graphbase', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createGraphbasePanel(ctx)),
  },
  {
    id: 'graph-settings-panel',
    menuLabel: 'Graph Settings',
    group: 'canvas',
    answers: 'How the drawing is laid out, coloured and labelled.',
    config: { type: 'component', componentType: 'graph-settings-panel', id: 'graph-settings-panel', title: 'Graph Settings', isClosable: true },
    overflow: 'auto',
    mount: (ctx, el) => m.mount(el, createGraphSettingsPanel(ctx)),
  },
];

export const PanelRegistry = {
  all: (): readonly PanelDefinition[] => PANEL_DEFINITIONS,
  get: (id: DockPanelId): PanelDefinition | undefined => PANEL_DEFINITIONS.find((p) => p.id === id),
};
