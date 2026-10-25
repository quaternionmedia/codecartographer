/**
 * Code cartography beyond one parse: a Cargo workspace, and the chrestomathy.
 *
 * Thin for the reason `EstateService` is thin. Both routes answer in the
 * estate envelope -- `GraphData` or a document, or a sentence saying why not
 * -- so they go through `seam_client`'s four outcomes and a draw reaches
 * `handlePlotData` like every other plot. What lives here is the URL and the
 * TypeScript shape of each document, nothing that knows what a crate is.
 */

import { RequestHandler } from '../../services/request_handler';
import { query, read, type Getter, type SeamOutcome } from '../estate/seam_client';

const get: Getter = (url) => RequestHandler.getRequest(url);

/** One package of `/cargo/data`. */
export interface CargoPackage {
  name: string;
  version: string;
  manifest: string;
  edition: string;
  member: boolean;
  source: string;
  links: string;
  no_std: string;
  targets: Array<{ name: string; kinds: string[]; src: string; declared: boolean }>;
  dependencies: Array<{
    name: string;
    kind: string;
    req: string;
    optional: boolean;
    platform: string;
    source: string;
    version: string;
  }>;
  features: Record<string, string[]>;
  resolved_features: string[];
  memory_maps: string[];
}

/** One document the reading looked for under `target/codecarto/`. */
export interface CargoDocumentState {
  name: string;
  path: string;
  present: boolean;
  generated_at: string;
  age_seconds: number | null;
  stale: boolean;
  used: boolean;
  problem: string;
}

export interface CargoDocument {
  root: string;
  engine: string;
  packages: CargoPackage[];
  documents: CargoDocumentState[];
  diagnostics: Array<{ level: string; message: string; package: string; target: string; file: string; line: number }>;
  build_success: boolean | null;
  firmware: {
    build_targets: string[];
    runners: Record<string, string>;
    linker_scripts: string[];
    memory_maps: string[];
    config: string;
  };
  notes: string[];
  caveat: string;
}

export interface CargoDrawRequest {
  path: string;
  layout?: string;
  paletteId?: string;
  features?: boolean;
  transitive?: boolean;
}

/** `/lexicon/constructs`: the index a Chrestomathy panel chooses from. */
export interface ConstructIndex {
  constructs: Array<{ id: string; name: string; gloss: string; facet: boolean; languages: string[] }>;
  languages: string[];
  source: string;
  caveat: string;
}

/** A token as a lexicon places it. */
export interface TokenContext {
  kind: string;
  layer_ordinal: number;
  layer_name: string;
  group: string;
  role: string;
  since: string;
}

/** `/lexicon/chrestomathy/{construct}`: one construct across languages. */
export interface ChrestomathyDocument {
  construct: { id: string; name: string; gloss: string; facet: boolean; look: { shape: string; color: string } | null };
  languages: Array<{
    language: string;
    display_name: string;
    has_lexicon: boolean;
    tokens: Array<{ token: string; contexts: TokenContext[] }>;
    kinds: string[];
    carried_by: string[];
    note: string;
  }>;
  source: string;
  caveat: string;
}

/** One construct a graph's nodes are: in which languages, and which nodes. */
export interface CensusRow {
  id: string;
  name: string;
  gloss: string;
  facet: boolean;
  look: { shape: string; color: string } | null;
  count: number;
  languages: Array<{ language: string; display_name: string; count: number }>;
  ids: string[];
}

/** `/lexicon/chrestomathy/census`: the chrestomathy of the graph on the canvas. */
export interface CensusDocument {
  nodes: number;
  constructs: CensusRow[];
  facets: CensusRow[];
  /** The walk's own folders (`directory`) and files (`file`). */
  walk: Array<{ kind: string; count: number }>;
  /** Kinds the vocabulary lists as no construct, each with its reason. */
  not_constructs: Array<{ language: string; display_name: string; kind: string; count: number; reason: string }>;
  unplaced: Array<{ language: string; display_name: string; kind: string; count: number }>;
  outside: Array<{ language: string; count: number }>;
  /** Stamps naming a construct or facet the vocabulary does not hold. */
  unknown: Array<{ construct: string; count: number; ids: string[] }>;
  unlabelled: number;
  source: string;
  caveat: string;
}

const flag = (value: boolean | undefined): string | undefined => (value ? 'true' : undefined);

export class CartographyService {
  public static cargoData(cargoUrl: string, path: string): Promise<SeamOutcome> {
    return read(get, `${cargoUrl}/data${query({ path })}`);
  }

  public static cargoGraph(cargoUrl: string, request: CargoDrawRequest): Promise<SeamOutcome> {
    return read(get, `${cargoUrl}/gjgf${query({
      path: request.path,
      layout: request.layout,
      palette_id: request.paletteId,
      features: flag(request.features),
      transitive: flag(request.transitive),
    })}`);
  }

  public static constructs(lexiconUrl: string): Promise<SeamOutcome> {
    return read(get, `${lexiconUrl}/constructs`);
  }

  public static chrestomathy(lexiconUrl: string, construct: string): Promise<SeamOutcome> {
    return read(get, `${lexiconUrl}/chrestomathy/${encodeURIComponent(construct)}`);
  }

  /** Read a graph's nodes as the constructs they are. A POST: the graph is the question. */
  public static census(lexiconUrl: string, nodes: ReadonlyArray<Record<string, unknown>>): Promise<SeamOutcome> {
    return read((url) => RequestHandler.postRequest(url, { nodes }), `${lexiconUrl}/chrestomathy/census`);
  }

  public static chrestomathyGraph(lexiconUrl: string, construct: string, layout?: string): Promise<SeamOutcome> {
    return read(get, `${lexiconUrl}/chrestomathy/${encodeURIComponent(construct)}/gjgf${query({ layout })}`);
  }
}
