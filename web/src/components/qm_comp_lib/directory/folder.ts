import m from 'mithril';
import { RawFile, RawFolder } from '../../models/source';
import { FileList } from './files';
import { animations } from '../../../core/animations';

interface FolderAttrs {
  folderName: string;
  /** Full path from repo root, e.g. "kernel" or "kernel/drivers" */
  folderPath: string;
  folders: RawFolder[];
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
  /** Called when a stub folder (no children) is opened — triggers lazy load */
  onFolderExpand?: (path: string) => void;
}

interface FolderState {
  isOpen: boolean;
  isLoading: boolean;
}

export const Folder: m.Component<FolderAttrs> = {
  oninit(vnode) {
    (vnode.state as FolderState).isOpen = false;
    (vnode.state as FolderState).isLoading = false;
  },

  onupdate(vnode) {
    const state = vnode.state as FolderState;
    if (state.isLoading) {
      const { folders, files } = vnode.attrs;
      // Reset spinner once the expansion has delivered content
      if (folders.length > 0 || files.length > 0) {
        state.isLoading = false;
        m.redraw();
      }
    }
  },

  view(vnode) {
    const { folderName, folderPath, folders, files, onUrlFileClicked, onFolderExpand } = vnode.attrs;
    const state = vnode.state as FolderState;
    const isStub = folders.length === 0 && files.length === 0;

    return m(`div.folder.folder__${folderName}`, [
      m(
        'div.folder_button',
        {
          class: isStub ? 'folder_button--stub' : '',
          onclick: function (e: MouseEvent) {
            const button = e.currentTarget as HTMLElement;
            button.classList.toggle('active');
            state.isOpen = !state.isOpen;

            // Animate button press
            animations.buttonPress(button);

            // If this is a stub folder being opened, request lazy expansion
            if (state.isOpen && isStub && onFolderExpand && !state.isLoading) {
              state.isLoading = true;
              onFolderExpand(folderPath);
            }

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
        [
          folderName,
          isStub && !state.isLoading ? m('span.folder_stub_indicator', ' …') : null,
          state.isLoading ? m('span.folder_loading_indicator', ' ↻') : null,
        ]
      ),
      m('div.folder_content', { style: { display: state.isOpen ? 'block' : 'none' } }, [
        foldersParse(folders, onUrlFileClicked, onFolderExpand, folderPath),
        m(FileList, { folderName, files: files, onUrlFileClicked }),
      ]),
    ]);
  },
};

export function foldersParse(
  folders: RawFolder[],
  onUrlFileClicked: (url: string) => void,
  onFolderExpand?: (path: string) => void,
  parentPath: string = ''
): m.Children {
  return folders.map(folder => {
    const folderPath = parentPath ? `${parentPath}/${folder.name}` : folder.name;
    return m(Folder, {
      key: folder.name,
      folderName: folder.name,
      folderPath: folderPath,
      folders: folder.folders,
      files: folder.files,
      onUrlFileClicked: onUrlFileClicked,
      onFolderExpand: onFolderExpand,
    });
  });
}
