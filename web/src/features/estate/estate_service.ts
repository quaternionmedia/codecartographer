/**
 * The estate's seams, read through this window's API.
 *
 * Thin for the reason `TopologyService` is thin: every estate route answers in
 * `GraphData` shape or in a small document, so a view reaches `handlePlotData`
 * like any other plot and inherits the canvas, the extensions and the radial
 * menu. What lives here is the URL, the envelope's four outcomes (through
 * `seam_client`), and the TypeScript shape of each document — nothing that
 * knows what a capability or an overview *is*.
 */

import { RequestHandler } from '../../services/request_handler';
import { instructOutcome, standingOf, type InstructOutcome, type InstructStanding } from './instruct';
import { query, read, type Getter, type SeamOutcome } from './seam_client';

const get: Getter = (url) => RequestHandler.getRequest(url);

/** One row of `/estate/seams`. */
export interface SeamRow {
  name: string;
  role: string;
  ok: boolean;
  where: string;
  schema: number | null;
  detail: string;
  problem: string;
  remedy: string;
  routes: string[];
  /** The panel that draws it, by registry id, or empty when nothing does. */
  panel: string;
}

export interface SeamsDocument {
  seams: SeamRow[];
  live: number;
  caveat: string;
}

/** One declaration of `/capabilities/data`. */
export interface CapabilityRow {
  id: string;
  title: string;
  repo: string;
  phase: string;
  stated_by: string;
  stated_on: string;
  what: string;
  cannot_see: string;
  evidence: Record<string, string>;
}

export interface CapabilitiesDocument {
  source: string;
  rungs: string[];
  capabilities: CapabilityRow[];
  unmeasured: number;
  caveat: string;
}

/** `/overview/data`: dossier's sections, as the terminal prints them. */
export interface OverviewDocument {
  source: string;
  scope: string;
  generated_from: string;
  /** The producer's own stamp, when the seam carries one. */
  generated_at: string;
  /** When the seam file was written -- a fact about the file, not the reading. */
  written_at: string;
  masthead: Array<Record<string, unknown>>;
  sections: Array<{ title?: string; rows?: unknown[]; [key: string]: unknown }>;
  caveat: string;
}

export interface DrawRequest {
  layout?: string;
  paletteId?: string;
  /** Overview only: a seam path other than the default. */
  seam?: string;
  /** Harness interactions only: `rows` for the reading alone, `all` for every node. */
  detail?: string;
}

export class EstateService {
  /** Every seam, probed once by the server. */
  public static seams(estateUrl: string): Promise<SeamOutcome> {
    return read(get, `${estateUrl}/seams`);
  }

  /** What the harness is running and asking, read by the server. */
  public static harnessData(harnessUrl: string): Promise<SeamOutcome> {
    return read(get, `${harnessUrl}/data`);
  }

  /** Whether this window relays an instruction for this reader. */
  public static async instructStanding(harnessUrl: string): Promise<InstructStanding> {
    return standingOf(await RequestHandler.getRequest(`${harnessUrl}/instructions`).catch(() => null));
  }

  /** One instruction a person typed, relayed to the harness by the server. Sent once. */
  public static async instruct(harnessUrl: string, text: string, project: string): Promise<InstructOutcome> {
    const url = `${harnessUrl}/instructions`;
    const body: Record<string, unknown> = project.trim() ? { text, project } : { text };
    return instructOutcome(await RequestHandler.postRequest(url, body).catch(() => null), url);
  }

  /** Who did what at the harness, through which way in, read by the server. */
  public static harnessInteractions(harnessUrl: string): Promise<SeamOutcome> {
    return read(get, `${harnessUrl}/interactions`);
  }

  /** The harness's interactions as a graph, laid out by the server. */
  public static harnessGraph(harnessUrl: string, request: DrawRequest = {}): Promise<SeamOutcome> {
    return read(get, `${harnessUrl}/gjgf${query({
      layout: request.layout, palette_id: request.paletteId, detail: request.detail,
    })}`);
  }

  public static capabilitiesData(capabilitiesUrl: string): Promise<SeamOutcome> {
    return read(get, `${capabilitiesUrl}/data`);
  }

  public static capabilitiesGraph(capabilitiesUrl: string, request: DrawRequest = {}): Promise<SeamOutcome> {
    return read(get, `${capabilitiesUrl}/gjgf${query({ layout: request.layout, palette_id: request.paletteId })}`);
  }

  public static overviewData(overviewUrl: string, seam?: string): Promise<SeamOutcome> {
    return read(get, `${overviewUrl}/data${query({ seam })}`);
  }

  public static overviewGraph(overviewUrl: string, request: DrawRequest = {}): Promise<SeamOutcome> {
    return read(get, `${overviewUrl}/gjgf${query({ layout: request.layout, palette_id: request.paletteId, seam: request.seam })}`);
  }
}
