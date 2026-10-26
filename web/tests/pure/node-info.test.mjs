/**
 * View → Info says something on every use; View → Source and a double-click
 * open one place, decided here.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { fitBadgeText, infoLine, sourceLine, sourceTarget } from '../../dist-pure/features/graph/services/node_info.js';

test('Info names the node, what its parser called it, and where it is', () => {
  const node = { id: 'rust::x', label: 'delay', language: 'rust', kind: 'function', file: 'src/main.rs', line: 12 };
  assert.equal(infoLine(node), 'delay · rust function · src/main.rs:12');
});

test('Info says what the node is across languages, and what else it is', () => {
  const node = {
    id: 'x', label: 'SysTick', language: 'rust', kind: 'function', file: 'src/main.rs', line: 28,
    construct_name: 'Function', meta: { facets: ['firmware.interrupt'] },
  };
  assert.equal(infoLine(node), 'SysTick · rust function · Function (firmware.interrupt) · src/main.rs:28');
});

test('a node from no file is still described, by what is known', () => {
  assert.equal(infoLine({ id: 'crate::hal', label: 'hal', kind: 'crate' }), 'hal · crate');
  assert.equal(infoLine({ id: 'bare' }), 'bare');
});

test('Source is the file and line, or nothing to show', () => {
  assert.equal(sourceLine({ id: 'a', file: 'main', line: 3 }), 'main:3');
  assert.equal(sourceLine({ id: 'a', file: 'main' }), 'main');
  assert.equal(sourceLine({ id: 'a' }), null);
});

test('Source opens the file on its forge, at the line when one is known and at the top when not', () => {
  /* Mutation: offer a target only for a node with a line, as the double-click
     did -- a file node opens nothing, and this fails. */
  const raw = 'https://raw.githubusercontent.com/tokio-rs/mini-redis/master/src/db.rs';
  assert.deepEqual(sourceTarget({ id: 'a', file: raw, line: 40 }),
    { kind: 'forge', href: 'https://github.com/tokio-rs/mini-redis/blob/master/src/db.rs#L40' });
  assert.deepEqual(sourceTarget({ id: 'a', file: raw, line: 0 }),
    { kind: 'forge', href: 'https://github.com/tokio-rs/mini-redis/blob/master/src/db.rs' });
});

test('a file read from disk is named beside the node, with its line when known', () => {
  assert.deepEqual(sourceTarget({ id: 'x', label: 'delay', file: '/ws/src/main.rs', line: 21 }),
    { kind: 'local', text: 'delay  /ws/src/main.rs:21' });
  assert.deepEqual(sourceTarget({ id: 'file::src/main.rs', label: 'main.rs', file: '/ws/src/main.rs', line: 0 }),
    { kind: 'local', text: 'main.rs  /ws/src/main.rs' });
});

test('a node from no file offers no source', () => {
  assert.equal(sourceTarget({ id: 'dir::src', file: '', line: 0 }), null);
  assert.equal(sourceTarget({ id: 'crate::hal' }), null);
});

/* A C symbol names its file's stem and a Python symbol `module.py`; where the
   file is, the GitHub URL or the path on disk, is held by the file node the
   symbol is drawn inside. These graphs are what the GitHub stream sends: the
   file node's `file` is the raw URL, a depth-2 symbol hangs from it by
   `contains`, and a depth-3 one from its symbol by `contains` or `field_of`,
   flat or under `metadata` as gJGF carries it. */
const RAW_C = 'https://raw.githubusercontent.com/o/fw/main/src/drivers/uart.c';
const RAW_PY = 'https://raw.githubusercontent.com/o/app/main/pkg/models.py';

function graphOf(nodes, edges) {
  return { nodes: new Map(nodes.map((n) => [n.id, n])), edges };
}

const cGraph = graphOf(
  [
    { id: 'file::src/drivers/uart.c', label: 'uart.c', kind: 'file', depth: 1, file: RAW_C, line: 0 },
    { id: 'uart::uart_init', label: 'uart_init', kind: 'function', depth: 2, file: 'uart', line: 12 },
    { id: 'uart::struct regs', label: 'regs', kind: 'struct', depth: 2, file: 'uart', line: 30 },
    { id: 'uart::struct regs::baud', label: 'baud', kind: 'field', depth: 3, file: 'uart', line: 32 },
  ],
  [
    { source: 'file::src/drivers/uart.c', target: 'uart::uart_init', kind: 'contains' },
    { source: 'file::src/drivers/uart.c', target: 'uart::struct regs', kind: 'contains' },
    { source: 'uart::struct regs', target: 'uart::struct regs::baud', kind: 'field_of' },
  ],
);

test('a C symbol from GitHub opens its file\'s forge page at its line, found through its file node', () => {
  /* Mutation: use the node's own `file` alone -- the stem names no page, a
     badge reads `uart_init  uart:12`, and this fails. */
  assert.deepEqual(sourceTarget(cGraph.nodes.get('uart::uart_init'), cGraph),
    { kind: 'forge', href: 'https://github.com/o/fw/blob/main/src/drivers/uart.c#L12' });
  assert.deepEqual(sourceTarget(cGraph.nodes.get('uart::struct regs::baud'), cGraph),
    { kind: 'forge', href: 'https://github.com/o/fw/blob/main/src/drivers/uart.c#L32' });
});

