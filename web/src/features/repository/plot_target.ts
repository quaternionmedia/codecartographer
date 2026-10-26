/**
 * What the Open panel's Plot draws, decided without a browser.
 *
 * **WITH A REPOSITORY LOADED, PLOT DRAWS THE REPOSITORY THE FILES PANEL
 * SHOWS.** Its URL is the shown tree's own (`info.url`, which `repo_tree.ts`
 * reads folders by), never the URL field's: the field follows every keystroke,
 * so fetch A, type B and press Plot streamed B while the Files panel showed A,
 * and the layout change or Relayout that re-ran the plot streamed B again. The
 * field is read only when nothing is loaded or added, as → Fetch reads it.
 */

// `.js`, so the build `node --test` reads resolves it as the bundler does.
import type { Directory } from '../../components/models/source.js';
import { hasTree, repositoryOf } from './repo_tree.js';

export type PlotTarget =
  /** The loaded repository, streamed by its URL. */
  | { readonly kind: 'repository'; readonly url: string }
  /** The loaded tree, which names no repository: streamed as it is. */
  | { readonly kind: 'tree' }
  /** Every added file, as one directory. */
  | { readonly kind: 'files'; readonly count: number }
  /** The URL in the field, fetched and drawn as → Fetch does. */
  | { readonly kind: 'fetch'; readonly url: string };

/**
 * What Plot draws: the loaded repository, else every added file, else the URL
 * in the field; null when there is none of them. A repository is loaded when
 * the Files panel shows its tree (`hasTree`), whatever the tree's size says.
 */
export function plotTarget(shown: Directory | null | undefined, added: number, field: string): PlotTarget | null {
  if (hasTree(shown)) {
    const url = repositoryOf(shown);
    return url ? { kind: 'repository', url } : { kind: 'tree' };
  }
  if (added > 0) return { kind: 'files', count: added };
  const url = field.trim();
  return url ? { kind: 'fetch', url } : null;
}
