/**
 * The Files panel's tree takes each folder read into the tree it shows when
 * the read answers.
 *
 * **WHAT THIS HOLDS THAT ONE ANSWER CANNOT SHOW.** Each defect here is an
 * order: two folders read at once, or a folder read and then another
 * repository fetched before it answered. The reads are promises the test
 * resolves in whatever order a slow network would.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { RepoTree } from '../../dist-pure/features/repository/repo_tree.js';
import { Directory, RawFile, RawFolder, RepoInfo } from '../../dist-pure/components/models/source.js';

const A = 'https://github.com/example/a/';
const B = 'https://github.com/example/b/';

const unread = (name) => new RawFolder(name, 0, [], []);
const read = (name, ...files) => new RawFolder(name, files.length, files.map((f) => new RawFile(f, 1, '', `${name}/${f}`)), []);
const partial = (url, ...folders) => {
  const name = url.split('/').filter(Boolean).pop();
  return new Directory(new RepoInfo('example', name, url), 1, new RawFolder('', 0, [], folders), true);
};

const flush = () => new Promise((resolve) => setImmediate(resolve));

function harness(tree) {
  let shown = tree;
  const asked = { subtree: [], expandAll: [] };
  const waiting = { subtree: [], expandAll: [] };
  const route = (name) => (...args) => {
    asked[name].push(args);
    return new Promise((resolve) => waiting[name].push(resolve));
  };
  const tree_ = new RepoTree(
    {
      get shown() { return shown; },
      show: (next) => { shown = next; },
    },
    { subtree: route('subtree'), expandAll: route('expandAll') },
  );
  return {
    tree: tree_,
    asked,
    get shown() { return shown; },
    /** What the panel shows after another fetch. */
    fetched(next) { shown = next; },
    /** Answer the `nth` request made to `name`, counting from 0 in the order asked. */
    async answer(name, nth, value) {
      waiting[name][nth](value);
      await flush();
    },
  };
}

const folder = (tree, name) => tree.root.folders.find((f) => f.name === name);
const fileNames = (f) => f.files.map((x) => x.name);

test('two folders read at once both reach the tree, whichever answers last', async () => {
  /**
   * Click `src`, then `docs` before `src` answers. Each read took the tree as
   * it was when it was asked and wrote it back when it answered, so the second
   * answer wrote a tree without the first's files. Mutation: merge into the
   * tree read before the request -- this fails.
   */
  const h = harness(partial(A, unread('src'), unread('docs')));
  const src = h.tree.expandPath('src');
  const docs = h.tree.expandPath('docs');
  await h.answer('subtree', 0, read('src', 'main.py'));
  await h.answer('subtree', 1, read('docs', 'index.md'));
  assert.deepEqual(await Promise.all([src, docs]), [true, true]);
  assert.deepEqual(fileNames(folder(h.shown, 'src')), ['main.py']);
  assert.deepEqual(fileNames(folder(h.shown, 'docs')), ['index.md']);
});

test('a folder read lands at its path, and the rest of the tree is kept', async () => {
  const lib = new RawFolder('lib', 0, [], [unread('deep')]);
  const h = harness(partial(A, new RawFolder('src', 0, [], [lib]), unread('docs')));
  const done = h.tree.expandPath('src/lib/deep');
  await h.answer('subtree', 0, read('deep', 'x.c'));
  await done;
  const deep = folder(h.shown, 'src').folders[0].folders[0];
  assert.deepEqual(fileNames(deep), ['x.c']);
  assert.ok(folder(h.shown, 'docs'), 'a folder not read is still there');
  assert.equal(h.shown.is_partial, true);
  assert.ok(h.shown instanceof Directory, 'a Directory, not an object shaped like one');
});

test('a folder read for a repository no longer shown is dropped', async () => {
  /**
   * Click a folder in repository A, then fetch B before it answers: A's answer
   * was merged into the tree A had, and that tree replaced B's. Mutation: drop
   * the check that the tree shown is still A's -- this fails.
   */
  const h = harness(partial(A, unread('src')));
  const late = h.tree.expandPath('src');
  const b = partial(B, unread('lib'));
  h.fetched(b);
  await h.answer('subtree', 0, read('src', 'main.py'));
  assert.equal(await late, false, 'nothing was put in the tree');
  assert.equal(h.shown, b, "B's tree is the one shown");
});

test('a folder read for a repository fetched again lands in the tree fetched', async () => {
  /** The same repository is the same tree, whichever reading of it is shown. */
  const h = harness(partial(A, unread('src')));
  const done = h.tree.expandPath('src');
  h.fetched(partial(A, unread('src'), unread('more')));
  await h.answer('subtree', 0, read('src', 'main.py'));
  assert.equal(await done, true);
  assert.deepEqual(fileNames(folder(h.shown, 'src')), ['main.py']);
  assert.ok(folder(h.shown, 'more'), 'the tree fetched since is the one read into');
});

test('a whole tree expanded for a repository no longer shown is dropped', async () => {
  /** Expand All in A, then fetch B: A's expanded tree replaced B's. */
  const h = harness(partial(A, unread('src')));
  const late = h.tree.expandAll(3);
  const b = partial(B, unread('lib'));
  h.fetched(b);
  await h.answer('expandAll', 0, partial(A, read('src', 'main.py')));
  assert.equal(await late, false);
  assert.equal(h.shown, b);
});

test('a folder is read from the repository the tree shows, whatever the URL field holds', async () => {
  /**
   * The Files panel passed `panelState.repoUrl`, which follows every keystroke
   * in the Repository panel's URL field: type B's URL without fetching it,
   * open a folder of A's tree, and B was asked for A's folder. Mutation: read
   * from a URL the caller passes -- this fails.
   */
  const h = harness(partial(A, unread('src')));
  void h.tree.expandPath('src');
  void h.tree.expandAll(3);
  assert.deepEqual(h.asked.subtree, [[A, 'src']]);
  assert.deepEqual(h.asked.expandAll, [[A, 3]]);
});
