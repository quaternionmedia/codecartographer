import m from 'mithril';
import { RawFile } from '../../models/source';
import { File } from './file';

interface FileListAttrs {
  folderName: string;
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
}

export const FileList: m.Component<FileListAttrs> = {
  view(vnode) {
    const { folderName, files, onUrlFileClicked } = vnode.attrs;

    return m(`div.files.files__${folderName}`, [
      files.map((file: RawFile) =>
        m('div.file_container', [
          m(File, {
            fileName: file.name,
            fileUrl: file.url,
            onUrlFileClicked: onUrlFileClicked,
          }),
          m('a.file_raw_btn', { href: file.url, target: '_blank' }, 'raw'),
        ])
      ),
    ]);
  },
};
