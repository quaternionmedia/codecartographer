/**
 * What each row of the Files panel's tree says and answers to, beside the
 * markup `file.ts` draws.
 *
 * No DOM types, so this compiles under `tsconfig.pure.json` and is asserted
 * under `node --test` (`tests/pure/tree-rows.test.mjs`).
 */

/** The attributes a file's row is drawn with. */
export interface FileRowAttrs {
  class: string;
  title: string;
  onclick?: () => void;
}

/**
 * The row for the file `name`, which `open` draws. A file whose extension is
 * not in `allowedExtensions` (given without or with its dot; null allows
 * every one) is drawn disabled, and opens nothing.
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
  return {
    class: `file__${ext}${disabled ? ' disabled' : ''}`,
    title: name,
    onclick: disabled ? undefined : open,
  };
}
