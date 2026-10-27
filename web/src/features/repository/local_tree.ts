/**
 * Files added from disk, a folder of them included: which are kept, and the
 * tree they are drawn as.
 *
 * **A FOLDER IS DRAWN AS A FOLDER.** Added files were drawn as one flat folder,
 * which was right for a handful dropped at once and wrong for a folder: its
 * `src/` and `tests/` were lost, and two `__init__.py` from different folders
 * were one file. Each added file carries the path it had under what was added
 * (`url`, its `webkitRelativePath` or the dropped entry's path), and the tree is
 * built from those paths.
 *
 * **A FOLDER HOLDS MORE THAN SOURCE.** A project folder carries its version
 * control, its dependencies and its build output, which are no source of its
 * own and can be thousands of files. Those folders are left out, and so is any
 * file larger than the parse would read, or of an extension the parse options
 * leave out when they name any.
 *
 * PURE ON PURPOSE: `web/tests/pure/local-tree.test.mjs` runs it under node.
 */

/** Folders that hold no source of the project's own, left out of an added folder. */
export const SKIPPED_FOLDERS: readonly string[] = [
  '.git', 'node_modules', '__pycache__', '.venv', 'venv', '.tox', '.mypy_cache', '.pytest_cache', 'target',
];

/** The largest file read from disk, in bytes: past this a file is data, not source. */
export const LOCAL_FILE_LIMIT = 2_000_000;

/** A file as the tree needs it: its name, size, contents and its path under what was added. */
export interface LocalFile {
  name: string;
  size: number;
  raw: string;
  url: string;
}

export interface LocalFolder {
  name: string;
  size: number;
  files: LocalFile[];
  folders: LocalFolder[];
}

/** The path's parts, with any leading `./` or `/` and Windows separators settled. */
export function pathParts(path: string): string[] {
  return path.replace(/\\/g, '/').split('/').filter((part) => part && part !== '.');
}

/**
 * Whether a file at `path`, of `size` bytes, is read: not under a folder in
 * `SKIPPED_FOLDERS`, not past `LOCAL_FILE_LIMIT`, and of one of `extensions`
 * when any are given (`.py`, or `py`).
 */
export function keptLocal(path: string, size: number, extensions: readonly string[] = []): boolean {
  const parts = pathParts(path);
  if (parts.length === 0) return false;
  if (parts.slice(0, -1).some((folder) => SKIPPED_FOLDERS.includes(folder))) return false;
  if (size > LOCAL_FILE_LIMIT) return false;
  if (extensions.length === 0) return true;
  const name = parts[parts.length - 1].toLowerCase();
  return extensions.some((ext) => {
    const wanted = ext.toLowerCase().replace(/^\.?/, '.');
    return name.endsWith(wanted);
  });
}

/**
 * The added files as a tree named `root`: each file in the folder its path
 * names, folders and files sorted by name, every folder's size the sum of
 * what it holds.
 */
export function localTree<F extends LocalFile>(files: readonly F[], root = 'upload'): LocalFolder {
  const top: LocalFolder = { name: root, size: 0, files: [], folders: [] };
  for (const file of files) {
    const parts = pathParts(file.url || file.name);
    let here = top;
    for (const folder of parts.slice(0, -1)) {
      let next = here.folders.find((f) => f.name === folder);
      if (!next) {
        next = { name: folder, size: 0, files: [], folders: [] };
        here.folders.push(next);
      }
      here = next;
    }
    here.files.push(file);
  }
  const settle = (folder: LocalFolder): number => {
    folder.files.sort((a, b) => a.name.localeCompare(b.name));
    folder.folders.sort((a, b) => a.name.localeCompare(b.name));
    folder.size = folder.files.reduce((sum, f) => sum + f.size, 0)
      + folder.folders.reduce((sum, f) => sum + settle(f), 0);
    return folder.size;
  };
  settle(top);
  return top;
}
