/**
 * Every panel is in one group and says what it answers.
 *
 * `grouped` is run as compiled. The registry is read as text, as the other
 * registry tests here read it, because it imports every panel and a panel
 * imports the DOM.
 *
 * Each test names the mutation it was seen to fail under.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { GROUPS, grouped } from '../../dist-pure/layout/panel_groups.js';

const registry = readFileSync('src/layout/panel_registry.ts', 'utf8');
const DEFINITIONS = [...registry.matchAll(
  /^\s+id: '([a-z-]+)',\s*\n\s+menuLabel: '([^']+)',\s*\n\s+group: '([a-z]+)',\s*\n\s+answers: '((?:[^'\\]|\\.)+)',/gm,
)].map(([, id, label, group, answers]) => ({ id, label, group, answers }));
const IDS = [...registry.matchAll(/^\s+id: '([a-z-]+)',\s*\n\s+menuLabel:/gm)].map((found) => found[1]);

test('every definition states a group a heading names, and a sentence', () => {
  // Mutations: delete one definition's `group` or `answers` line -- the counts
  // differ; set a group to a word no heading has -- the membership fails.
  assert.ok(IDS.length >= 10, 'no definitions read from panel_registry.ts; the pattern is stale');
  assert.deepEqual(DEFINITIONS.map((found) => found.id), IDS);
  const known = GROUPS.map((heading) => heading.group);
  for (const found of DEFINITIONS) {
    assert.ok(known.includes(found.group), `${found.id} is in ${found.group}, which no heading names`);
    assert.match(found.answers, /^[A-Z].{20,}\.$/, `${found.id} does not say what it answers in a sentence`);
  }
});

test('no two panels answer in the same words', () => {
  // Mutation: copy one panel's sentence onto another -- two near names are again told apart by nothing.
  const said = DEFINITIONS.map((found) => found.answers);
  assert.equal(new Set(said).size, said.length);
});

test('the panels that read the organisation are told apart by source', () => {
  // Mutation: drop the source from one of these sentences -- this fails. Estate,
  // Show, Overview and Capabilities each read a different thing, and the
  // sentence is where a reader learns which.
  const by = Object.fromEntries(DEFINITIONS.map((found) => [found.id, found.answers]));
  assert.match(by['estate-panel'], /source/);
  assert.match(by['show-panel'], /corpus/);
  assert.match(by['overview-panel'], /dossier/);
  assert.match(by['capabilities-panel'], /registry/);
  for (const id of ['estate-panel', 'show-panel', 'overview-panel', 'capabilities-panel']) {
    assert.equal(DEFINITIONS.find((found) => found.id === id).group, 'organisation', id);
  }
  for (const id of ['topology-panel', 'harness-panel', 'interactions-panel']) {
    assert.equal(DEFINITIONS.find((found) => found.id === id).group, 'harness', id);
  }
});

const P = (id, group) => ({ id, group });

test('panels are listed under their headings, in heading order', () => {
  // Mutation: return the panels in the order given, under one heading -- this fails.
  const found = grouped([P('show', 'organisation'), P('graph', 'canvas'), P('harness', 'harness'), P('estate', 'organisation')]);
  assert.deepEqual(found.map((entry) => entry.heading.title), ['Canvas', 'Harness', 'Organisation']);
  assert.deepEqual(found[2].panels.map((panel) => panel.id), ['show', 'estate']);
});

test('a heading with no panel is left out', () => {
  // Mutation: drop the filter -- an empty heading is drawn above nothing.
  assert.deepEqual(grouped([P('graph', 'canvas')]).map((entry) => entry.heading.title), ['Canvas']);
  assert.deepEqual(grouped([]), []);
});

test('a panel in a group no heading names is still listed', () => {
  // Mutation: drop the stray entry -- a definition with a mistyped group cannot be opened.
  const found = grouped([P('graph', 'canvas'), P('odd', 'elsewhere')]);
  assert.deepEqual(found.map((entry) => entry.heading.title), ['Canvas', 'Ungrouped']);
  assert.deepEqual(found[1].panels.map((panel) => panel.id), ['odd']);
});
