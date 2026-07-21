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
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
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
