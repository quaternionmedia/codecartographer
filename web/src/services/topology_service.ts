/**
 * TopologyService
 *
 * The harness's flows, fetched as ordinary graph data.
 *
 * WHY THIS IS THIN. `/topology/gjgf` already answers in `GraphData` shape, so a
 * topology reaches `handlePlotData` like any other plot and inherits this app's
 * renderer, styling, extensions and radial menu. This service exists to build
 * the URL and to unwrap the standard envelope — nothing here knows what a
 * topology *is*, which is the point: if it did, the graph feature would need to
 * know too.
 *
 * WHAT IS DIFFERENT ABOUT A TOPOLOGY, AND IT IS ONLY THIS. An edge may carry no
 * measurement at all. `metadata.unmeasured` counts those, and `metadata.caveat`
 * is the sentence a reader needs before believing the shape. Both ride in the
 * graph metadata rather than being recomputed here, because the side that
 * measured is the side that should say.
 *
 * THE HARNESS IS A SEPARATE PROCESS and is often not running. That is reported
 * as a `problem` with a `remedy` — the command that starts it — rather than as
 * an empty graph, which would look like an answer.
 */

import { logger } from '../core/logger';
import { RequestHandler } from './request_handler';

/**
 * **`RequestHandler` ALREADY UNWRAPS THE ENVELOPE.** `handleResponse` returns
 * `responseData.results`, not `{status, message, results}` — so a service that
 * reads `.results` off what it is handed gets `undefined` and throws on the
 * next property access. This one did, the throw was swallowed by the caller's
 * `catch`, and the panel sat on "asking the harness…" forever with a perfectly
 * successful 200 in the network log.
 *
 * The lesson is smaller than the bug: read the layer you are building on.
 * Everything below takes the *inner* document, because that is what arrives.
 */

export interface TopologyProblem {
  /** Present only when the harness could not be reached. */
  unreachable: true;
  /** What is wrong, in a sentence. */
  problem: string;
  /** What the reader can do about it. Empty when there is nothing they could. */
  remedy: string;
  /** The URL that was tried, so a wrong base is visible. */
  where: string;
}

export interface TopologyChoice {
  topology: string;
  caption: string;
  status: string;
  boxes: number;
  arrows: number;
}

export interface TopologyChoices {
  topologies: TopologyChoice[];
  layouts: string[];
  encoding: Array<Record<string, unknown>>;
}

export interface TopologyRequest {
  /** A named topology from the harness's own vocabulary. */
  kind?: string;
  /** A project to read the archive for. Wins over `kind` when both are given,
   *  because asking about a subject is the more specific request. */
  subject?: string;
  layout?: string;
  paletteId?: string;
}

/**
 * Whether a result says the harness could not be reached.
 *
 * **A `null` COUNTS.** `RequestHandler` returns `null` when the request itself
 * failed — the API down rather than the harness — and a caller that only
 * checked for `unreachable` would treat that as a graph.
 */
function problemOf(found: unknown, url: string): TopologyProblem | null {
  if (found === null || found === undefined) {
    return {
      unreachable: true,
      problem: 'the front end could not reach its own API',
      remedy: 'check that the codecarto server is running',
      where: url,
    };
  }
  if (typeof found === 'object' && 'unreachable' in (found as object)) {
    return found as TopologyProblem;
  }
  return null;
}

export class TopologyService {
  /** Every topology on offer, plus the layouts this server can lay out with. */
  public static async available(
    topologyUrl: string,
  ): Promise<TopologyChoices | TopologyProblem> {
    const url = `${topologyUrl}/available`;
    const found = await RequestHandler.getRequest(url);
    const problem = problemOf(found, url);
    if (problem) {
      logger.warn('TopologyService.available - ' + problem.problem);
      return problem;
    }
    const results = found as TopologyChoices;
    return {
      topologies: results.topologies ?? [],
      layouts: results.layouts ?? [],
      encoding: results.encoding ?? [],
    };
  }

  /**
   * One topology as graph data, ready for `handlePlotData`.
   *
   * Returns the same shape `PlotService` does on success, so the caller does
   * not branch on where a graph came from.
   */
  public static async load(
    topologyUrl: string,
    request: TopologyRequest = {},
  ): Promise<unknown | TopologyProblem> {
    const query = new URLSearchParams();
    // Subject wins: asking what the archive says about one project is more
    // specific than asking for a named shape, and sending both would leave the
    // server to guess which was meant.
    if (request.subject) {
      query.set('subject', request.subject);
    } else {
      query.set('kind', request.kind ?? 'delegation');
    }
    if (request.layout) query.set('layout', request.layout);
    if (request.paletteId) query.set('palette_id', request.paletteId);

    const url = `${topologyUrl}/gjgf?${query.toString()}`;
    const found = await RequestHandler.getRequest(url);
    return problemOf(found, url) ?? found;
  }

  /** True when a result says the harness could not be reached. */
  public static isProblem(found: unknown): found is TopologyProblem {
    return !!found && typeof found === 'object' && 'unreachable' in found;
  }
}
