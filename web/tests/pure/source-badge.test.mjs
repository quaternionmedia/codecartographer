/**
 * The badge naming a node's file is drawn beside the point it was opened
 * from, and none of it outside the window.
 *
 * **THE DEFECT THIS PINS.** The badge was placed 8px right of the pointer on
 * one line, and a path read from disk is most of a window wide: a
 * double-click on a node right of the window's middle drew it past the right
 * edge, cutting off the file's name and the line. view-source.spec.ts saw it
 * as a badge 756px wide at x 557 in a 1280px window.
 *
 *   npm run test:pure
 */

import assert from 'node:assert/strict';
import { test } from 'node:test';

import { BADGE_MARGIN, badgePlace } from '../../dist-pure/features/graph/services/source_badge.js';

const WINDOW = { width: 1280, height: 720 };
const LINE = 23;

/** The badge's box, from what `badgePlace` returns. */
function box(at, badge, viewport = WINDOW) {
  const { left, top } = badgePlace(at, badge, viewport);
  return { left, top, right: left + badge.width, bottom: top + badge.height };
}

test('a badge with room is drawn just right of the point and above it', () => {
  assert.deepEqual(badgePlace({ x: 300, y: 300 }, { width: 200, height: LINE }, WINDOW),
    { left: 308, top: 300 - 6 - LINE });
});

test('a badge that would run past the right edge is moved left to keep the margin', () => {
  /* Mutation: place it at the point plus 8px, as the renderer did -- its
     right edge is 1312.8, past the window's 1280, and this fails. */
  const drawn = box({ x: 549, y: 311 }, { width: 755.8, height: LINE });
  assert.equal(drawn.right, WINDOW.width - BADGE_MARGIN);
  assert.ok(drawn.left >= BADGE_MARGIN);
});

test('a badge opened at the top of the window is moved down into it', () => {
  /* A dispatched event carries no position: the badge was drawn at top -28. */
  const drawn = box({ x: 0, y: 0 }, { width: 400, height: LINE });
  assert.equal(drawn.top, BADGE_MARGIN);
  assert.equal(drawn.left, 8);
});

test('a badge moved down over the point it was opened from is put below the point', () => {
  /* Mutation: leave it where moving it down puts it -- its box holds the
     point, and this fails. The badge takes the pointer, for its title. */
  const at = { x: 1180, y: 15 };
  const drawn = box(at, { width: 400, height: LINE });
  const over = at.x >= drawn.left && at.x <= drawn.right && at.y >= drawn.top && at.y <= drawn.bottom;
  assert.equal(over, false, JSON.stringify(drawn));
  assert.ok(drawn.top > at.y, JSON.stringify(drawn));
  assert.equal(drawn.right, WINDOW.width - BADGE_MARGIN);
});

test('a badge opened past the bottom or right of the window is moved back into it', () => {
  const drawn = box({ x: 2000, y: 2000 }, { width: 400, height: LINE });
  assert.equal(drawn.right, WINDOW.width - BADGE_MARGIN);
  assert.equal(drawn.bottom, WINDOW.height - BADGE_MARGIN);
});

test('a badge as wide as the window allows starts at the left margin, wherever it is opened', () => {
  /* The renderer bounds the badge's width to the window less both margins
     and lets the path wrap. */
  const width = WINDOW.width - 2 * BADGE_MARGIN;
  for (const x of [0, 640, 1279]) {
    const drawn = box({ x, y: 400 }, { width, height: 3 * LINE });
    assert.equal(drawn.left, BADGE_MARGIN);
    assert.equal(drawn.right, WINDOW.width - BADGE_MARGIN);
  }
});
