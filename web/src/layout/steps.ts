/**
 * The four steps from opening source to reading its graph, as one flow.
 *
 * Open -> Browse -> Tune -> Read. They are numbered on a rail in the header,
 * the walkthrough card is a page per step, and each step owns a group of the
 * dock's windows: entering it brings that group forward, and a window the
 * reader chooses -- by its tab, from the "+" menu, or by maximising its stack
 * -- says which step they are on. The canvas alone is Read however it was
 * maximised, and restored from Read it is the step before (`layout_context.ts`).
 *
 * The shape is alfred's stage flow (Source -> Edit -> Render -> Deliver, in
 * `website/src/Stages.js` and `website/src/layout/registry.js` there): a
 * numbered rail that is always shown, a stage's panels brought forward
 * whether or not it is the stage already chosen, a closed one opened again,
 * and a tab chosen naming its stage. Two things differ, each for a reason.
 * alfred keeps its stage in the address, so a reload lands where the person
 * left off; here a reload has nothing drawn, so it opens on step 1, and the
 * address keeps holding nothing but a Show drawing (`docs/ui.md`). And
 * reading a graph needs nothing but the graph, so step 4 maximises the
 * canvas and hides every other window, where a stage there only brings its
 * panels forward.
 *
 * No Golden Layout or Mithril import, so this compiles under
 * `tsconfig.pure.json` and is asserted under `node --test`; the dock is
 * reached through `StepDock`, which `layout_context.ts` implements.
 */

export type StepId = 'open' | 'browse' | 'tune' | 'read';

export interface Step {
  readonly id: StepId;
  /** Its name on the rail, after its number. */
  readonly label: string;
  /** The rail's tooltip, and what Next says is coming. */
  readonly hint: string;
  /** The walkthrough card's page for it. */
  readonly icon: string;
  readonly title: string;
  readonly body: string;
  /**
   * Every window the step owns: choosing one of these says the reader is on
   * it. Each registered window belongs to exactly one step.
   */
  readonly owns: readonly string[];
  /**
   * The windows entering the step brings forward, the one it is about first:
   * that one is in front where two share a stack, and has the focus. A
   * closed one is opened again.
   */
  readonly forward: readonly string[];
  /** Whether entering it maximises its first window's stack, hiding the rest. */
  readonly alone: boolean;
}

export const STEPS: readonly Step[] = [
  {
    id: 'open',
    label: 'Open',
    hint: 'Choose a repository or an example',
    icon: '📁',
    title: 'Open a source',
    body: 'Everything starts in the Open panel: paste a GitHub URL or a local path and press → Fetch, pick an example, or press ⚡ Load Demo; files and folders from disk are added in the Files panel. ▶ Plot at its foot draws what is open, and Cancel stops it. The Estate panel and the + menu draw the estate instead. Drag a tab to move a window; + adds one.',
    // Every window that starts a drawing: the code map's sources, the
    // estate's seams, and the graphs kept in Graphbase.
    owns: [
      'open', 'estate-panel', 'show-panel', 'topology-panel', 'capabilities-panel',
      'overview-panel', 'cargo-panel', 'graphbase-panel',
    ],
    // The canvas comes forward on every step but its own stack's: whatever a
    // step does is drawn there, and the dock keeps it in view.
    forward: ['open', 'graph'],
    alone: false,
  },
  {
    id: 'browse',
    label: 'Browse',
    hint: 'Add files or a folder, walk the tree, draw one file alone',
    icon: '◉',
    title: 'Browse what was opened',
    body: 'The Files panel adds files or a whole folder from disk, dropped on its box or chosen, and holds the loaded repository\'s tree and the added files. Click a folder to open it and a file to draw that file alone; ⊞ Expand All reads every folder.',
    owns: ['file-tree'],
    forward: ['file-tree', 'graph'],
    alone: false,
  },
  {
    id: 'tune',
    label: 'Tune',
    hint: 'The renderer, the layout and the look',
    icon: '⚙',
    title: 'Tune the drawing',
    body: 'Graph Settings chooses the renderer and the layout algorithm, the node size, labels and colour, and the theme. A new layout draws the graph again.',
    owns: ['graph-settings-panel'],
    forward: ['graph-settings-panel', 'graph'],
    alone: false,
  },
  {
    id: 'read',
    label: 'Read',
    hint: 'The graph alone: zoom, hover, the ring',
    icon: '◈',
    title: 'Read the graph',
    body: 'The canvas fills the window. Scroll to zoom, drag to pan, hover a node for details and double-click one for its source. Right-click opens the ring, and the legend at the bottom left keys the colours. Restore, or another step, brings the windows back.',
    // Chrestomathy reads whatever is drawn as the constructs it is.
    owns: ['graph', 'chrestomathy-panel'],
    forward: ['graph'],
    alone: true,
  },
];

/** The step a page opens on: nothing is drawn yet, so the first. */
export const FIRST_STEP: StepId = 'open';

/** Step `id`, or the first where it names none. */
export function stepNamed(id: string | null | undefined): Step {
  return STEPS.find((s) => s.id === id) ?? STEPS[0];
}

/** Its number on the rail, from 1. */
export function stepNumber(id: StepId): number {
  return STEPS.findIndex((s) => s.id === id) + 1;
}

/** The step after `id`, or null after the last. */
export function nextStep(id: StepId): Step | null {
  return STEPS[stepNumber(id)] ?? null;
}

/** The step before `id`, or null before the first. */
export function previousStep(id: StepId): Step | null {
  return STEPS[stepNumber(id) - 2] ?? null;
}

/** The step that owns window `panelId`, or null for a window no step owns. */
export function stepOfPanel(panelId: string): StepId | null {
  return STEPS.find((s) => s.owns.includes(panelId))?.id ?? null;
}

/** As much of the dock as entering a step asks of it. */
export interface StepDock {
  /** Bring window `panelId` to the front of its stack, opening it when it is closed. */
  show(panelId: string, focus: boolean): void;
  /** Maximise the stack holding window `panelId`, unless it is already. */
  maximise(panelId: string): void;
  /** Restore a maximised stack, if there is one. */
  restore(): void;
}

/**
 * Bring step `id`'s windows forward in `dock`.
 *
 * **WHATEVER WAS MAXIMISED IS RESTORED FIRST.** A maximised stack hides every
 * other, and a window brought to the front of a stack nobody can see has not
 * been shown -- step 4's canvas, or a stack the reader maximised themselves.
 * Step 4 maximises the canvas again after.
 *
 * **THE WINDOW THE STEP IS ABOUT IS SHOWN LAST.** Where two of a step's
 * windows share a stack, only one can be in front, and the last one shown is;
 * so `forward` is shown in reverse, and only its first takes the focus.
 */
export function enterStep(id: StepId, dock: StepDock): void {
  const step = stepNamed(id);
  dock.restore();
  for (const panelId of [...step.forward].reverse()) dock.show(panelId, panelId === step.forward[0]);
  if (step.alone) dock.maximise(step.forward[0]);
}
