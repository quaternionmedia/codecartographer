import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. Starts both the FastAPI backend and the Vite frontend dev
 * server automatically — most of this app's meaningful behavior (parsing,
 * rendering a real graph) requires a live backend, not just a static page.
 *
 * baseURL uses `localhost`, not `127.0.0.1`: the backend's CORS allowlist
 * (codecarto/main.py) only lists `http://localhost:1234`/`1235` — the two
 * resolve to the same machine but are different CORS origins, and
 * `127.0.0.1` gets silently blocked.
 */
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
    baseURL: 'http://localhost:1234/codecartographer/',
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
        'uv run uvicorn codecarto.main:app --host 127.0.0.1 --port 8000',
      cwd: '..',
      url: 'http://127.0.0.1:8000/docs',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:1234/codecartographer/',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
});
