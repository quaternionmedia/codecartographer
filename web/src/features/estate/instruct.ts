/**
 * What the window says about an instruction a person typed in it.
 *
 * The window's API relays the text to the harness, which records it and runs
 * nothing. Four things can come back and each sends a reader somewhere else:
 * this window's own API not answering, the harness not answering, the
 * instruction refused (by the harness, or because the window does not relay
 * for this request), and the harness's row. `instructOutcome` tells them
 * apart from the unwrapped `results`, as `seam_client.classify` does for a
 * read.
 *
 * Pure: no DOM and no request, so `web/tests/pure/instruct.test.mjs` runs
 * every branch under node.
 */

export interface InstructProblem {
  kind: 'api-down' | 'unreachable' | 'refused';
  /** What is wrong, in a sentence. */
  problem: string;
  /** What the reader can do about it, or empty. */
  remedy: string;
  /** The URL that was tried. */
  where: string;
}

export type InstructOutcome =
  | InstructProblem
  | { kind: 'recorded'; instruction: Record<string, unknown>; where: string };

/** Whether the window relays an instruction for this reader, and if not, why. */
export interface InstructStanding {
  available: boolean;
  problem: string;
  remedy: string;
}

const text = (value: unknown): string => (value === null || value === undefined ? '' : String(value));

const API_DOWN = 'the front end could not reach its own API';
const API_REMEDY = 'check that the codecarto server is running';

/** Decide what the API's answer to a posted instruction was. */
export function instructOutcome(found: unknown, url: string): InstructOutcome {
  if (found === null || found === undefined || typeof found !== 'object') {
    return { kind: 'api-down', problem: API_DOWN, remedy: API_REMEDY, where: url };
  }
  const doc = found as Record<string, unknown>;
  const instruction = doc.instruction;
  if (doc.recorded === true && instruction !== null && typeof instruction === 'object') {
    return { kind: 'recorded', instruction: instruction as Record<string, unknown>, where: text(doc.where) || url };
  }
  return {
    kind: doc.unreachable === true ? 'unreachable' : 'refused',
    problem: text(doc.problem) || 'the instruction was not recorded, and the answer did not say why',
    remedy: text(doc.remedy),
    where: text(doc.where) || url,
  };
}

/** Read the API's answer to "is an instruction taken here". No answer is a no. */
export function standingOf(found: unknown): InstructStanding {
  if (found === null || found === undefined || typeof found !== 'object') {
    return { available: false, problem: API_DOWN, remedy: API_REMEDY };
  }
  const doc = found as Record<string, unknown>;
  return {
    available: doc.available === true,
    problem: text(doc.problem),
    remedy: text(doc.remedy),
  };
}

/** Whether a press would send: there is text, and no send is under way. */
export function sendable(typed: string, sending: boolean): boolean {
  return !sending && typed.trim().length > 0;
}

/** The harness's row for a recorded instruction, as one sentence. */
export function recordedShown(instruction: Record<string, unknown>): string {
  const id = text(instruction.id) || 'an instruction with no id';
  const project = text(instruction.project);
  const status = text(instruction.status);
  const forWhat = project ? `for ${project}` : 'with no project resolved';
  return `the harness recorded ${id} ${forWhat}${status ? `, status ${status}` : ''}. Nothing ran.`;
}
