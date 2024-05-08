export interface DebugOptions {
  menu?: boolean;
  tracer?: boolean;
}

export interface Configurations {
  processor_url?: string;
}

export interface State {
  debug?: DebugOptions;
  configurations?: Configurations;
  page?: string;
  container?: any;
  source_code_path?: string;
}
