import m from 'mithril';

interface FileAttrs {
  fileName: string;
  fileUrl: string;
  onUrlFileClicked: (url: string) => void;
}

export const File: m.Component<FileAttrs> = {
  view(vnode: any) {
    const { fileName, fileUrl, onUrlFileClicked } = vnode.attrs;
    const ext = fileName.split('.').pop() ?? '';
    const isDisabled = !['py'].includes(ext);

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
