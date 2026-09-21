/**
 * Before any spec believes an answer, the API is asked what it is.
 *
 * A port answering proves that something listens. The suite starts its own
 * backend on a port nobody's default picks and refuses to reuse a stranger's,
 * and this spec closes the last gap: the document behind the dev server's
 * proxy must name this application. Runs first because of the underscore --
 * files run in path order -- so a wrong server fails here with its own name in
 * the message rather than as a mystery three specs later.
 */

import { expect, test } from '@playwright/test';

test('the API behind the dev server is codecarto', async ({ request, baseURL }) => {
  const origin = new URL(baseURL ?? 'http://localhost/').origin;
  const answer = await request.get(`${origin}/openapi.json`);
  expect(answer.ok(), `openapi.json at ${origin} answered ${answer.status()}`).toBe(true);
  const document = await answer.json();
  expect(document.info?.title, `something else is answering at ${origin}: ${JSON.stringify(document.info)}`)
    .toBe('codecarto');
});
