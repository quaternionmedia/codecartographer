import m from 'mithril';
import { MeiosisCell } from 'meiosis-setup/types';

export interface ICell extends MeiosisCell<State> {}

export interface DebugOptions {
  menu?: boolean;
  tracer?: boolean;
}

export interface Configurations {
  processor_url?: string;
}

export interface State {
  debug: DebugOptions;
  configurations: Configurations;
  container?: any;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  repo_data: m.Vnode[];
  directory_content: m.Vnode[];
  upload_content: m.Vnode[];
  graph_content: m.Vnode[];
  selected_url_file: string;
  selected_uploaded_file?: File;
  uploaded_files: File[];
  showDirectoryNav: boolean;
  showUploadNav: boolean;
}

export const InitialState: State = {
  debug: {
    menu: false,
    tracer: false,
  },
  configurations: {
    processor_url: 'http://localhost:2020',
  },
  repo_url: '',
  repo_owner: '',
  repo_name: '',
  repo_data: [],
  directory_content: [],
  selected_url_file: '',
  uploaded_files: [],
  upload_content: [],
  graph_content: [],
  showDirectoryNav: false,
  showUploadNav: false,
};

export class StateController {
  public static clearGithubData(cell: ICell) {
    cell.state.repo_url = '';
    cell.state.repo_owner = '';
    cell.state.repo_name = '';
    cell.state.repo_data = [];
    cell.state.directory_content = [];
  }
  public static clearAllFileData(cell: ICell) {
    cell.state.uploaded_files = [];
    cell.state.upload_content = [];
    cell.state.selected_uploaded_file = undefined;
  }
  public static clearSelectedFile(cell: ICell) {
    cell.state.selected_uploaded_file = undefined;
  }
  public static clearGraphContent(cell: ICell) {
    cell.state.graph_content = [];
  }

  /** Clear all data from the cell */
  public static clear(cell: ICell) {
    this.clearGithubData(cell);
    this.clearAllFileData(cell);
    this.clearGraphContent(cell);
  }

  /** Update the cell with the new content */
  public static update(cell: ICell, state: Partial<State>) {
    cell.update(state);
  }
}
