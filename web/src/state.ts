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
  plot_repo_url: string;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  repo_data: m.Vnode[];
  directory_content: m.Vnode[];
  upload_content: m.Vnode[];
  graph_content: m.Vnode[];
  selected_file_url: string;
  uploaded_file: object;
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
  plot_repo_url: '',
  repo_url: '',
  repo_owner: '',
  repo_name: '',
  repo_data: [],
  directory_content: [],
  upload_content: [],
  graph_content: [],
  selected_file_url: '',
  uploaded_file: {},
  showDirectoryNav: false,
  showUploadNav: false,
};
