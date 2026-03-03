import m from 'mithril';
import { RawFile } from '../../models/source';
import { File } from './file';
import { animations } from '../../../core/animations';

interface FileListAttrs {
  folderName: string;
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
}

function animateInvisibleContainers(dom: Element): void {
  // Animate file containers that are still invisible (opacity: 0).
  // Covers both initial render and files that arrive via lazy folder expansion.
  const invisible = Array.from(dom.querySelectorAll('.file_container')).filter(
    el => (el as HTMLElement).style.opacity === '0'
  );
  if (invisible.length > 0) {
    animations.staggerIn(invisible, { staggerDelay: 30 });
  }
}

export const FileList: m.Component<FileListAttrs> = {
  oncreate(vnode) {
    animateInvisibleContainers(vnode.dom);
  },

  onupdate(vnode) {
    animateInvisibleContainers(vnode.dom);
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
