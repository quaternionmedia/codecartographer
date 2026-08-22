import appSettings from '../appsettings.json';

/**
 * Where the API is.
 *
 * **THIS WAS A BUILD-TIME CONSTANT AND IT POINTED AT A PORT NOTHING RAN ON.**
 * `appsettings.json` says `http://127.0.0.1:8000`; the container publishes 2020
 * and the trio runs it on 2718. So a built bundle could only ever talk to one
 * machine's guess, and moving the API meant rebuilding the front end.
 *
 * Resolved in three steps, most specific first:
 *
 * 1. **A meta tag**, when something served this page and knows where its API
 *    is. That is the deployment case: the server injects one line and the
 *    bundle stops guessing.
 * 2. **Same origin**, for a production build with no meta tag — if this page
 *    came from a server, that server is the most likely place its API lives,
 *    and it is certainly a better guess than a port in a checked-in file.
 * 3. **`appsettings.json`**, under `vite dev`, where the app is on 1234 and the
 *    API is genuinely somewhere else. That is the only case the old constant
 *    was ever right for, and it is still right for it.
 */
function resolveBackendUrl(): string {
  const declared = document
    ?.querySelector('meta[name="codecarto-api"]')
    ?.getAttribute('content');
  if (declared) return declared.replace(/\/$/, '');

  // `import.meta.env.DEV` is true only under the dev server. Vite replaces it
  // at build time, so this branch is removed from a production bundle.
  const isDev = Boolean(
    (import.meta as unknown as { env?: { DEV?: boolean } }).env?.DEV,
  );
  if (!isDev && typeof window !== 'undefined' && window.location?.origin
      && window.location.protocol.startsWith('http')) {
    return window.location.origin.replace(/\/$/, '');
  }

  return String(appSettings['backend_url'] ?? '').replace(/\/$/, '');
}

export class ConfigManager {
  private _baseUrl: string;

  constructor() {
    this._baseUrl = resolveBackendUrl();
  }

  get backendUrl(): string {
    return this._baseUrl;
  }
}

export class DebugManager {
  public isMenuOpen: boolean = false;
  public isTracerShown: boolean = false;

  public toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  public toggleTracer() {
    this.isTracerShown = !this.isTracerShown;
  }
}
