/**
 * Files from disk as the browser hands them over, each with its path under
 * what was added: chosen in a file chooser, chosen as a folder, or dropped.
 *
 * A folder chosen in the chooser gives each file its `webkitRelativePath`. A
 * folder dropped gives only its entry, which is read here, folder by folder;
 * a dropped file is its own entry. Where the browser offers no entries, the
 * dropped files are taken as they come, each at the root.
 */

/** A file from disk, and its path under what was added. */
export interface AddedFile {
  file: File;
  path: string;
}

/** The files of a file chooser or a folder chooser. */
export function chosenFiles(files: FileList | null): AddedFile[] {
  return Array.from(files ?? []).map((file) => ({ file, path: file.webkitRelativePath || file.name }));
}

/** Every entry in a folder: `readEntries` answers in batches, until an empty one. */
function readFolder(folder: FileSystemDirectoryEntry): Promise<FileSystemEntry[]> {
  const reader = folder.createReader();
  const all: FileSystemEntry[] = [];
  return new Promise((resolve, reject) => {
    const next = () => reader.readEntries((batch) => {
      if (batch.length === 0) resolve(all);
      else { all.push(...batch); next(); }
    }, reject);
    next();
  });
}

async function walk(entry: FileSystemEntry, out: AddedFile[]): Promise<void> {
  if (entry.isFile) {
    const file = await new Promise<File>((resolve, reject) => (entry as FileSystemFileEntry).file(resolve, reject));
    out.push({ file, path: entry.fullPath.replace(/^\//, '') });
  } else if (entry.isDirectory) {
    for (const child of await readFolder(entry as FileSystemDirectoryEntry)) await walk(child, out);
  }
}

/** The files dropped, a dropped folder's files included, each with its path. */
export async function droppedFiles(transfer: DataTransfer | null): Promise<AddedFile[]> {
  if (!transfer) return [];
  // Read before any await: the browser empties the transfer once the drop event returns.
  const entries = Array.from(transfer.items ?? [])
    .map((item) => (item.kind === 'file' ? item.webkitGetAsEntry?.() ?? null : null));
  if (entries.length && entries.every((entry) => entry)) {
    const out: AddedFile[] = [];
    for (const entry of entries) await walk(entry as FileSystemEntry, out);
    return out;
  }
  return chosenFiles(transfer.files);
}
