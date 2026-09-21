/**
 * One way to read a seam, and four things that can come back.
 *
 * WHY THIS EXISTS. `TopologyService` learned, one bug at a time, that a seam
 * answers in four distinguishable ways and that collapsing any two of them sends
 * a reader to the wrong place: the window's own API not answering (`null` from
 * the request handler), the seam unreachable (a 200 whose results say
 * `unreachable`), the seam present and unreadable (`unreadable` — a file the pin
 * predates, a schema this window does not know), and a document. Capabilities
 * and Overview needed the same four, and a second copy of the lesson would drift
 * from the first.
 *
 * PURE ON PURPOSE. `classify` takes what the request handler returned and the
 * URL it was asked for, and decides. It touches no DOM and makes no request, so
 * `web/tests/pure/seam-client.test.mjs` exercises every branch under node with
 * no browser. The request itself is one line in `read`, and the getter is
 * injectable for the same reason.
 *
 * THE ENVELOPE IS ALREADY UNWRAPPED. `RequestHandler.handleResponse` returns
 * `results`, not `{status, message, results}` — a service reading `.results` off
 * what it is handed gets `undefined`, and the topology panel once sat on
 * "asking…" forever for exactly that. Everything here takes the inner document.
 */

export type SeamOutcome =
  | { kind: 'api-down'; problem: SeamProblem }
  | { kind: 'unreachable'; problem: SeamProblem }
  | { kind: 'unreadable'; problem: SeamProblem }
  | { kind: 'ok'; document: Record<string, unknown> };

/** What a reader is told when nothing was drawn. The same shape every seam's
 *  router puts in its `results`, plus which of the two absences it was. */
export interface SeamProblem {
  /** `api-down` is this window's own server; the other two are the seam's. */
  kind: 'api-down' | 'unreachable' | 'unreadable';
  /** What is wrong, in a sentence. */
  problem: string;
  /** What the reader can do about it. Empty when there is nothing they could. */
  remedy: string;
  /** The URL or path that was tried, so a wrong base is visible. */
  where: string;
}

export type Getter = (url: string) => Promise<unknown>;

/** Decide what a request handler's answer was. */
export function classify(found: unknown, url: string): SeamOutcome {
  if (found === null || found === undefined) {
    return {
      kind: 'api-down',
      problem: {
        kind: 'api-down',
        problem: 'the front end could not reach its own API',
        remedy: 'check that the codecarto server is running',
        where: url,
      },
    };
  }
  if (typeof found !== 'object') {
    return {
      kind: 'unreadable',
      problem: {
        kind: 'unreadable',
        problem: 'the API answered with something that is not a document',
        remedy: '',
        where: url,
      },
    };
  }
  const doc = found as Record<string, unknown>;
  if (doc.unreachable === true || doc.unreadable === true) {
    const kind = doc.unreachable === true ? 'unreachable' : 'unreadable';
    return {
      kind,
      problem: {
        kind,
        problem: String(doc.problem ?? ''),
        remedy: String(doc.remedy ?? ''),
        where: String(doc.where ?? url),
      },
    };
  }
  return { kind: 'ok', document: doc };
}

/** True when an outcome is one of the three absences. */
export function isProblem(outcome: SeamOutcome): outcome is Exclude<SeamOutcome, { kind: 'ok' }> {
  return outcome.kind !== 'ok';
}

/**
 * Read one seam document through the window's API.
 *
 * A throw inside the getter is an `api-down` with the error's own words as the
 * remedy: a rejected promise that a panel's `catch` swallows is a pending state
 * nothing exits, which is the failure the topology panel shipped with.
 */
export async function read(get: Getter, url: string): Promise<SeamOutcome> {
  let found: unknown;
  try {
    found = await get(url);
  } catch (error) {
    return {
      kind: 'api-down',
      problem: {
        kind: 'api-down',
        problem: 'the front end failed while reading the answer',
        remedy: String((error as Error)?.message ?? error),
        where: url,
      },
    };
  }
  return classify(found, url);
}

/**
 * Build a query string from the defined entries only.
 *
 * Hand-encoded rather than `URLSearchParams`, which is a DOM type: this file is
 * compiled in the browser-free `tsconfig.pure.json` build so its branches can
 * be asserted under node, and a DOM name here would be a compile error there —
 * which is the point of that build.
 */
export function query(params: Record<string, string | number | undefined | null>): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
  }
  return parts.length ? `?${parts.join('&')}` : '';
}
