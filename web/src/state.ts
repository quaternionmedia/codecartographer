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
  showContentNav: boolean;
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
  showContentNav: false,
};
