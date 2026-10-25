/**
 * A folder a large repository left unread opens when it is clicked.
 *
 * A repository over the server's size threshold arrives with its folders
 * unread (`is_partial`), and the toast that says so tells the reader to click
 * a folder to expand it. The Files panel has to hand the folder its expand
 * handler for that to do anything.
 *
 * The repository is stubbed at the browser: a real one large enough to be
 * partial is tens of megabytes of network, and what is under test is the
 * panel's wiring, not GitHub.
 */

import { expect, test } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const REPO = 'https://github.com/example/large';

test('an unread folder in a partial tree reads itself on click', async ({ page }) => {
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'large', url: REPO },
        size: 1,
        root: { name: '', size: 0, files: [], folders: [{ name: 'src', size: 0, files: [], folders: [] }] },
        is_partial: true,
      },
    },
  }));
  const asked: string[] = [];
  await page.route('**/repo/subtree?**', (route) => {
    asked.push(new URL(route.request().url()).searchParams.get('path') ?? '');
    return route.fulfill({
      json: {
        status: 200,
        message: 'stubbed',
        results: {
          name: 'src', size: 12, folders: [],
          files: [{ name: 'main.py', size: 12, raw: '', url: `${REPO}/raw/main/src/main.py` }],
        },
      },
    });
  });
  // The graph is not under test; the stream ends at once.
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: 'event: error\ndata: {"message": "stubbed"}\n\n',
  }));

  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill(REPO);
  await page.locator('.panel-source__url-input button.primary').click();

  const tree = page.locator('.gl-panel--file-tree');
  const src = tree.locator('.folder_button', { hasText: 'src' });
  // Mutation: do not pass the expand handler -- the folder is drawn as empty,
  // with no `…` and no click, and this fails.
  await expect(src.locator('.folder_stub_indicator')).toBeVisible();
  await src.click();
  await expect(tree).toContainText('main.py');
  expect(asked).toEqual(['src']);
});

test('a folder whose read failed stops loading and reads again on the next click', async ({ page }) => {
  // Not run with the change that added it: the browser suites bind fixed
  // ports this workstation shares. stub-read.test.mjs holds the same order.
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'large', url: REPO },
        size: 1,
        root: { name: '', size: 0, files: [], folders: [{ name: 'src', size: 0, files: [], folders: [] }] },
        is_partial: true,
      },
    },
  }));
  let answered = 0;
  await page.route('**/repo/subtree?**', (route) => {
    answered++;
    // The first read is refused as a submodule's path is: the route raises
    // GithubNoDataError and FastAPI answers with its detail alone.
    if (answered === 1) {
      return route.fulfill({ status: 404, json: { detail: 'GithubNoDataError: Expected directory listing' } });
    }
    return route.fulfill({
      json: {
        status: 200,
        message: 'stubbed',
        results: {
          name: 'src', size: 12, folders: [],
          files: [{ name: 'main.py', size: 12, raw: '', url: `${REPO}/raw/main/src/main.py` }],
        },
      },
    });
  });
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: 'event: error\ndata: {"message": "stubbed"}\n\n',
  }));

  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Repository' }).click();
  await page.locator('.panel-source__url-input input').fill(REPO);
  await page.locator('.panel-source__url-input button.primary').click();

  const tree = page.locator('.gl-panel--file-tree');
  const src = tree.locator('.folder_button', { hasText: 'src' });
  await src.click();
  // Mutation: end the spinner only when contents arrive -- it spins for good,
  // and this fails.
  await expect(src.locator('.folder_loading_indicator')).toHaveCount(0);
  await expect(src.locator('.folder_stub_indicator')).toBeVisible();
  await src.click();
  await expect(tree).toContainText('main.py');
  expect(answered).toBe(2);
});
