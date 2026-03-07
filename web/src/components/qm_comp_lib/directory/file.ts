import m from 'mithril';

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
    const ext = fileName.split('.').pop() ?? '';
    const isDisabled = allowedExtensions != null
      ? !allowedExtensions.some(e => e.replace(/^\./, '') === ext)
      : false;

    return m(
      'div.file',
      {
        class: `file__${ext} ${isDisabled ? 'disabled' : ''}`,
        onclick: () => !isDisabled && onUrlFileClicked(fileUrl),
      },
      fileName
    );
  },
};
