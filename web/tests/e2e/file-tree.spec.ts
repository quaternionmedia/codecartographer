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

/** A folder in a stubbed tree, as the server sends it. */
interface StubFolder {
  name: string;
  size: number;
  files: { name: string; size: number; raw: string; url: string }[];
  folders: StubFolder[];
}

/**
 * Open `url` with its tree stubbed as `files` and `folders` at the root, and
 * the graph's stream ended at once.
 */
async function openStubbedTree(
  page: Page,
  url: string,
  files: { name: string; url: string }[],
  folders: StubFolder[] = [],
): Promise<void> {
  await page.route('**/repo/tree?**', (route) => route.fulfill({
    json: {
      status: 200,
      message: 'stubbed',
      results: {
        info: { owner: 'example', name: 'small', url },
        size: files.length,
        root: { name: '', size: 0, folders, files: files.map((f) => ({ ...f, size: 1, raw: '' })) },
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

/**
 * How many lines each listed file's entry takes: its height over the height
 * of one line of its name, which is a range over the name's first character.
 * A raw link pushed under the name, or a name wrapped, makes it more than 1.
 * (Over the name's own height it was 1 however the name wrapped, as a name
 * that wraps grows with its entry.)
 */
async function entryLines(page: Page): Promise<number[]> {
  const entries = page.locator('.gl-panel--file-tree .file_container');
  await expect(entries.first()).toBeVisible();
  return entries.evaluateAll((els) => els.map((el) => {
    const text = (el.querySelector('.file') as HTMLElement).firstChild as Text;
    const line = document.createRange();
    line.setStart(text, 0);
    line.setEnd(text, 1);
    return Math.round(el.getBoundingClientRect().height / line.getBoundingClientRect().height);
  }));
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

test('a file read from disk is listed by its name alone, on one line however long', async ({ page }) => {
  const LONG = 'notes on why the streaming renderer fits again after a relayout.md';
  await openStubbedTree(page, '/work/small', [
    { name: 'Cargo.toml', url: '/work/small/Cargo.toml' },
    { name: LONG, url: `/work/small/${LONG}` },
  ]);
  const tree = page.locator('.gl-panel--file-tree');
  await expect(tree.locator('.file')).toHaveText(['Cargo.toml', LONG]);
  // A disk path is no address a browser page can open.
  // Mutation: draw the raw link for every file again -- this fails.
  await expect(tree.locator('.file_raw_btn')).toHaveCount(0);
  // A tree narrower than the long name, which has spaces to wrap at.
  await tree.locator('.gl-file-tree__tree').evaluate((el) => { (el as HTMLElement).style.width = '12em'; });
  // Mutation: let a name wrap (drop .file's white-space: nowrap) -- the long
  // one takes several lines, and this fails.
  expect(await entryLines(page)).toEqual([1, 1]);
});

test('a name cut short is titled whole', async ({ page }) => {
  // tree-rows.test.mjs holds the title; this sees it on the drawn row.
  const names = ['test_streaming_renderer_fit_after_stream.ts', 'test_streaming_renderer_fit_after_relayout.ts'];
  await openStubbedTree(page, '/work/small', names.map((name) => ({ name, url: `/work/small/${name}` })));
  const files = page.locator('.gl-panel--file-tree .file');
  await expect(files).toHaveCount(2);
  // Mutation: drop the row's title -- both read alike once cut, and this fails.
  for (const [i, name] of names.entries()) {
    await expect(files.nth(i)).toHaveAttribute('title', name);
  }
});

test("each folder's contents sit a step in from its name", async ({ page }) => {
  // tree-indent.test.mjs reads the step from the stylesheet; this sees it drawn.
  const RAW = 'https://raw.githubusercontent.com/example/small/main';
  const crate = (name: string): StubFolder => ({
    name, size: 1, files: [], folders: [{
      name: 'src', size: 1, folders: [],
      files: [{ name: 'lib.rs', size: 1, raw: '', url: `${RAW}/crates/${name}/src/lib.rs` }],
    }],
  });
  await openStubbedTree(page, 'https://github.com/example/small',
    [{ name: 'Cargo.toml', url: `${RAW}/Cargo.toml` }],
    [{ name: 'crates', size: 2, files: [], folders: [crate('a'), crate('b')] }]);
  const tree = page.locator('.gl-panel--file-tree');
  await tree.locator('.folder__crates > .folder_button').click();
  for (const name of ['a', 'b']) {
    await tree.locator(`.folder__${name} > .folder_button`).click();
    await tree.locator(`.folder__${name} .folder__src > .folder_button`).click();
  }
  await expect(tree.locator('.file', { hasText: 'lib.rs' })).toHaveCount(2);
  // Each offsetLeft summed up its offset parents to the page, as the press's
  // scale and the entries' slide-in transform the rows' boxes while they run,
  // and a file's own offsetLeft is from its .file_container, a folder's from
  // the content holding it.
  const left = (selector: string) => tree.locator(selector).first()
    .evaluate((el) => {
      let x = 0;
      for (let e: HTMLElement | null = el as HTMLElement; e; e = e.offsetParent as HTMLElement | null) {
        x += e.offsetLeft;
      }
      return x;
    });
  const root = await left('.folder__crates > .folder_button');
  const crateRow = await left('.folder__a > .folder_button');
  const srcRow = await left('.folder__a .folder__src > .folder_button');
  const libA = await left('.folder__a .file');
  // Mutation: drop .folder_content's step -- every level is at one x, and this fails.
  expect(await left('.directory_content > .files .file')).toBe(root); // Cargo.toml
  expect(crateRow).toBeGreaterThan(root);
  expect(srcRow).toBeGreaterThan(crateRow);
  expect(libA).toBeGreaterThan(srcRow);
  expect(await left('.folder__b .file')).toBe(libA);
});

test('the tree is pressed from the keyboard, and a raw link says which file it opens', async ({ page }) => {
  // tree-rows.test.mjs holds the rows' roles, keys and names; this presses them.
  const RAW = 'https://raw.githubusercontent.com/example/small/main';
  const fetched: string[] = [];
  await page.route(`${RAW}/**`, (route) => {
    fetched.push(route.request().url());
    return route.fulfill({ headers: { 'access-control-allow-origin': '*' }, body: 'pub fn f() {}\n' });
  });
  await openStubbedTree(page, 'https://github.com/example/small', [], [
    { name: 'src', size: 1, folders: [], files: [{ name: 'lib.rs', size: 1, raw: '', url: `${RAW}/src/lib.rs` }] },
  ]);
  const tree = page.locator('.gl-panel--file-tree');
  const folder = tree.getByRole('button', { name: 'src' });
  await expect(folder).toHaveAttribute('aria-expanded', 'false');
  // Mutation: drop the rows' role, tabindex or key handler -- this fails.
  await folder.focus();
  await page.keyboard.press('Enter');
  await expect(folder).toHaveAttribute('aria-expanded', 'true');
  await page.keyboard.press('Tab');
  await expect(tree.getByRole('button', { name: 'lib.rs' })).toBeFocused();
  // Mutation: leave the link named "raw" alone -- this fails.
  await expect(tree.getByRole('link', { name: 'raw contents of src/lib.rs' }))
    .toHaveAttribute('href', `${RAW}/src/lib.rs`);
  // Space draws the file as a click does, which first fetches its contents.
  await page.keyboard.press('Space');
  await expect.poll(() => fetched).toEqual([`${RAW}/src/lib.rs`]);
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
  // stub-read.test.mjs holds the same order.
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
