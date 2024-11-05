import m from 'mithril';
import { RawFile, RawFolder } from '../../models/source';
import { FileList } from './files';

interface FolderAttrs {
  folderName: string;
  folders: RawFolder[];
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
}

interface FolderState {
  isOpen: boolean;
}

export const Folder: m.Component<FolderAttrs> = {
  view(vnode) {
    const { folderName, folders, files, onUrlFileClicked } = vnode.attrs;
    let state = vnode.state as FolderState; // Type assertion for state

    return m(`div.folder.folder__${folderName}`, [
      m(
        'div.folder_button',
        {
          onclick: function () {
            this.classList.toggle('active');
            state.isOpen = !state.isOpen;
            m.redraw(); // Trigger a redraw to update the view
          },
        },
        folderName
      ),
      m('div.folder_content', {}, [
        foldersParse(folders, onUrlFileClicked),
        m(FileList, { folderName, files: files, onUrlFileClicked }),
      ]),
    ]);
  },
};

export function foldersParse(
  folders: RawFolder[],
  onUrlFileClicked: (url: string) => void
): m.Children {
  let folderElements: m.Children = [];

  folders.forEach((folder) => {
    folderElements.push(
      m(Folder, {
        folderName: folder.name,
        folders: folder.folders,
        files: folder.files,
        onUrlFileClicked: onUrlFileClicked,
      })
    );
  });

  return folderElements;
}
