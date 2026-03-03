/** Holds all the api endpoints */
export class API {
  private _base: string;
  private _parser: string = 'parser';
  private _palette: string = 'palette';
  private _plotter: string = 'plotter';
  private _polygraph: string = 'polygraph';
  private _repoReader: string = 'repo';
  private _cParser: string = 'c-parser';
  private _parse: string = 'parse';

  constructor(base: string) {
    this._base = base;
  }

  get base(): string {
    return `${this._base}`;
  }

  get parser(): string {
    return `${this._base}/${this._parser}`;
  }

  get palette(): string {
    return `${this._base}/${this._palette}`;
  }

  get plotter(): string {
    return `${this._base}/${this._plotter}`;
  }

  get polygraph(): string {
    return `${this._base}/${this._polygraph}`;
  }

  get repoReader(): string {
    return `${this._base}/${this._repoReader}`;
  }

  get cParser(): string {
    return `${this._base}/${this._cParser}`;
  }

  get parse(): string {
    return `${this._base}/${this._parse}`;
  }
}
