/** Holds all the api endpoints */
export class API {
  private _base: string;
  private _palette: string = 'palette';
  private _plotter: string = 'plotter';
  private _repoReader: string = 'repo';
  private _parse: string = 'parse';
  private _lexicon: string = 'lexicon';

  constructor(base: string) {
    this._base = base;
  }

  get base(): string {
    return `${this._base}`;
  }

  get palette(): string {
    return `${this._base}/${this._palette}`;
  }

  get plotter(): string {
    return `${this._base}/${this._plotter}`;
  }

  get repoReader(): string {
    return `${this._base}/${this._repoReader}`;
  }

  get parse(): string {
    return `${this._base}/${this._parse}`;
  }

  get lexicon(): string {
    return `${this._base}/${this._lexicon}`;
  }

  get db(): string {
    return `${this._base}/db`;
  }

  get authGithub(): string {
    return `${this._base}/auth/github`;
  }
}
