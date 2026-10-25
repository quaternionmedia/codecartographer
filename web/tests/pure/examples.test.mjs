/**
 * What the project selector offers, in what order.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { GITHUB_EXAMPLES, SIZES_MEASURED, exampleGroups } from '../../dist-pure/features/examples/examples.js';

const blinky = {
  id: 'rust-firmware', label: 'blinky (recorded)', language: 'rust',
  title: 'recorded', path: '/checkout/examples/rust-firmware', cargo: true,
};

test('Rust leads, and its bundled example leads Rust', () => {
  /* Mutation: append bundled examples instead of putting them first -- the
     one example that needs no network sits behind five that do, and this fails. */
  const groups = exampleGroups([blinky]);
  assert.deepEqual(groups.map((g) => g.language), ['Rust', 'C', 'Python']);
  const first = groups[0].examples[0];
  assert.deepEqual([first.label, first.url, first.bundled, first.cargo],
    ['blinky (recorded)', '/checkout/examples/rust-firmware', true, true]);
  assert.equal(groups[0].examples.length, GITHUB_EXAMPLES[0].examples.length + 1);
});

test('with nothing bundled, the GitHub examples stand alone and unchanged', () => {
  assert.deepEqual(exampleGroups([]), GITHUB_EXAMPLES.map((g) => ({ ...g, examples: [...g.examples] })));
});

test('a bundled example in a language with no group gets one', () => {
  const groups = exampleGroups([{ ...blinky, language: 'zig', label: 'z' }]);
  assert.equal(groups.at(-1).language, 'zig');
  assert.equal(groups.at(-1).examples[0].label, 'z');
});

test('every GitHub example is a repository URL, once, measured, with a title that ends saying how much is drawn', () => {
  /* Which of the three words the server's thresholds give for its size is
     held by tests/test_examples.py, which reads github_service's limits. */
  const urls = GITHUB_EXAMPLES.flatMap((g) => g.examples.map((e) => e.url));
  assert.equal(new Set(urls).size, urls.length);
  assert.match(SIZES_MEASURED, /^\d{4}-\d{2}-\d{2}$/);
  for (const group of GITHUB_EXAMPLES) {
    for (const e of group.examples) {
      assert.match(e.url, /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/);
      assert.ok(Number.isInteger(e.sizeKb) && e.sizeKb > 0, `${e.label} has no measured size`);
      assert.match(e.title, /, (with content|structure only|shallow root)$/);
    }
  }
});
