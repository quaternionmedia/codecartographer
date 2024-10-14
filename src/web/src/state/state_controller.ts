import { Patch } from 'meiosis-setup/types';
import {
  RawFile,
  RawFolder,
  Directory,
  DirectoryController,
} from '../components/models/source';
import { ICell, ICellState } from './cell_state';
import { API } from './api_base';

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

  get cell(): ICell {
    return this._cell;
  }

  get api(): API {
    return this._api;
  }

  get repo(): DirectoryController {
    return this._cell.state.repo;
  }

  get local(): DirectoryController {
    return this._cell.state.local;
  }

  public update(state: Patch<ICellState>) {
    this._cell.update(state);
    console.log('StateController.update: passed state: \n', state);
    this._cell.update(state);
    console.log('StateController.update: updated state: ', this._cell.state);
  }

  public updateRepoContent(data: Directory) {
    this._cell.state.repo.content = data;
    this.update({ repo: { content: data } });
  }

  public setSelectedRepoFile(file: RawFile) {
    this._cell.state.repo.selectedFile = file;
    this.update({ repo: { selectedFile: file } });
  }

  public setSelectedRepoFolder(folder: RawFolder) {
    this._cell.state.repo.selectedFolder = folder;
    this.update({ repo: { selectedFolder: folder } });
  }

  public setSelectedLocalFile(file: RawFile) {
    this._cell.state.local.selectedFile = file;
    this.update({ local: { selectedFile: file } });
  }

  public setSelectedLocalFolder(folder: RawFolder) {
    this._cell.state.local.selectedFolder = folder;
  }

  public clearSelectedRepoFile() {
    this._cell.state.repo.clearSelectedFile();
  }

  public clearSelectedLocalFile() {
    this._cell.state.local.clearSelectedFile();
  }

  public clearRepoData() {
    this._cell.state.repo.clearContent();
  }

  public clearLocalData() {
    this._cell.state.local.clearContent();
  }

  public clearGraphContent() {
    this._cell.state.graphContent = [];
  }

  public clear() {
    this.clearRepoData();
    this.clearLocalData();
    this.clearGraphContent();
  }

  public toggleDirectoryNav() {
    this._cell.state.repo.toggleNav();
  }

  public toggleUploadNav() {
    this._cell.state.local.toggleNav();
  }

  public toggleNavs() {
    this.toggleDirectoryNav();
    this.toggleUploadNav();
  }
}
