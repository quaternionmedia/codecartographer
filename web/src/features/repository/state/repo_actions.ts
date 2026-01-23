/**
 * Repository Feature Actions
 *
 * Handles repository state updates
 */
import { Directory, RawFile, RawFolder } from '../../../components/models/source';
import { RepoState } from './repo_state';

export const repoActions = {
  /**
   * Set repository URL
   */
  setUrl: (url: string) => (state: RepoState): RepoState => ({
    ...state,
    url,
  }),

  /**
   * Set directory structure
   */
  setDirectory: (directory: Directory) => (state: RepoState): RepoState => ({
    ...state,
    directory,
    isLoading: false,
    error: null,
  }),

  /**
   * Select a file
   */
  selectFile: (file: RawFile) => (state: RepoState): RepoState => ({
    ...state,
    selectedFile: file,
    selectedFolder: null,
  }),

  /**
   * Select a folder
   */
  selectFolder: (folder: RawFolder) => (state: RepoState): RepoState => ({
    ...state,
    selectedFolder: folder,
    selectedFile: null,
  }),

  /**
   * Set loading state
   */
  setLoading: (isLoading: boolean) => (state: RepoState): RepoState => ({
    ...state,
    isLoading,
    error: isLoading ? null : state.error,
  }),

  /**
   * Set error
   */
  setError: (error: string) => (state: RepoState): RepoState => ({
    ...state,
    error,
    isLoading: false,
  }),

  /**
   * Clear repository data
   */
  clear: () => (state: RepoState): RepoState => ({
    url: '',
    directory: null,
    selectedFile: null,
    selectedFolder: null,
    isLoading: false,
    error: null,
  }),
};
