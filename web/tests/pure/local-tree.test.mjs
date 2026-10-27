// Added files and folders: which are read, and the tree they are drawn as.
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { LOCAL_FILE_LIMIT, keptLocal, localTree, pathParts } from '../../dist-pure/features/repository/local_tree.js';

const file = (url, size = 10) => ({ name: url.split('/').pop(), size, raw: '', url });

test('a folder is drawn as its folders, not as one flat folder', () => {
  // Mutation: put every file in the root, as the uploads were -- `src` and
  // `tests` are lost, and this fails.
  const tree = localTree([file('proj/src/a.py'), file('proj/tests/__init__.py'), file('proj/src/__init__.py'),
    file('proj/README.md')]);
  assert.equal(tree.name, 'upload');
  const proj = tree.folders.find((f) => f.name === 'proj');
  assert.deepEqual(proj.folders.map((f) => f.name), ['src', 'tests']);
  assert.deepEqual(proj.files.map((f) => f.name), ['README.md']);
  const src = proj.folders.find((f) => f.name === 'src');
  assert.deepEqual(src.files.map((f) => f.name), ['__init__.py', 'a.py']);
  // Two files of one name in two folders are two files.
  assert.equal(proj.folders.find((f) => f.name === 'tests').files.length, 1);
  assert.equal(tree.size, 40);
});

test('files dropped on their own sit at the root', () => {
  const tree = localTree([file('b.py'), file('a.py')]);
  assert.deepEqual(tree.files.map((f) => f.name), ['a.py', 'b.py']);
  assert.equal(tree.folders.length, 0);
});

test("a folder's version control, dependencies and build output are not read", () => {
  // Mutation: read everything under a folder -- node_modules is read, and this fails.
  assert.equal(keptLocal('proj/node_modules/x/index.js', 10), false);
  assert.equal(keptLocal('proj/.git/config', 10), false);
  assert.equal(keptLocal('proj/src/__pycache__/a.cpython-312.pyc', 10), false);
  assert.equal(keptLocal('proj/target/debug/build.rs', 10), false);
  assert.equal(keptLocal('proj/src/node_modules.py', 10), true, 'a file named like a skipped folder is read');
  assert.equal(keptLocal('proj/src/a.py', 10), true);
});

test('a file past the limit, or of an extension the parse leaves out, is not read', () => {
  assert.equal(keptLocal('a.py', LOCAL_FILE_LIMIT + 1), false);
  assert.equal(keptLocal('a.py', LOCAL_FILE_LIMIT), true);
  assert.equal(keptLocal('a.py', 10, ['.rs', 'py']), true);
  assert.equal(keptLocal('a.PY', 10, ['.py']), true);
  assert.equal(keptLocal('a.md', 10, ['.py']), false);
  assert.equal(keptLocal('a.md', 10, []), true, 'no extensions named reads every file');
});

test("a path's parts are read whatever its separators", () => {
  assert.deepEqual(pathParts('./proj\\src/a.py'), ['proj', 'src', 'a.py']);
  assert.deepEqual(pathParts('/proj/a.py'), ['proj', 'a.py']);
});
