/**
 * What the project selector offers, in what order.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { GITHUB_EXAMPLES, exampleGroups } from '../../dist-pure/features/examples/examples.js';

const blinky = {
  id: 'rust-firmware', label: 'blinky (recorded)', language: 'rust',
  title: 'recorded', path: '/checkout/examples/rust-firmware', cargo: true,
};

test('Rust leads, and its bundled example leads Rust', () => {
  /* Mutation: append bundled examples instead of putting them first -- the
     one example that needs no network sits behind five that do, and this fails. */
  const groups = exampleGroups([blinky]);
  assert.deepEqual(groups.map((g) => g.language), ['Rust', 'C', 'Python', 'JavaScript']);
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

test('every GitHub example is a repository URL, once, with a title that says how much is drawn', () => {
  const urls = GITHUB_EXAMPLES.flatMap((g) => g.examples.map((e) => e.url));
  assert.equal(new Set(urls).size, urls.length);
  for (const group of GITHUB_EXAMPLES) {
    for (const e of group.examples) {
      assert.match(e.url, /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/);
      assert.match(e.title, /content|structure only|shallow root/);
    }
  }
});
