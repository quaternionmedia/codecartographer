import appSettings from '../appsettings.json';

export class ConfigManager {
  private _baseUrl: string;

  constructor() {
    this._baseUrl = appSettings['backend_url'];
  }

  get backendUrl(): string {
    return this._baseUrl;
  }
}

export class DebugManager {
  public isMenuOpen: boolean;
  public isTracerShown: boolean;

  public toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  public toggleTracer() {
    this.isTracerShown = !this.isTracerShown;
  }
}
