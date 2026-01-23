/**
 * Upload Feature State Management
 */
import { RawFile } from '../../../components/models/source';

export interface UploadState {
  /** Uploaded files */
  files: RawFile[];
  /** Currently selected file */
  selectedFile: RawFile | null;
  /** Whether files are being processed */
  isProcessing: boolean;
}

export const DEFAULT_UPLOAD_STATE: UploadState = {
  files: [],
  selectedFile: null,
  isProcessing: false,
};
