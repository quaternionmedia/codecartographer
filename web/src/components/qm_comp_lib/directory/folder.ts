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
  allowedExtensions?: string[] | null;
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
    const { folderName, folderPath, folders, files, onUrlFileClicked, onFolderExpand, allowedExtensions } = vnode.attrs;
    const state = vnode.state as FolderState;
    const isEmpty = folders.length === 0 && files.length === 0;
    const isStub = isEmpty && !!onFolderExpand;  // empty AND can be lazy-loaded

    return m(`div.folder.folder__${folderName}`, [
      m(
        'div.folder_button',
        {
          class: [
            isStub ? 'folder_button--stub' : '',
            isEmpty && !isStub ? 'folder_button--empty' : '',
            state.isOpen ? 'active' : '',
          ].filter(Boolean).join(' '),
          onclick: isEmpty && !isStub ? undefined : function (e: MouseEvent) {
            const button = e.currentTarget as HTMLElement;
            const folderContent = button.nextElementSibling as HTMLElement;

            // Animate button press
            animations.buttonPress(button);

            if (state.isOpen) {
              // Closing: animate out first, then let Mithril hide via state
              const close = () => {
                state.isOpen = false;
                m.redraw();
              };
              if (folderContent) {
                const anim = animations.fadeOut(folderContent, { duration: 150 });
                Promise.resolve(anim?.finished).then(close);
              } else {
                close();
              }
            } else {
              // Opening: set state so Mithril renders the content (oncreate animates it in)
              state.isOpen = true;
              if (isStub && onFolderExpand && !state.isLoading) {
                state.isLoading = true;
                onFolderExpand(folderPath);
              }
              m.redraw();
            }
          },
        },
        [
          folderName,
          isStub && !state.isLoading ? m('span.folder_stub_indicator', ' …') : null,
          state.isLoading ? m('span.folder_loading_indicator', ' ↻') : null,
        ]
      ),
      state.isOpen
        ? m('div.folder_content', {
            oncreate: (vnode: m.VnodeDOM<unknown, unknown>) => {
              animations.fadeIn(vnode.dom as HTMLElement, { duration: 200, translateY: -10 });
            },
          }, [
            foldersParse(folders, onUrlFileClicked, onFolderExpand, folderPath, allowedExtensions),
            m(FileList, { folderName, files: files, onUrlFileClicked, allowedExtensions }),
          ])
        : null,
    ]);
  },
};

export function foldersParse(
  folders: RawFolder[],
  onUrlFileClicked: (url: string) => void,
  onFolderExpand?: (path: string) => void,
  parentPath: string = '',
  allowedExtensions?: string[] | null
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
      allowedExtensions: allowedExtensions,
    });
  });
}
