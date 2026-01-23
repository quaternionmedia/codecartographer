import m from 'mithril';
import { RawFile, RawFolder } from '../../models/source';
import { FileList } from './files';
import { animations } from '../../../core/animations';

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
  oninit(vnode) {
    (vnode.state as FolderState).isOpen = false;
  },

  view(vnode) {
    const { folderName, folders, files, onUrlFileClicked } = vnode.attrs;
    let state = vnode.state as FolderState;

    return m(`div.folder.folder__${folderName}`, [
      m(
        'div.folder_button',
        {
          onclick: function (e: MouseEvent) {
            const button = e.currentTarget as HTMLElement;
            button.classList.toggle('active');
            state.isOpen = !state.isOpen;
            
            // Animate button press
            animations.buttonPress(button);
            
            // Animate folder content
            const folderContent = button.nextElementSibling as HTMLElement;
            if (folderContent) {
              if (state.isOpen) {
                folderContent.style.display = 'block';
                animations.fadeIn(folderContent, { duration: 200, translateY: -10 });
              } else {
                animations.fadeOut(folderContent, { duration: 150 }).finished.then(() => {
                  if (!state.isOpen) {
                    folderContent.style.display = 'none';
                  }
                });
              }
            }
            
            m.redraw();
          },
        },
        folderName
      ),
      m('div.folder_content', { style: { display: state.isOpen ? 'block' : 'none' } }, [
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
