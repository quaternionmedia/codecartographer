/**
 * What the Compose panel offers for a design, and what it says the harness did.
 *
 * Each test names the mutation it was seen to fail under.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  compositionQuery, configOf, designLink, errorsElsewhere, errorsFor, fieldsOf, initialValues, referencesOf, savable,
  saveOutcome, ticked, toggled, verdictShown,
} from '../../dist-pure/features/estate/compose.js';

const SCHEMA = {
  $defs: {
    Method: { enum: ['majority', 'unanimous'], title: 'Method', type: 'string' },
    Ref: { type: 'object', properties: { name: { type: 'string' } } },
  },
  properties: {
    components: { type: 'array', items: { $ref: '#/$defs/Ref' }, title: 'Components' },
    compose: { type: 'array', items: { type: 'string' }, title: 'Compose' },
    num_checkers: { type: 'integer', default: 3, minimum: 2, maximum: 10, title: 'Num Checkers' },
    method: { $ref: '#/$defs/Method', default: 'majority' },
    share: { type: 'boolean', default: false, title: 'Share' },
    fallback: { anyOf: [{ type: 'string' }, { type: 'null' }], default: null, title: 'Fallback' },
    specialisms: { type: 'array', items: { type: 'string' }, title: 'Specialisms' },
    slots: { type: 'object', title: 'Slots' },
  },
};
const URL = 'http://window/designer/designs';
const byName = (fields) => Object.fromEntries(fields.map((field) => [field.name, field]));

test('each property is offered as the schema types it, in the harness\'s order', () => {
  // Mutation: leave a `$ref` unresolved -- `method` has no choices.
  const fields = fieldsOf(SCHEMA);
  assert.deepEqual(fields.map((field) => field.name),
    ['components', 'compose', 'num_checkers', 'method', 'share', 'fallback', 'specialisms', 'slots']);
  const found = byName(fields);
  assert.equal(found.num_checkers.kind, 'integer');
  assert.equal(found.num_checkers.minimum, 2);
  assert.equal(found.num_checkers.maximum, 10);
  assert.equal(found.method.kind, 'choice');
  assert.deepEqual(found.method.choices, ['majority', 'unanimous']);
  assert.equal(found.method.fallback, 'majority');
  assert.equal(found.share.kind, 'boolean');
  assert.equal(found.specialisms.kind, 'strings');
  assert.equal(found.num_checkers.title, 'Num Checkers');
});

test('the two reference properties are offered as references, by name', () => {
  // Mutation: offer `compose` as a list of typed strings -- nothing ticks a saved design.
  const found = byName(fieldsOf(SCHEMA));
  assert.equal(found.components.kind, 'components');
  assert.equal(found.compose.kind, 'compose');
});

test('a value that may be null is the type beside it, and says it may be left empty', () => {
  // Mutation: treat `anyOf` as not offered -- `fallback` has no control.
  const found = byName(fieldsOf(SCHEMA));
  assert.equal(found.fallback.kind, 'string');
  assert.equal(found.fallback.nullable, true);
  assert.equal(found.num_checkers.nullable, false);
});

test('a property this window has no control for is listed as not offered, and never sent', () => {
  // Mutation: send an unoffered field's value -- `slots` reaches the harness as text.
  const fields = fieldsOf(SCHEMA);
  assert.equal(byName(fields).slots.kind, 'unoffered');
  assert.ok(!('slots' in initialValues(fields)));
  assert.ok(!('slots' in configOf(fields, { ...initialValues(fields), slots: 'typed' })));
  assert.deepEqual(fieldsOf(null), []);
});

test('the form starts at the harness\'s defaults', () => {
  // Mutation: start every field blank -- the default `majority` is not shown.
  assert.deepEqual(initialValues(fieldsOf(SCHEMA)), {
    components: [], compose: [], num_checkers: '3', method: 'majority', share: false, fallback: '', specialisms: '',
  });
});

test('what is sent is what was filled in, typed, with a blank field left out', () => {
  // Mutation: send a number as the text typed -- `num_checkers` is "5".
  const fields = fieldsOf(SCHEMA);
  const config = configOf(fields, {
    components: ['reader'], compose: ['intake', 'review'], num_checkers: '5', method: 'unanimous',
    share: true, fallback: '  ', specialisms: 'law, , code',
  });
  assert.deepEqual(config, {
    components: [{ name: 'reader' }], compose: ['intake', 'review'], num_checkers: 5, method: 'unanimous',
    share: true, specialisms: ['law', 'code'],
  });
  assert.deepEqual(configOf(fields, { ...initialValues(fields), num_checkers: '' }),
    { method: 'majority', share: false });
});

test('a number that is not one is sent as typed, for the harness to refuse', () => {
  // Mutation: drop what does not parse -- the harness saves its default and nobody is told.
  const fields = fieldsOf(SCHEMA);
  assert.equal(configOf(fields, { num_checkers: 'many' }).num_checkers, 'many');
});

test('ticking a reference adds it once, and unticking takes only it away', () => {
  // Mutation: push without removing first -- a name ticked twice is sent twice.
  let values = { compose: [], components: ['reader'] };
  values = toggled(values, 'compose', 'intake', true);
  values = toggled(values, 'compose', 'intake', true);
  values = toggled(values, 'compose', 'review', true);
  assert.deepEqual(ticked(values, 'compose'), ['intake', 'review']);
  assert.deepEqual(ticked(toggled(values, 'compose', 'intake', false), 'compose'), ['review']);
  assert.deepEqual(ticked(values, 'components'), ['reader']);
  assert.deepEqual(ticked({}, 'compose'), []);
});

test('the composition is asked for with the draft and each reference named so far', () => {
  // Mutation: leave the references out of the query -- no line is drawn for a draft.
  const draft = { name: ' triage ', kind: 'delegation', description: '', project: '' };
  assert.equal(compositionQuery(draft, { compose: ['intake', 'review'], components: ['reader'] }),
    '?draft=true&name=triage&kind=delegation&components=reader&compose=intake%2Creview');
  assert.equal(compositionQuery(null, { compose: ['intake'] }), '');
  assert.equal(compositionQuery(null, {}, 'Circular'), '?layout=Circular');
});

test('a design is savable with a kind and a name, and not while one is being saved', () => {
  // Mutation: allow a blank name -- a press posts a design the server will not send.
  const draft = { name: 'triage', kind: 'delegation', description: '', project: '' };
  assert.equal(savable(draft, false), true);
  assert.equal(savable(draft, true), false);
  assert.equal(savable({ ...draft, name: '  ' }, false), false);
  assert.equal(savable({ ...draft, kind: '' }, false), false);
});

test('the harness\'s row is a saved design, and saved with no row is not called saved', () => {
  // Mutation: trust `saved` alone -- the panel prints a row that is not there.
  const row = { name: 'triage', address: 'qm://alpha/topology/triage' };
  const found = saveOutcome({ saved: true, design: row, where: 'http://harness/v1/topologies' }, URL);
  assert.equal(found.kind, 'saved');
  assert.deepEqual(found.design, row);
  assert.equal(saveOutcome({ saved: true }, URL).kind, 'refused');
});

test('no answer is this window\'s own API, a harness not answering is its own, a refusal keeps its fields', () => {
  // Mutation: call every failure a refusal -- a harness not answering reads as its judgement.
  assert.equal(saveOutcome(null, URL).kind, 'api-down');
  assert.equal(saveOutcome({ unreachable: true, problem: 'nothing is answering' }, URL).kind, 'unreachable');
  const refused = saveOutcome({
    refused: true, problem: 'the harness did not save the design (422)',
    errors: [{ field: 'config.num_checkers', message: 'too few' }, { field: '', message: '' }],
  }, URL);
  assert.equal(refused.kind, 'refused');
  assert.deepEqual(refused.errors, [{ field: 'config.num_checkers', message: 'too few' }]);
  assert.equal(refused.where, URL);
});

test('a message stands beside its field, or the field it is inside, and nowhere else', () => {
  // Mutation: match a field by prefix alone -- `config.compose` shows `config.components`' message.
  const errors = [
    { field: 'config.components.0.name', message: 'Field required' },
    { field: 'config.compose', message: 'unknown composed topology' },
    { field: 'name', message: 'bad name' },
    { field: '', message: 'a design of this name exists' },
    { field: 'version', message: 'not a version' },
  ];
  assert.deepEqual(errorsFor(errors, 'config.components'), ['Field required']);
  assert.deepEqual(errorsFor(errors, 'config.compose'), ['unknown composed topology']);
  assert.deepEqual(errorsFor(errors, 'config.comp'), []);
  assert.deepEqual(errorsElsewhere(errors, ['name', 'config.components', 'config.compose']),
    ['a design of this name exists', 'version: not a version']);
});

test('what the harness said of a design is its sentences as given, a part it left out not invented', () => {
  // Mutation: print `refused to run` for every design -- a design that runs reads as refused.
  assert.deepEqual(verdictShown({
    address: 'qm://alpha/topology/triage',
    capability: { status: 'refused', refusal: 'its arbiter decides', saved_anyway: 'designing is not an act' },
  }), ['status refused', 'refused to run: its arbiter decides', 'designing is not an act',
    'address qm://alpha/topology/triage']);
  assert.deepEqual(verdictShown({ address: null, address_unknown: 'no origin remote', capability: { status: 'runs' } }),
    ['status runs', 'no address: no origin remote']);
  assert.deepEqual(verdictShown({}), []);
});

test('a design\'s references are read from its configuration, whichever way each is written', () => {
  // Mutation: read strings only -- a component given as a mapping is not listed.
  assert.deepEqual(referencesOf({ config: { components: [{ name: 'reader' }, 'writer'], compose: ['intake'] } }),
    { components: ['reader', 'writer'], compose: ['intake'] });
  assert.deepEqual(referencesOf({}), { components: [], compose: [] });
});

test('a design\'s link is the harness\'s own row for it, in the project that was read', () => {
  // Mutation: append the name after the query -- the link asks for a project named `alpha/triage`.
  assert.equal(designLink('http://h/v1/topologies?project=alpha', 'tri age'),
    'http://h/v1/topologies/tri%20age?project=alpha');
  assert.equal(designLink('http://h/v1/topologies', 'triage'), 'http://h/v1/topologies/triage');
});
