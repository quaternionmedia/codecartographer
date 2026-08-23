/**
 * rad core import-boundary lint.
 *
 * The rad interaction contract's Conformance clause §2 requires a conformant
 * implementation to keep the state machine and geometry in a platform-free
 * core, "enforced by a grep lint in CI". The reference implementation cannot
 * run this check on itself — its core shares a file with an SVG renderer, so
 * there is nothing to grep but a comment banner (rad's C13).
 *
 * This port can, so it does. Two rules:
 *
 *   1. core/ may not mention the DOM.
 *   2. core/, session.ts and dom/ may not import application code. That is
 *      what keeps this directory liftable into a shared package once a second
 *      web host wants it; host/ is the only half that knows about this app.
 *
 * Exit 1 on violation. No dependencies.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';

const RAD = 'src/features/graph/rad';

/** Rule 1 — anything that only exists in a browser. */
const DOM_TOKENS = /\b(document|window|navigator|HTMLElement|SVGElement|localStorage|fetch)\b/;

/** Rule 2 — an import that climbs out of the rad directory. */
const ESCAPING_IMPORT = /from\s+'(\.\.\/){3,}/;

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...walk(p));
    else if (name.endsWith('.ts')) out.push(p);
  }
  return out;
}

/**
 * Comments are excluded before matching. A rule that trips on its own
 * documentation teaches contributors to stop documenting, and this file's
 * own header would fail rule 1.
 */
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

const violations = [];

for (const file of walk(RAD)) {
  const rel = relative(RAD, file).split(sep).join('/');
  const area = rel.split('/')[0];
  const body = stripComments(readFileSync(file, 'utf8'));

  if (area === 'core') {
    body.split('\n').forEach((line, i) => {
      const m = line.match(DOM_TOKENS);
      if (m) violations.push(`${rel}:${i + 1}: core/ may not reference the DOM — found '${m[1]}'`);
    });
  }

  if (area !== 'host') {
    body.split('\n').forEach((line, i) => {
      if (ESCAPING_IMPORT.test(line)) {
        violations.push(
          `${rel}:${i + 1}: only host/ may import application code — this import escapes rad/`,
        );
      }
    });
  }
}

if (violations.length) {
  console.error('rad core lint: FAIL');
  for (const v of violations) console.error('  ' + v);
  process.exit(1);
}

console.log(`rad core lint: clean (${walk(RAD).length} files)`);
