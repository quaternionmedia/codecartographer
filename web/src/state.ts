export interface DebugOptions {
  menu?: boolean;
  tracer?: boolean;
}

export interface State {
  debug?: DebugOptions;
  page?: string;
  container?: any;
}
