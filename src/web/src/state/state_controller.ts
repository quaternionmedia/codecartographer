import { Patch } from 'meiosis-setup/types';
import {
  RawFile,
  RawFolder,
  Directory,
  DirectoryController,
} from '../components/models/source';
import { ICell, ICellState } from './cell_state';
import { API } from './api_base';
import { Vnode } from 'mithril';

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
    console.log('StateController.update - updated state: ', this._cell.state);
  }

  public redraw() {
    this._cell.state.redraw();
  }

  // Getter methods

  // TODO: At some point, we may hide the cell
  //       and expose the state directly
  get cell(): ICell {
    return this._cell;
  }

  get api(): API {
    return this._api;
  }

  get repo(): DirectoryController {
    this._cell.state = this._cell.getState();
    return this._cell.state.repo;
  }

  get local(): DirectoryController {
    this._cell.state = this._cell.getState();
    return this._cell.state.local;
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

  public clear() {
    this.clearRepoData();
    this.clearLocalData();
    this.clearGraphContent();
  }

  // Toggle methods

  public toggleDirectoryNav() {
    let currIsOpen = this._cell.state.repo.isMenuOpen;
    this.update({ repo: { isMenuOpen: !currIsOpen } });
  }

  public toggleUploadNav() {
    let currIsOpen = this._cell.state.local.isMenuOpen;
    this.update({ local: { isMenuOpen: !currIsOpen } });
  }

  public toggleNavs() {
    this.toggleDirectoryNav();
    this.toggleUploadNav();
  }
}
