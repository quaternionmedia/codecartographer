/**
 * What the Cargo and Chrestomathy panels do when they read and draw, decided
 * without a browser.
 *
 * **WHY THIS IS NOT IN `PlotActions`.** Every defect these panels shipped with
 * was a matter of order, not of any one answer: a reading merged into the one
 * before it, a late answer to an earlier request shown over a newer one, a
 * relayout drawing whatever was chosen since rather than what was drawn, one
 * problem field shared by two requests so that either cleared the other's, a
 * retry that re-read after a failed draw. Order is a sequence, a sequence is a
 * test, and `actions.ts` is application code no test build compiles -- the
 * lesson `legend_marks.ts` is built on. So the sequencing lives here, against a
 * host and reads that `PlotActions` supplies and `node --test` fakes.
 */

// `.js`, so the build `node --test` reads resolves it as the bundler does.
import { isProblem } from '../estate/seam_client.js';
import type { SeamOutcome, SeamProblem } from '../estate/seam_client.js';

/** The state these actions read. */
export interface CartographyState {
  cargoPath: string;
  constructChosen: string;
  constructIndex: unknown;
  constructIndexProblem?: SeamProblem | null;
  chrestomathyReading: { construct: { id: string } } | null;
  chrestomathyProblem: SeamProblem | null;
}

/** What these actions need from the application. */
export interface CartographyHost {
  readonly state: CartographyState;
  /** A mergerino patch: an object deep-merges, a function replaces. */
  update(patch: Record<string, unknown>): void;
  redraw(): void;
  /** Empty the canvas, as every draw does first. */
  clear(): void;
  /** Put a graph on the canvas (`handlePlotData`). */
  plot(document: unknown): void;
  /** The backend's name for the layout chosen now. */
  layout(): string;
}

/** The routes these actions read, as `CartographyService` reaches them. */
export interface CartographyReads {
  cargoData(path: string): Promise<SeamOutcome>;
  cargoGraph(request: CargoDraw & { layout: string }): Promise<SeamOutcome>;
  constructs(): Promise<SeamOutcome>;
  chrestomathy(construct: string): Promise<SeamOutcome>;
  chrestomathyGraph(construct: string, layout: string): Promise<SeamOutcome>;
}

export interface CargoDraw {
  path: string;
  features?: boolean;
  transitive?: boolean;
}

/** A draw as it was asked for. Resolves true when a graph reached the canvas. */
export type Draw = () => Promise<boolean>;

/** What "try again" repeats: the request whose problem is shown. */
export type Retry = { op: 'read'; run: () => Promise<void> } | { op: 'draw'; run: Draw };

/** Hands out tickets; a ticket is current until a later one is taken. */
export class Latest {
  private issued = 0;

  take(): () => boolean {
    const mine = ++this.issued;
    return () => mine === this.issued;
  }
}

/**
 * A patch setting each field to exactly the value given.
 *
 * **A FUNCTION PATCH, BECAUSE AN OBJECT ONE MERGES.** mergerino deep-merges an
 * object into the value already there, so `{ cargoReading: b }` kept every key
 * of the reading before it that `b` did not name -- workspace A's
 * `firmware.runners` survived into B's reading, shown under B as its runner.
 * A function's result replaces, as `StateController.replaceGraphData` already
 * relies on.
 */
export function replacing(fields: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, () => value]));
}

/** Put a document in one field and clear the other, or the reverse. */
export function settlePatch(found: SeamOutcome, readingField: string, problemField: string): Record<string, unknown> {
  return isProblem(found)
    ? replacing({ [readingField]: null, [problemField]: found.problem })
    : replacing({ [readingField]: found.document, [problemField]: null });
}

/**
 * What the construct choice shows: the list, why it could not be read, or that
 * it is being read. The list's problem is its own field, so "reading the
 * vocabulary…" is never what a failed read leaves behind.
 */
export function vocabularyShown(state: CartographyState): 'list' | 'problem' | 'pending' {
  if (state.constructIndex) return 'list';
  return state.constructIndexProblem ? 'problem' : 'pending';
}

/**
 * The panels' reads and draws.
 *
 * **ONLY THE LATEST REQUEST OF EACH KIND IS SHOWN.** Each read and each draw
 * takes a ticket and settles only while it holds the latest: read A then B,
 * and A answering last showed A's crates while "draw" drew B.
 *
 * **A DRAW IS CAPTURED WHEN IT IS ASKED FOR.** `cargoDraw` and
 * `chrestomathyDraw` return the draw of what the panel shows now, which is
 * what `plotWith` remembers and a layout change re-runs; read from state when
 * it ran, choosing another construct after drawing one made a relayout draw
 * the new choice.
 *
 * **"TRY AGAIN" REPEATS WHAT FAILED.** The problem a panel shows is the last
 * request's, read or draw, and `cargoRetry`/`chrestomathyRetry` hand back that
 * request; a draw that failed is drawn again, not the workspace re-read. A draw
 * resolves true only when a graph reached the canvas, so the panel brings the
 * canvas forward then and not over its own problem.
 */
