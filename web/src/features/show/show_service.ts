/**
 * The showgraphs, read through this window's API.
 *
 * Thin for the reason `EstateService` is thin: `/show/*` answers in `GraphData`
 * shape or in a small document, so a showgraph reaches `handlePlotData` like
 * any other plot. What lives here is the URL, the envelope's four outcomes
 * (through `seam_client`), and the shape of each document -- nothing that
 * knows what a family *is*. That is the corpus's, read by the server.
 */

import { RequestHandler } from '../../services/request_handler';
import { query, read, type Getter, type SeamOutcome } from '../estate/seam_client';
import type { ShowAddress } from './show_address';

const get: Getter = (url) => RequestHandler.getRequest(url);

export interface ShowFamilyRow {
  name: string;
  drives: string;
  within: string | null;
  subfamilies: string[];
  members: number;
  all_members: number;
  hue: string | null;
}

export interface ShowProjectRow {
  name: string;
  families: string[];
  /** `null` when git could not say -- unknown, never "not adopted". */
  governed: boolean | null;
  phase: string;
  description: string;
  views: string[];
}

export interface ShowProvenance {
  source: string;
  commit: string | null;
  schema: number | null;
  generated_at: string;
  /** Whether `CODECARTO_CORPUS` pointed the window away from the pin. */
  overridden: boolean;
}

export interface ShowSubjectsDocument {
  families: ShowFamilyRow[];
  projects: ShowProjectRow[];
  unstated: number;
  private: number;
  provenance: ShowProvenance;
  notes: string[];
}

export interface ShowViewState {
  available: boolean;
  problem?: string;
  remedy?: string;
  url?: string;
  depth?: number;
  components?: number;
}

export interface ShowViewsDocument {
  name: string;
  estate: ShowViewState;
  code: ShowViewState;
  system: ShowViewState;
}

export class ShowService {
  public static subjects(showUrl: string): Promise<SeamOutcome> {
    return read(get, `${showUrl}/subjects`);
  }

  public static views(showUrl: string, project: string): Promise<SeamOutcome> {
    return read(get, `${showUrl}/project/${encodeURIComponent(project)}/views`);
  }

  /** The estate graph for an address: the index, a family, or a project. */
  public static graph(showUrl: string, address: ShowAddress,
                      request: { layout?: string; paletteId?: string } = {}): Promise<SeamOutcome> {
    // The index's code view is the whole corpus: every family, each
    // project's code in it.
    const path = address.kind === 'index'
      ? (address.view === 'code' ? 'corpus' : 'index')
      : `${address.kind}/${encodeURIComponent(address.name)}`;
    return read(get, `${showUrl}/${path}/gjgf${query({ layout: request.layout, palette_id: request.paletteId })}`);
  }
}
