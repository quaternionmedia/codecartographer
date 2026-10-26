/**
 * The Open panel's plots -- added files, the demo, a lexicon -- drawn in the
 * order they were asked for, decided without a browser.
 *
 * **ONLY THE LATEST PLOT ASKED FOR IS DRAWN.** Each takes a ticket, the
 * `Latest` that `cartography_actions.ts` hands its reads and draws, and draws
 * its answer only while it holds the latest: press Plot over added files, then
 * Load Demo, and a slow `/parse/unified` answer arriving after the demo
 * replaced it. A stream draws by another way and drops what is still out
 * (`supersede`). A superseded plot's failure is dropped with it, so it cannot
 * say "Error" over the plot that replaced it.
 *
 * `actions.ts` is application code no test build compiles, which is why the
 * order lives here, against a canvas `PlotActions` supplies and `node --test`
 * fakes.
 */

// `.js`, so the build `node --test` reads resolves it as the bundler does.
import { Latest } from '../features/cartography/cartography_actions.js';

/** A plot's place in the order asked: true while no plot has been asked for since. */
export type PlotTicket = () => boolean;

export class LatestPlot {
  private readonly latest = new Latest();

  /** `clear` empties the canvas for a plot asked for now. */
  constructor(private readonly clear: () => void) {}

  /** A plot drawn another way has begun: an answer still out is dropped. */
  supersede(): void {
    this.latest.take();
  }

  /**
   * The latest place, taken now, for a drawing that asks for something else
   * before it plots -- a project's showgraph reads its views first. An answer
   * still out is dropped from here, and `plot` handed this draws only while no
   * plot has been asked for since. True while it is still the latest.
   */
  ticket(): PlotTicket {
    return this.latest.take();
  }

  /**
   * Clear the canvas, ask, and `show` the answer unless another plot was asked
   * for since. Resolves true when it was shown, false when it was dropped; a
   * failure is thrown only while this plot is still the latest. Handed a
   * `current` overtaken already, it neither clears nor asks.
   */
  async plot<T>(
    ask: () => Promise<T>,
    show: (answer: T) => void,
    current: PlotTicket = this.latest.take(),
  ): Promise<boolean> {
    if (!current()) return false;
    this.clear();
    let answer: T;
    try {
      answer = await ask();
    } catch (error) {
      if (!current()) return false;
      throw error;
    }
    if (!current()) return false;
    show(answer);
    return true;
  }
}
