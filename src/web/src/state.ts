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
  plot_repo_url: '',
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
