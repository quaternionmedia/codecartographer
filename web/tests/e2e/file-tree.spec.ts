/**
 * The Files panel: one line per file, and a folder a large repository left
 * unread opens when it is clicked.
 *
 * A file's entry is its name, and a raw link only when the file has a web
 * address; a file read from disk has a disk path, which no browser page can
 * open. The entry's one-line layout is CSS, so only a browser shows it.
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

import { expect, test, type Page } from '@playwright/test';

import { dismissOnboardingModal } from './helpers';

const REPO = 'https://github.com/example/large';

/** Open `url` with its tree stubbed as `files` at the root, and the graph's stream ended at once. */
async function openStubbedTree(page: Page, url: string, files: { name: string; url: string }[]): Promise<void> {
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'small', url },
        size: files.length,
        root: { name: '', size: 0, folders: [], files: files.map((f) => ({ ...f, size: 1, raw: '' })) },
        is_partial: false,
      },
    },
  }));
  await page.route('**/parse/stream-url', (route) => route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body: 'event: error\ndata: {"message": "stubbed"}\n\n',
  }));
  await page.goto('/');
  await dismissOnboardingModal(page);
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
  await page.locator('.panel-source__url-input input').fill(url);
  await page.locator('.panel-source__url-input button.primary').click();
}

/** Each listed file's entry height over its name's: 1 when the entry is one line. */
async function entryLines(page: Page): Promise<number[]> {
  const entries = page.locator('.gl-panel--file-tree .file_container');
  await expect(entries.first()).toBeVisible();
  return entries.evaluateAll((els) => els.map((el) =>
    Math.round(el.getBoundingClientRect().height / (el.querySelector('.file') as HTMLElement).getBoundingClientRect().height),
  ));
}

test("a GitHub file's raw link sits on its name's line", async ({ page }) => {
  await openStubbedTree(page, 'https://github.com/example/small', [
    { name: 'Cargo.toml', url: 'https://raw.githubusercontent.com/example/small/main/Cargo.toml' },
    { name: 'README.md', url: 'https://raw.githubusercontent.com/example/small/main/README.md' },
  ]);
  const tree = page.locator('.gl-panel--file-tree');
  await expect(tree.locator('.file_raw_btn')).toHaveCount(2);
  await expect(tree.locator('.file_raw_btn').first())
    .toHaveAttribute('href', 'https://raw.githubusercontent.com/example/small/main/Cargo.toml');
  // Mutation: drop the entry's one-line layout -- each raw link drops to a
  // line of its own under its file, and this fails.
  expect(await entryLines(page)).toEqual([1, 1]);
});

test('a file read from disk is listed by its name alone', async ({ page }) => {
  await openStubbedTree(page, '/work/small', [
    { name: 'Cargo.toml', url: '/work/small/Cargo.toml' },
    { name: 'README.md', url: '/work/small/README.md' },
  ]);
  const tree = page.locator('.gl-panel--file-tree');
  await expect(tree.locator('.file')).toHaveText(['Cargo.toml', 'README.md']);
  // A disk path is no address a browser page can open.
  // Mutation: draw the raw link for every file again -- this fails.
  await expect(tree.locator('.file_raw_btn')).toHaveCount(0);
  expect(await entryLines(page)).toEqual([1, 1]);
});

test('a name cut short is titled whole', async ({ page }) => {
  // Not run with the change that added it: the browser suites bind fixed
  // ports this workstation shares. tree-rows.test.mjs holds the title.
  const names = ['test_streaming_renderer_fit_after_stream.ts', 'test_streaming_renderer_fit_after_relayout.ts'];
  await openStubbedTree(page, '/work/small', names.map((name) => ({ name, url: `/work/small/${name}` })));
  const files = page.locator('.gl-panel--file-tree .file');
  await expect(files).toHaveCount(2);
  // Mutation: drop the row's title -- both read alike once cut, and this fails.
  for (const [i, name] of names.entries()) {
    await expect(files.nth(i)).toHaveAttribute('title', name);
  }
});

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
  await page.locator('.lm_tab', { hasText: 'Open' }).click();
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
