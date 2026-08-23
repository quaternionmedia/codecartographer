import { test, expect } from '@playwright/test';
import { dismissOnboardingModal } from './helpers';

test('Load Demo renders a real graph with no console errors', async ({ page }) => {
  const consoleErrors: string[] = [];
  const failedRequestUrls: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`));
  page.on('requestfailed', (request) => failedRequestUrls.push(request.url()));

  await page.goto('/');
  await dismissOnboardingModal(page);
  consoleErrors.length = 0;
  failedRequestUrls.length = 0;

  await page.getByRole('button', { name: /Load Demo/i }).first().click();

  // The demo graph renders via the same D3/streaming node rendering path
  // as every real repo plot — `.graph-node` is the class both renderers
  // apply to every node element (graph_renderer.ts, streaming_renderer.ts).
  await expect(page.locator('.graph-node').first()).toBeVisible({ timeout: 15_000 });
  const nodeCount = await page.locator('.graph-node').count();
  expect(nodeCount).toBeGreaterThan(0);

  // Known, pre-existing, environment-dependent gap (not fixed here, out of
  // scope for adding E2E coverage): Graphbase's /db/bookmarks and
  // /db/snapshots auto-load on every plot. MONGODB_URI defaults to
  // localhost:27017 with no reachability check, so the router mounts
  // unconditionally; with no local MongoDB running (the common case for a
  // dev/CI environment that doesn't use Graphbase), the handler throws an
  // unhandled ServerSelectionTimeoutError -> 500 with no CORS headers,
  // which the browser reports as a failed request. Correlated against the
  // actual failed request URLs (not fragile console-text matching) so a
  // *different*, genuinely new failure still fails this test.
  const isKnownGraphbaseGap = (url: string) => /\/db\/(bookmarks|snapshots)/.test(url);
  const unexpectedFailedRequests = failedRequestUrls.filter((u) => !isKnownGraphbaseGap(u));
  expect(unexpectedFailedRequests).toEqual([]);

  const isBoilerplateForFailedRequest = (msg: string) =>
    msg === 'Failed to load resource: net::ERR_FAILED' || /CORS policy/.test(msg);
  const unexpectedConsoleErrors = consoleErrors.filter((e) => !isBoilerplateForFailedRequest(e));
  expect(unexpectedConsoleErrors).toEqual([]);
});
