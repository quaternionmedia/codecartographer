// Time how long Chromium takes to draw each picture of a show export, and to
// open each built page that embeds one: the half of `codecarto show measure`
// that depends on the machine (codecarto/services/show_measure.py is the rest).
//
//   node scripts/measure-draw.mjs SHOW_DIR OUT.json [SITE_DIR]
//
// Every file is served from disk at a made-up origin and every other request
// is refused, so nothing comes from the network and no server is started. A
// picture is fetched once, then drawn RUNS times from a fresh object URL --
// decoded, put on the page at its own size and two frames let pass -- and the
// median is kept. A page is opened RUNS times, each in a fresh context so no
// picture is drawn from a cache; its time runs from navigation until its eager
// pictures are decoded and two frames have passed.
import { chromium } from '@playwright/test';
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { cpus, platform, release, totalmem } from 'node:os';
import { extname, join, relative, resolve, sep } from 'node:path';

const [showArg, outArg, siteArg] = process.argv.slice(2);
if (!showArg || !outArg) {
  console.error('usage: node scripts/measure-draw.mjs SHOW_DIR OUT.json [SITE_DIR]');
  process.exit(2);
}
const RUNS = 3;
const ORIGIN = 'http://measure.invalid';
const SHOW = resolve(showArg);
const SITE = siteArg ? resolve(siteArg) : null;
const TYPES = {
  '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.html': 'text/html',
  '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2',
};

function files(dir, suffix) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return files(path, suffix);
    return path.endsWith(suffix) ? [path] : [];
  });
}

const key = (root, path) => relative(root, path).split(sep).join('/');
const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

/** What a path on the made-up origin names on disk: `/__show/...` the export, anything else the site. */
function onDisk(pathname) {
  const path = decodeURIComponent(pathname);
  if (path === '/__blank') return null;
  const file = path.startsWith('/__show/') ? join(SHOW, path.slice('/__show/'.length)) : join(SITE ?? SHOW, path);
  try {
    return statSync(file).isDirectory() ? join(file, 'index.html') : file;
  } catch {
    return undefined;
  }
}

async function context(browser) {
  const made = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  await made.route('**/*', (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== ORIGIN) return route.abort();
    const file = onDisk(url.pathname);
    if (file === null) return route.fulfill({ status: 200, contentType: 'text/html', body: '<!doctype html><body style="margin:0">' });
    if (!file) return route.fulfill({ status: 404, body: '' });
    let body;
    try {
      body = readFileSync(file);
    } catch {
      return route.fulfill({ status: 404, body: '' });
    }
    return route.fulfill({ status: 200, body, contentType: TYPES[extname(file)] ?? 'application/octet-stream' });
  });
  return made;
}

const browser = await chromium.launch();
const result = {
  machine: {
    cpu: cpus()[0]?.model?.trim(), cores: cpus().length, memory_gb: Math.round(totalmem() / 2 ** 30),
    os: `${platform()} ${release()}`, browser: `chromium ${browser.version()}`,
  },
  runs: RUNS, pictures: {}, pages: {},
};

const blank = await (await context(browser)).newPage();
await blank.goto(`${ORIGIN}/__blank`);
for (const path of files(SHOW, '.svg').sort()) {
  const name = key(SHOW, path);
  const runs = await blank.evaluate(async ({ src, runs }) => {
    const blob = await (await fetch(src)).blob();
    const out = [];
    for (let i = 0; i < runs; i++) {
      const url = URL.createObjectURL(blob);
      const img = new Image();
      const start = performance.now();
      img.src = url;
      await img.decode();
      document.body.append(img);
      await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
      out.push(performance.now() - start);
      img.remove();
      URL.revokeObjectURL(url);
    }
    return out;
  }, { src: `${ORIGIN}/__show/${name}`, runs: RUNS });
  result.pictures[name] = Math.round(median(runs));
  console.error(`${name}  ${result.pictures[name]} ms`);
}

if (SITE) {
  const embeds = /<img\b[^>]*\bsrc="[^"]*show\/[^"]+"/;
  for (const path of files(SITE, '.html').sort()) {
    if (!embeds.test(readFileSync(path, 'utf8'))) continue;
    const name = key(SITE, path);
    const runs = [];
    for (let i = 0; i < RUNS; i++) {
      const fresh = await context(browser);
      const page = await fresh.newPage();
      await page.goto(`${ORIGIN}/${name}`, { waitUntil: 'load' });
      runs.push(await page.evaluate(async () => {
        const eager = [...document.images].filter((img) => img.loading !== 'lazy' && img.src.includes('/show/'));
        await Promise.all(eager.map((img) => img.decode().catch(() => undefined)));
        await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
        return performance.now();
      }));
      await fresh.close();
    }
    result.pages[name] = Math.round(median(runs));
    console.error(`${name}  ${result.pages[name]} ms`);
  }
}

await browser.close();
writeFileSync(outArg, JSON.stringify(result, null, 1) + '\n');
