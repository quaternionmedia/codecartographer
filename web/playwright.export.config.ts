import { defineConfig, devices } from '@playwright/test';

/**
 * `codecarto show export`'s harness: the browser suite's two servers, on ports
 * of their own, driving the real window over the subjects a manifest names
 * (`tests/export/`). Run through the command, which writes the manifest and
 * checks what this leaves; on its own it finds no manifest and draws nothing.
 *
 * The backend reads the corpus `CODECARTO_CORPUS` names, which the command
 * sets; it inherits the environment, as the browser suite's does.
 */
const API_PORT = 27184;
const WEB_PORT = 12344;
const API = `http://127.0.0.1:${API_PORT}`;
const WEB = `http://localhost:${WEB_PORT}/codecartographer/`;

export default defineConfig({
  testDir: './tests/export',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 300_000,
  reporter: 'line',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: WEB,
  },
  webServer: [
    {
      command: `uv run --no-sync uvicorn codecarto.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: '..',
      url: `${API}/openapi.json`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm run dev',
      url: WEB,
      reuseExistingServer: false,
      timeout: 30_000,
      env: { CODECARTO_API: API, CODECARTO_WEB_PORT: String(WEB_PORT) },
    },
  ],
});
