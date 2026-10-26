import m from 'mithril';
import { fileRow } from './tree_rows';

interface FileAttrs {
  fileName: string;
  fileUrl: string;
  onUrlFileClicked: (url: string) => void;
  /** Allowed extensions (without leading dot). Null/undefined = all enabled. */
  allowedExtensions?: string[] | null;
}

export const File: m.Component<FileAttrs> = {
  view(vnode: m.Vnode<FileAttrs>) {
    const { fileName, fileUrl, onUrlFileClicked, allowedExtensions } = vnode.attrs;
    return m(
      'div.file',
      fileRow(fileName, () => onUrlFileClicked(fileUrl), allowedExtensions),
      fileName
    );
  },
};
