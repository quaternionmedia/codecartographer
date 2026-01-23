/**
 * Upload Feature Actions
 *
 * Handles upload state updates
 */
import { RawFile } from '../../../components/models/source';
import { UploadState } from './upload_state';

export const uploadActions = {
  /**
   * Add uploaded files
   */
  addFiles: (files: RawFile[]) => (state: UploadState): UploadState => ({
    ...state,
    files: [...state.files, ...files],
  }),

  /**
   * Remove a file
   */
  removeFile: (file: RawFile) => (state: UploadState): UploadState => ({
    ...state,
    files: state.files.filter(f => f !== file),
    selectedFile: state.selectedFile === file ? null : state.selectedFile,
  }),

  /**
   * Select a file
   */
  selectFile: (file: RawFile) => (state: UploadState): UploadState => ({
    ...state,
    selectedFile: file,
  }),

  /**
   * Set processing state
   */
  setProcessing: (isProcessing: boolean) => (state: UploadState): UploadState => ({
    ...state,
    isProcessing,
  }),

  /**
   * Clear all uploads
   */
  clear: () => (state: UploadState): UploadState => ({
    files: [],
    selectedFile: null,
    isProcessing: false,
  }),
};
