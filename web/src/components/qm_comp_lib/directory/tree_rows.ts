/**
 * What each row of the Files panel's tree says and answers to, beside the
 * markup `file.ts`, `files.ts` and `folder.ts` draw.
 *
 * Every row that does something on a click is pressed from the keyboard as a
 * button is (`pressable`): a row was a `div` with only a click handler, so a
 * keyboard never reached a file or a folder, and a screen reader read each as
 * text.
 *
 * No DOM types, so this compiles under `tsconfig.pure.json` and is asserted
 * under `node --test` (`tests/pure/tree-rows.test.mjs`).
 */

import { pressable, type KeyPress } from '../../codecarto/control_panel/pressable.js';

/** What makes a row a button, pressed from the keyboard. */
interface ButtonRow {
  role?: 'button';
  tabindex?: 0;
  onkeydown?: (event: KeyPress) => void;
}

/** The attributes a file's row is drawn with. */
export interface FileRowAttrs extends ButtonRow {
  class: string;
  title: string;
  onclick?: () => void;
  'aria-disabled'?: 'true';
}

/**
 * The row for the file `name`, which `open` draws. A file whose extension is
 * not in `allowedExtensions` (given without or with its dot; null allows
 * every one) is drawn disabled, opens nothing, says so, and is no tab stop.
 * Any other file's row is a button that Enter and Space open, as a click does.
 *
 * The row is one line, and a long name is cut short with an ellipsis, so the
 * row is titled with the whole name, as the uploaded-files list's entries
 * are: two names that differ only past the cut read alike otherwise.
 */
export function fileRow(
  name: string,
  open: () => void,
  allowedExtensions?: string[] | null,
): FileRowAttrs {
  const ext = name.split('.').pop() ?? '';
  const disabled = allowedExtensions != null
    ? !allowedExtensions.some((e) => e.replace(/^\./, '') === ext)
    : false;
  const row = { class: `file__${ext}${disabled ? ' disabled' : ''}`, title: name };
  return disabled
    ? { ...row, role: 'button', 'aria-disabled': 'true' }
    : { ...row, ...pressable(open), onclick: open };
}

/** The attributes a folder's row is drawn with. */
export interface FolderRowAttrs extends ButtonRow {
  title: string;
  onclick?: () => void;
  'aria-expanded'?: 'true' | 'false';
}

/**
 * The row for the folder `name`, open or not, which `toggle` opens and
 * closes; null for a folder with nothing in it to open, which is no button.
 * Any other folder's row is a button that Enter and Space toggle, as a click
 * does, and says whether it is open.
 *
 * It is one line, its name cut short when long, as a file's is, and titled
 * with the whole name for the same reason.
 */
export function folderRow(name: string, open: boolean, toggle: (() => void) | null): FolderRowAttrs {
  if (!toggle) return { title: name };
  return { title: name, ...pressable(toggle), onclick: toggle, 'aria-expanded': open ? 'true' : 'false' };
}

/** The path from the tree's root of the entry `name` in the folder at `folderPath` ('' for the root). */
export function entryPath(folderPath: string, name: string): string {
  return folderPath ? `${folderPath}/${name}` : name;
}

/** The attributes of a file's raw link. */
export interface RawLinkAttrs {
  href: string;
  target: '_blank';
  rel: 'noopener';
  'aria-label': string;
}

/**
 * The raw link for the file at `path`, whose address is `url`, or null when
 * it has none to offer. A file read from disk has a disk path for its url,
 * which no browser page can open, so only a file with a web address (a
 * GitHub file's raw.githubusercontent.com) is offered a raw link.
 *
 * Its text is "raw", beside the file's name; the link is named for the path,
 * as a keyboard or a screen reader meets the links one by one, and each read
 * "raw" with nothing to say which file's contents it opens.
 */
export function rawLink(path: string, url: string): RawLinkAttrs | null {
  if (!/^https?:\/\//.test(url)) return null;
  return { href: url, target: '_blank', rel: 'noopener', 'aria-label': `raw contents of ${path}` };
}
