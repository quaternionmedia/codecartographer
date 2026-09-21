import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. Starts both the FastAPI backend and the Vite frontend dev
 * server automatically — most of this app's meaningful behavior (parsing,
 * rendering a real graph) requires a live backend, not just a static page.
 *
 * **THE PORTS ARE NOBODY'S DEFAULTS, AND NOTHING ALREADY LISTENING IS REUSED.**
 * This used to start the backend on 8000 and reuse whatever was already there.
 * On a workstation running several of this org's servers at once, "already
 * there" was regularly another project, and an afternoon was spent measuring
 * it (`governance/qm/handbook/async-contract.md` §4). So: the backend on
 * 27182 and the dev server on 12340 -- digits of e, the constant `qm dashboard`
 * gives this project, and ports no default picks; `reuseExistingServer: false`
 * on both, so a busy port fails the run instead of adopting a stranger; and
 * `tests/e2e/_identity.spec.ts` asks the API what it is before any other spec
 * believes an answer from it.
 *
 * baseURL uses `localhost`, not `127.0.0.1`: the app talks to its API through
 * the dev server's proxy, so the browser sees one origin either way, but the
 * backend's CORS allowlist (codecarto/main.py) names `localhost` and a direct
 * call from `127.0.0.1` would be silently blocked.
 */
const API_PORT = 27182;
const WEB_PORT = 12340;
const API = `http://127.0.0.1:${API_PORT}`;
const WEB = `http://localhost:${WEB_PORT}/codecartographer/`;

export default defineConfig({
  testDir: './tests/e2e',
  // webServer starts exactly one backend process, shared by every test --
  // running workers in parallel means multiple browser sessions hammering
  // that single process concurrently. Verified live: with the default
  // parallel workers, demo-graph.spec.ts's "no unexpected failed requests"
  // assertion flaked consistently (an unrelated request would fail under
  // the added load); serialized runs (`--workers=1`) passed every time.
  // Trading parallel speed for reliability given the shared-backend
  // constraint, not working around a real app bug.
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: WEB,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command:
        `uv run --no-sync uvicorn codecarto.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: '..',
      // The document that names the app, not a page that any server has.
      url: `${API}/openapi.json`,
      reuseExistingServer: false,
      timeout: 60_000,
      // dossier's overview seam, handed over as a fixture so the Overview
      // panel's happy path runs the real route and the real serializer rather
      // than a hand-built graph. The shape is what `dossier overview --json`
      // writes; the names are invented.
      env: { DOSSIER_OVERVIEW_SEAM: 'web/tests/e2e/fixtures/overview.json' },
    },
    {
      command: 'npm run dev',
      url: WEB,
      reuseExistingServer: false,
      timeout: 30_000,
      // The dev server proxies API paths, and this says where to. Stated
      // rather than defaulted: this project has meant four different addresses
      // by "the API", and a panel once sat forever asking a port nothing
      // answered on.
      env: { CODECARTO_API: API, CODECARTO_WEB_PORT: String(WEB_PORT) },
    },
  ],
});
