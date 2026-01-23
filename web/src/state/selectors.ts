import { AppState, RepoState, LocalState, GraphState, UIState } from './types';

/**
 * State selectors - derive computed values from state
 * Use these instead of accessing state directly for computed properties
 */
export const selectors = {
  // Repository selectors
  hasRepoContent: (state: { repo: RepoState }): boolean =>
    state.repo.directory !== null && (state.repo.directory.size ?? 0) > 0,

  hasRepoUrl: (state: { repo: RepoState }): boolean =>
    state.repo.url.trim().length > 0,

  isValidGithubUrl: (state: { repo: RepoState }): boolean => {
    const url = state.repo.url.trim();
    return url.startsWith('https://github.com/') && url.split('/').length >= 5;
  },

  selectedRepoFile: (state: { repo: RepoState }): string | null =>
    state.repo.selectedFile?.name ?? null,

  // Local file selectors
  hasLocalFiles: (state: { local: LocalState }): boolean =>
    state.local.files.length > 0,

  localFileCount: (state: { local: LocalState }): number =>
    state.local.files.length,

  selectedLocalFile: (state: { local: LocalState }): string | null =>
    state.local.selectedFile?.name ?? null,

  // Graph selectors
  hasGraphContent: (state: { graph: GraphState }): boolean =>
    state.graph.content.length > 0,

  isGraphRendering: (state: { graph: GraphState }): boolean =>
    state.graph.isRendering,

  // UI selectors
  isLoading: (state: { ui: UIState }): boolean =>
    state.ui.isLoading,

  hasError: (state: { ui: UIState }): boolean =>
    state.ui.error !== null,

  currentError: (state: { ui: UIState }): string | null =>
    state.ui.error,

  isControlPanelOpen: (state: { ui: UIState }): boolean =>
    state.ui.controlPanelOpen,

  activeTab: (state: { ui: UIState }): string =>
    state.ui.controlPanelTab,

  // Combined selectors
  canPlotRepo: (state: { repo: RepoState; ui: UIState }): boolean =>
    selectors.hasRepoContent(state) && !state.ui.isLoading,

  canPlotLocal: (state: { local: LocalState; ui: UIState }): boolean =>
    selectors.hasLocalFiles(state) && !state.ui.isLoading,

  activeFile: (state: { repo: RepoState; local: LocalState }) =>
    state.repo.selectedFile ?? state.local.selectedFile,

  isReady: (state: { ui: UIState }): boolean =>
    !state.ui.isLoading && state.ui.error === null,
};

export default selectors;
