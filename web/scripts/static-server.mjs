/**
 * A plain static server, with each folder mounted at a path: what the browser
 * tests serve the built page without a server from, the way GitHub Pages
 * serves it, from a subfolder of an origin.
 *
 *   node scripts/static-server.mjs <port> /codecartographer=dist-view /qm/show=tests/e2e/fixtures/show
 *
 * It answers files and nothing else: no route, no proxy, no fallback page. A
 * folder is answered with its `index.html`. Bound to loopback.
 */

import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, resolve, sep } from 'node:path';

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
};

const [port, ...mounts] = process.argv.slice(2);
const table = mounts.map((mount) => {
  const [at, folder] = mount.split('=');
  return { at: at.replace(/\/$/, ''), folder: resolve(folder) };
});

createServer(async (request, response) => {
  const path = decodeURIComponent(new URL(request.url ?? '/', 'http://localhost').pathname);
  for (const { at, folder } of table) {
    if (path !== at && !path.startsWith(`${at}/`)) continue;
    let file = resolve(join(folder, path.slice(at.length)));
    if (file !== folder && !file.startsWith(folder + sep)) break;
    try {
      if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
      const body = await readFile(file);
      response.writeHead(200, { 'content-type': TYPES[extname(file)] ?? 'application/octet-stream' });
      response.end(body);
      return;
    } catch {
      break;
    }
  }
  response.writeHead(404, { 'content-type': 'text/plain' });
  response.end('not found');
}).listen(Number(port), '127.0.0.1');
