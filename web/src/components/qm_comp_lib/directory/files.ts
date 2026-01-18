import m from 'mithril';
import { RawFile } from '../../models/source';
import { File } from './file';
import { animations } from '../../../core/animations';

interface FileListAttrs {
  folderName: string;
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
}

export const FileList: m.Component<FileListAttrs> = {
  oncreate(vnode) {
    // Stagger animate file items on initial render
    const fileContainers = vnode.dom.querySelectorAll('.file_container');
    if (fileContainers.length > 0) {
      animations.staggerIn(fileContainers, { staggerDelay: 30 });
    }
  },

  view(vnode) {
    const { folderName, files, onUrlFileClicked } = vnode.attrs;

    return m(`div.files.files__${folderName}`, [
      files.map((file: RawFile) =>
        m('div.file_container', { style: { opacity: 0 } }, [
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
