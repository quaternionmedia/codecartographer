import { Patch } from 'meiosis-setup/types';
import { RawFile, RawFolder, Directory } from '../components/models/source';
import { DirectoryNavController } from '../components/codecarto/directory/directory_nav';
import { ICell, ICellState } from './cell_state';
import { API } from './api_base';
import { Vnode } from 'mithril';
import { clearError } from '../utility';

/**
 * The state controller tracks the state of the application.
 * * toggles the applications navigation menus
 * * holds and updates the current cell state
 * * holds the API endpoints
 */
export class StateController {
  private _cell: ICell;
  private _api: API;

  constructor(cell: ICell) {
    this._cell = cell;
    this._api = new API(this._cell.state.config.backendUrl);
  }

  public update(state: Patch<ICellState>) {
    this._cell.update(state);
    this._cell.state = this._cell.getState();
    //console.log('StateController.update - updated state: ', this._cell.state);
  }

  public redraw() {
    this._cell.state.redraw();
  }

  // Getter methods
  get api(): API {
    return this._api;
  }

  get state(): ICellState {
    return this._cell.state;
  }

  get repo(): DirectoryNavController {
    return this.state.repo;
  }

  get local(): DirectoryNavController {
    return this.state.local;
  }

  // Setter methods
  public setRepoContent(data: Directory) {
    this.update({ repo: { content: data } });
  }

  public setDirectoryComponent(component: Vnode[]) {
    this.update({ repo: { component: component } });
  }

  public setSelectedRepoFile(file: RawFile) {
    this.update({ repo: { selectedFile: file } });
  }

  public setSelectedRepoFolder(folder: RawFolder) {
    this.update({ repo: { selectedFolder: folder } });
  }

  public setUploadComponent(component: Vnode[]) {
    this.update({ local: { component: component } });
  }

  public setSelectedLocalFile(file: RawFile) {
    this.update({ local: { selectedFile: file } });
  }

  public setSelectedLocalFolder(folder: RawFolder) {
    this.update({ local: { selectedFolder: folder } });
  }

  // Clear methods
  public clearSelectedRepoFile() {
    this.update({ repo: { selectedFile: new RawFile() } });
  }

  public clearSelectedLocalFile() {
    this.update({ local: { selectedFile: new RawFile() } });
  }

  public clearRepoData() {
    this.update({ repo: { content: new Directory() } });
  }

  public clearLocalData() {
    this.update({ local: { content: new Directory() } });
  }

  public clearGraphContent() {
    this.update({ graphContent: [] });
  }

  /** Clear the graph and optionally the repo and uploaded files */
  public clear(clearRepo: boolean = false, clearLocal: boolean = false) {
    clearError();
    if (clearRepo) this.clearRepoData();
    if (clearLocal) this.clearLocalData();
    this.clearGraphContent();
    this.redraw();
  }

  // Nav Methods
  public toggleDirectoryNav() {
    let currIsOpen = this.repo.isMenuOpen;
    this.update({ repo: { isMenuOpen: !currIsOpen } });
  }

  public toggleUploadNav() {
    let currIsOpen = this.local.isMenuOpen;
    this.update({ local: { isMenuOpen: !currIsOpen } });
  }

  public openDirectoryNav() {
    this.update({ repo: { isMenuOpen: true } });
  }

  public openUploadNav() {
    this.update({ local: { isMenuOpen: true } });
  }

  public openNavs() {
    this.openDirectoryNav();
    this.openUploadNav();
  }

  public closeDirectoryNav() {
    this.update({ repo: { isMenuOpen: false } });
  }

  public closeUploadNav() {
    this.update({ local: { isMenuOpen: false } });
  }

  public closeNavs() {
    this.closeDirectoryNav();
    this.closeUploadNav();
  }

  // Specific Control Methods
  public updatePlotFrame(frame: Vnode[]) {
    this.update({ graphContent: frame });
    this.closeNavs();
    this.redraw();
  }

  public updateRepoContent(data: Directory) {
    this.setRepoContent(data);
    this.closeUploadNav();
    this.openDirectoryNav();
    this.redraw();
  }
}
