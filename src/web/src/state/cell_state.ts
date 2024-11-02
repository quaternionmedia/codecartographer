import m from 'mithril';

import { MeiosisCell } from 'meiosis-setup/types';
import { DirectoryController } from '../components/models/source';
import { ConfigManager, DebugManager } from './config_manager';

export interface ICell extends MeiosisCell<ICellState> {}

export interface ICellState {
  debug: DebugManager;
  config: ConfigManager;
  repo: DirectoryController;
  local: DirectoryController;
  graphContent: m.Vnode[];
  inputRepoUrl: string;
  redraw: () => void;
}

// Used for initial app state
export class CellState implements ICellState {
  public debug = new DebugManager();
  public config = new ConfigManager();
  public repo = new DirectoryController(false);
  public local = new DirectoryController(true);
  public graphContent: m.Vnode[] = [];
  public inputRepoUrl: string = '';
  public redraw: () => void = () => {
    m.redraw();
  };

  constructor(inputRepoUrl: string) {
    this.inputRepoUrl = inputRepoUrl;
  }
}