test('a Python symbol from GitHub opens its file\'s forge page at the top, since its parser records no line', () => {
  const g = graphOf(
    [
      { id: 'file::pkg/models.py', label: 'models.py', kind: 'file', depth: 1, file: RAW_PY, line: 0 },
      { id: 'models.User', label: 'User', kind: 'class', depth: 2, file: 'models.py', line: 0 },
      { id: 'models.User.save', label: 'save', kind: 'function', depth: 3, file: 'models.py', line: 0 },
    ],
    [
      { source: 'file::pkg/models.py', target: 'models.User', metadata: { kind: 'contains' } },
      { source: 'models.User', target: 'models.User.save', metadata: { kind: 'contains' } },
    ],
  );
  assert.deepEqual(sourceTarget(g.nodes.get('models.User.save'), g),
    { kind: 'forge', href: 'https://github.com/o/app/blob/main/pkg/models.py' });
});

test('a symbol read from disk is named by its file node\'s path, at its line', () => {
  const g = graphOf(
    [
      { id: 'file::src/uart.c', label: 'uart.c', kind: 'file', depth: 1, file: '/ws/src/uart.c', line: 0 },
      { id: 'uart::uart_init', label: 'uart_init', kind: 'function', depth: 2, file: 'uart', line: 12 },
    ],
    [{ source: 'file::src/uart.c', target: 'uart::uart_init', kind: 'contains' }],
  );
  assert.deepEqual(sourceTarget(g.nodes.get('uart::uart_init'), g),
    { kind: 'local', text: 'uart_init  /ws/src/uart.c:12' });
});

test('a symbol with no file node above it is named by its own file; one that names no file offers nothing', () => {
  // Calls are not containment: the caller's file is not the callee's.
  const g = graphOf(
    [
      { id: 'file::src/main.c', label: 'main.c', kind: 'file', depth: 1, file: RAW_C, line: 0 },
      { id: 'main::main', label: 'main', kind: 'function', depth: 2, file: 'main', line: 3 },
      { id: 'uart::uart_init', label: 'uart_init', kind: 'function', depth: 2, file: 'uart', line: 12 },
      { id: 'pkg.helper', label: 'helper', kind: 'function', depth: 2, file: '', line: 0 },
    ],
    [
      { source: 'file::src/main.c', target: 'main::main', kind: 'contains' },
      { source: 'main::main', target: 'uart::uart_init', kind: 'calls' },
      { source: 'file::src/main.c', target: 'pkg.helper', kind: 'contains' },
    ],
  );
  assert.deepEqual(sourceTarget(g.nodes.get('uart::uart_init'), g),
    { kind: 'local', text: 'uart_init  uart:12' });
  assert.equal(sourceTarget(g.nodes.get('pkg.helper'), g), null);
});

test('a node that names its own URL keeps it', () => {
  const rs = 'https://raw.githubusercontent.com/o/fw/main/src/main.rs';
  const g = graphOf(
    [
      { id: 'file::src/main.rs', label: 'main.rs', kind: 'file', depth: 1, file: RAW_C, line: 0 },
      { id: 'rust::delay', label: 'delay', kind: 'function', depth: 2, file: rs, line: 21 },
    ],
    [{ source: 'file::src/main.rs', target: 'rust::delay', kind: 'contains' }],
  );
  assert.deepEqual(sourceTarget(g.nodes.get('rust::delay'), g),
    { kind: 'forge', href: 'https://github.com/o/fw/blob/main/src/main.rs#L21' });
});

test('a badge too long for the canvas keeps the name and the end of the path', () => {
  /* Mutation: cut the end off instead, as a CSS ellipsis does -- the line
     number goes, and this fails. */
  const text = 'delay  /home/runner/work/codecartographer/examples/rust-firmware/crates/blinky/src/main.rs:21';
  const short = fitBadgeText(text, 40);
  assert.ok(short.length <= 40, `${short} is ${short.length} long`);
  assert.ok(short.startsWith('delay  …/'), short);
  assert.ok(short.endsWith('/src/main.rs:21'), short);
  // Cut at a separator, so no directory's name is left half there.
  assert.match(short, /^delay  …\/[^/]+\//);
});

test('a badge that fits is left whole, and Windows paths are cut at a backslash', () => {
  assert.equal(fitBadgeText('main.rs  /ws/src/main.rs', 40), 'main.rs  /ws/src/main.rs');
  const win = fitBadgeText(String.raw`build.rs  D:\ws\examples\rust-firmware\crates\blinky\build.rs`, 36);
  assert.ok(win.length <= 36, win);
  assert.match(win, /^build\.rs  …\\.*\\blinky\\build\.rs$/);
});

test('a canvas too narrow for the name keeps the end of the text', () => {
  const short = fitBadgeText('a_very_long_function_name  /ws/src/main.rs:21', 12);
  assert.ok(short.length <= 12, short);
  assert.ok(short.startsWith('…') && short.endsWith('main.rs:21'), short);
  assert.equal(fitBadgeText('anything at all', 0), '');
});

test('a name that leaves no room for the file is shortened first, so the file and line stay', () => {
  /* Mutation: keep the name whole and cut the path to what is left -- at 30
     `…21` is all of the path that stays, and this fails. */
  const text = 'a_very_long_function_name  /ws/src/main.rs:21';
  for (const max of [30, 36]) {
    const short = fitBadgeText(text, max);
    assert.ok(short.length <= max, `${short} is ${short.length} long`);
    assert.ok(short.endsWith('/main.rs:21'), short);
    assert.ok(short.startsWith('a_very_long_fun'), short);
  }
});
