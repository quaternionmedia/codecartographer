/**
 * The Files panel's repository tree, read into folder by folder, decided
 * without a browser.
 *
 * **WHY THIS IS NOT IN `RepoActions`.** The defects here are matters of order,
 * not of any one answer: two folders read at once, or a folder read and then
 * another repository fetched before it answered. Order is a sequence, a
 * sequence is a test, and `actions.ts` is application code no test build
 * compiles -- the reason `cartography_actions.ts` exists. So the sequencing
 * lives here, against a host and reads that `RepoActions` supplies and
 * `node --test` fakes.
 */

// `.js`, so the build `node --test` reads resolves it as the bundler does.
import { Directory, RawFolder } from '../../components/models/source.js';

/** The tree the Files panel shows, as these reads need it. */
export interface RepoTreeHost {
  /** The tree shown now. */
  readonly shown: Directory | null | undefined;
  /** Show this tree in its place. */
  show(tree: Directory): void;
}

/** The routes these reads use, as `RepoService` reaches them. */
export interface RepoTreeReads {
  /** One level of the folder at `path`. */
  subtree(url: string, path: string): Promise<RawFolder | null>;
  /** The whole tree, structure only, to `maxDepth`. */
  expandAll(url: string, maxDepth: number): Promise<Directory | null>;
}

/** The tree with `expanded` in place of the folder at `pathParts`. */
export function mergeFolderAtPath(root: RawFolder, pathParts: string[], expanded: RawFolder): RawFolder {
  if (pathParts.length === 0) return expanded;
  const [head, ...rest] = pathParts;
  return new RawFolder(
    root.name,
    root.size,
    root.files,
    root.folders.map((f) => (f.name === head ? mergeFolderAtPath(f, rest, expanded) : f)),
  );
}

/** The repository a tree is of. Two readings of one repository are one tree. */
function repositoryOf(tree: Directory | null | undefined): string {
  return (tree?.info?.url ?? '').replace(/\/+$/, '');
}

/**
 * Folder reads and Expand All.
 *
 * **AN ANSWER IS MERGED INTO THE TREE SHOWN WHEN IT ANSWERS.** A read that
 * took the tree when it was asked and wrote it back when it answered lost
 * every folder read in between: click `src`, then `docs` before `src`
 * answers, and `src`'s files were gone.
 *
 * **AN ANSWER FOR A TREE NO LONGER SHOWN IS DROPPED.** Each read holds the
 * repository of the tree it was asked from -- the ticket `Latest` hands out in
 * `cartography_actions.ts`, kept by the tree rather than by the request, since
 * any number of folders may be read into one tree at once. Fetch another
 * repository before the answer comes and the answer is of a tree that has
 * gone; merged, it replaced the new repository's tree with the old one.
 * Fetching the same repository again keeps the ticket: it is the same tree.
 */
export class RepoTree {
  constructor(
    private readonly host: RepoTreeHost,
    private readonly reads: RepoTreeReads,
  ) {}

  /**
   * Read the folder at `path` into the tree. Resolves true when its contents
   * were put in the tree, false when the tree it was asked from has gone.
   *
   * **READ FROM THE REPOSITORY THE TREE IS OF.** The URL is the shown tree's
   * own (`info.url`), never one the caller holds: the Files panel passed the
   * Repository panel's URL field, which follows every keystroke, so a folder
   * of A's tree was asked of whatever had been typed since.
   */
  async expandPath(path: string): Promise<boolean> {
    const shown = this.host.shown;
    const asked = repositoryOf(shown);
    if (!shown || !asked) return false;
    const folder = await this.reads.subtree(shown.info.url, path);
    const now = this.host.shown;
    if (!now || repositoryOf(now) !== asked) return false;
    const pathParts = path.split('/').filter((p) => p.length > 0);
    // Constructed via `new Directory(...)`, not a `{...now}` spread --
    // isEmpty is a computed getter on the class prototype, which a plain
    // object spread silently drops.
    this.host.show(new Directory(now.info, now.size, mergeFolderAtPath(now.root, pathParts, folder as RawFolder), now.is_partial));
    return true;
  }

  /**
   * Replace the tree with every folder read to `maxDepth`. Resolves true when
   * it was shown, false when there was nothing to show or the tree it was
   * asked from has gone.
   */
  async expandAll(maxDepth = 3): Promise<boolean> {
    const shown = this.host.shown;
    const asked = repositoryOf(shown);
    if (!shown || !asked) return false;
    const result = await this.reads.expandAll(shown.info.url, maxDepth);
    if (!result || repositoryOf(this.host.shown) !== asked) return false;
    this.host.show(result);
    return true;
  }
}
