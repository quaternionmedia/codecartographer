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

/** The standard envelope every codecarto route answers in. */
interface Envelope {
  status: number;
  message: string;
  results: Record<string, unknown>;
}

export interface TopologyProblem {
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

function isProblem(envelope: Envelope | null): boolean {
  return !envelope || envelope.status >= 400;
}

function asProblem(envelope: Envelope | null, url: string): TopologyProblem {
  const results = (envelope?.results ?? {}) as Partial<TopologyProblem>;
  return {
    problem: results.problem ?? envelope?.message ?? 'the front end could not reach its own server',
    remedy: results.remedy ?? '',
    where: results.where ?? url,
  };
}

export class TopologyService {
  /** Every topology on offer, plus the layouts this server can lay out with. */
  public static async available(
    topologyUrl: string,
  ): Promise<TopologyChoices | TopologyProblem> {
    const url = `${topologyUrl}/available`;
    const envelope = (await RequestHandler.getRequest(url)) as Envelope | null;
    if (isProblem(envelope)) {
      logger.warn('TopologyService.available - harness unreachable');
      return asProblem(envelope, url);
    }
    const results = envelope!.results as unknown as TopologyChoices;
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
    const envelope = (await RequestHandler.getRequest(url)) as Envelope | null;
    if (isProblem(envelope)) {
      return asProblem(envelope, url);
    }
    return envelope!.results;
  }

  /** True when a result is a problem rather than a graph. */
  public static isProblem(found: unknown): found is TopologyProblem {
    return !!found && typeof found === 'object' && 'problem' in found;
  }
}
