import m from 'mithril';
import { RawFile } from '../../models/source';
import { File } from './file';
import { animations } from '../../../core/animations';
import { entryPath, rawLink } from './tree_rows';

interface FileListAttrs {
  folderName: string;
  /** The folder's path from the tree's root; '' for the root. */
  folderPath: string;
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
  allowedExtensions?: string[] | null;
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
    const { folderName, folderPath, files, onUrlFileClicked, allowedExtensions } = vnode.attrs;

    return m(`div.files.files__${folderName}`, [
      files.map((file: RawFile) => {
        // Only a file with a web address has a raw link (`tree_rows.ts`).
        const raw = rawLink(entryPath(folderPath, file.name), file.url);
        return m('div.file_container', { style: { opacity: 0 } }, [
          m(File, {
            fileName: file.name,
            fileUrl: file.url,
            onUrlFileClicked: onUrlFileClicked,
            allowedExtensions: allowedExtensions,
          }),
          raw ? m('a.file_raw_btn', raw, 'raw') : null,
        ]);
      }),
    ]);
  },
};
