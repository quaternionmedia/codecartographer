/**
 * What the Open panel's Plot draws: the loaded repository, else every added
 * file, else the URL in the field.
 *
 * `tests/state/plot-draws-the-loaded-tree.test.mjs` holds `onPlot` to asking
 * this.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { plotTarget } from '../../dist-pure/features/repository/plot_target.js';
import { Directory, RawFile, RawFolder, RepoInfo } from '../../dist-pure/components/models/source.js';

const A = 'https://github.com/example/a';
const B = 'https://github.com/example/b';

const tree = (url, size = 3) => new Directory(
  new RepoInfo('example', 'a', url),
  size,
  new RawFolder('', 1, [new RawFile('main.py', 1, '', `${url}/main.py`)], []),
);

test('with a repository loaded, Plot draws it, whatever the URL field has been typed to since', () => {
  /** Mutation: answer the field's URL while a tree is shown -- B is streamed beside A's tree, and this fails. */
  assert.deepEqual(plotTarget(tree(A), 0, B), { kind: 'repository', url: A });
  assert.deepEqual(plotTarget(tree(A), 2, ''), { kind: 'repository', url: A });
});

test('a tree read with a trailing slash is drawn as the one repository it is', () => {
  // Expand All's answer carries the URL with a `/` added (repo_router.py).
  assert.deepEqual(plotTarget(tree(`${A}/`), 0, ''), { kind: 'repository', url: A });
});

test('a loaded tree that names no repository is drawn as it is', () => {
  assert.deepEqual(plotTarget(tree(''), 0, B), { kind: 'tree' });
});

test('with nothing loaded, Plot draws every added file, and else the URL in the field', () => {
  assert.deepEqual(plotTarget(null, 2, B), { kind: 'files', count: 2 });
  assert.deepEqual(plotTarget(null, 0, `  ${B}  `), { kind: 'fetch', url: B });
  assert.equal(plotTarget(undefined, 0, '   '), null);
});