export class CartographyActions {
  private readonly cargoReads = new Latest();
  private readonly cargoDraws = new Latest();
  private readonly indexReads = new Latest();
  private readonly chrestomathyReads = new Latest();
  private readonly chrestomathyDraws = new Latest();
  private cargoFailed: Retry | null = null;
  private chrestomathyFailed: Retry | null = null;

  constructor(
    private readonly host: CartographyHost,
    private readonly reads: CartographyReads,
  ) {}

  // --- Cargo -------------------------------------------------------------------

  /**
   * What the server reads at a workspace path. Draws nothing; runs nothing.
   * `cargoPath` becomes the path of what is shown when it settles, so the draw
   * button draws the workspace the panel lists.
   */
  async loadCargoReading(path: string): Promise<void> {
    const latest = this.cargoReads.take();
    const found = await this.reads.cargoData(path);
    if (!latest()) return;
    this.cargoFailed = isProblem(found) ? { op: 'read', run: () => this.loadCargoReading(path) } : null;
    this.settle({ ...settlePatch(found, 'cargoReading', 'cargoProblem'), ...replacing({ cargoPath: path }) });
  }

  /** The draw of the workspace shown now, with these options. */
  cargoDraw(options: { features?: boolean; transitive?: boolean } = {}): Draw {
    const request: CargoDraw = { path: this.host.state.cargoPath, ...options };
    const draw: Draw = () => this.drawCargo(request, draw);
    return draw;
  }

  private async drawCargo(request: CargoDraw, draw: Draw): Promise<boolean> {
    const latest = this.cargoDraws.take();
    this.host.clear();
    const found = await this.reads.cargoGraph({ ...request, layout: this.host.layout() });
    if (!latest()) return false;
    this.cargoFailed = isProblem(found) ? { op: 'draw', run: draw } : null;
    return this.drawn(found, 'cargoProblem');
  }

  /** What "try again" on the Cargo panel's problem repeats, or null with none shown. */
  cargoRetry(): Retry | null {
    return this.cargoFailed;
  }

  // --- the chrestomathy --------------------------------------------------------

  /**
   * Every construct, for the panel's choice. Its problem is its own
   * (`constructIndexProblem`): sharing the reading's, a reading that succeeded
   * cleared it and left "reading the vocabulary…" with nothing to retry, and
   * a list that loaded never cleared it.
   */
  async loadConstructIndex(): Promise<void> {
    const latest = this.indexReads.take();
    const found = await this.reads.constructs();
    if (!latest()) return;
    this.settle(settlePatch(found, 'constructIndex', 'constructIndexProblem'));
  }

  /** One construct across languages, for the panel's table. */
  async loadChrestomathy(construct: string): Promise<void> {
    const latest = this.chrestomathyReads.take();
    // At once: the choice is the select's value, and it shows what was picked.
    this.host.update(replacing({ constructChosen: construct }));
    const found = await this.reads.chrestomathy(construct);
    if (!latest()) return;
    this.chrestomathyFailed = isProblem(found)
      ? { op: 'read', run: () => this.loadChrestomathy(construct) }
      : null;
    this.settle(settlePatch(found, 'chrestomathyReading', 'chrestomathyProblem'));
  }

  /** The draw of the construct whose table is shown now, or null when none is. */
  chrestomathyDraw(): Draw | null {
    const construct = this.host.state.chrestomathyReading?.construct.id;
    if (!construct) return null;
    const draw: Draw = () => this.drawChrestomathy(construct, draw);
    return draw;
  }

  private async drawChrestomathy(construct: string, draw: Draw): Promise<boolean> {
    const latest = this.chrestomathyDraws.take();
    this.host.clear();
    const found = await this.reads.chrestomathyGraph(construct, this.host.layout());
    if (!latest()) return false;
    this.chrestomathyFailed = isProblem(found) ? { op: 'draw', run: draw } : null;
    return this.drawn(found, 'chrestomathyProblem');
  }

  /** What "try again" on the Chrestomathy panel's problem repeats, or null with none shown. */
  chrestomathyRetry(): Retry | null {
    return this.chrestomathyFailed;
  }

  // --- shared ------------------------------------------------------------------

  private settle(patch: Record<string, unknown>): void {
    this.host.update(patch);
    this.host.redraw();
  }

  private drawn(found: SeamOutcome, problemField: string): boolean {
    if (isProblem(found)) {
      this.host.update(replacing({ [problemField]: found.problem }));
      this.host.redraw();
      return false;
    }
    this.host.update(replacing({ [problemField]: null }));
    this.host.plot(found.document);
    this.host.redraw();
    return true;
  }
}
