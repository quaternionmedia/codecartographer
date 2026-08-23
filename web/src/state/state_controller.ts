import { Patch } from 'meiosis-setup/types';
import { RawFile, RawFolder, Directory } from '../components/models/source';
import { DirectoryNavController } from '../components/codecarto/directory/directory_nav';
import { ICell, ICellState } from './cell_state';
import { GraphData } from '../features/graph';
import { API } from './api_base';
import { Vnode } from 'mithril';
import { clearError } from '../utility';
import { logger } from '../core/logger';

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
    const newState = this._cell.getState();
    this._cell.state = newState;
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

  public setSelectedRepoFolder(folder: RawFolder) {
    this.update({ repo: { selectedFolder: folder } });
  }

  public setUploadComponent(component: Vnode[]) {
    this.update({ local: { component: component } });
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
    // **`graphData` TOO, AND AS A REPLACEMENT.** Two defects met here.
    // `clear()` emptied the rendered vnodes and left the *data* behind; and
    // `update` is a mergerino patch, which deep-merges — so `{graphData: next}`
    // merged the new graph into the old one, and `graph.nodes` is an object
    // keyed by node id. Every plot therefore drew the union of itself and
    // everything plotted before it. Switching between two harness topologies
    // made it obvious because they share ids like `in` and `out`; between two
    // repositories it would have looked like an oddly large graph.
    //
    // A function patch replaces instead of merging. See `replaceGraphData`.
    this.update({ graphContent: [], graphData: null });
  }

  /**
   * Set the graph data, replacing whatever was there.
   *
   * **NEVER `update({ graphData })` DIRECTLY.** That is a merge, and a merged
   * graph is the union of every graph ever drawn.
   */
  public replaceGraphData(graphData: GraphData | null) {
    this.update({ graphData: () => graphData } as unknown as Patch<ICellState>);
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
    logger.debug('StateController.updatePlotFrame - updating with frames:', frame.length);
    this.update({ graphContent: frame });
    this.closeNavs();
    logger.debug('StateController.updatePlotFrame - state after update:', this._cell.state.graphContent);
    this.redraw();
  }

  public updateRepoContent(data: Directory) {
    this.setRepoContent(data);
    this.closeUploadNav();
    this.openDirectoryNav();
    this.redraw();
  }
}
