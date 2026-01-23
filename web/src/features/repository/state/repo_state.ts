/**
 * Repository Feature State Management
 */
import { Directory, RawFile, RawFolder } from '../../../components/models/source';

export interface RepoState {
  /** GitHub repository URL */
  url: string;
  /** Fetched directory structure */
  directory: Directory | null;
  /** Currently selected file */
  selectedFile: RawFile | null;
  /** Currently selected folder */
  selectedFolder: RawFolder | null;
  /** Whether repository is being fetched */
  isLoading: boolean;
  /** Error message if fetch failed */
  error: string | null;
}

export const DEFAULT_REPO_STATE: RepoState = {
  url: '',
  directory: null,
  selectedFile: null,
  selectedFolder: null,
  isLoading: false,
  error: null,
};
