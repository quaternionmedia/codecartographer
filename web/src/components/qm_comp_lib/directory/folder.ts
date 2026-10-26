import m from 'mithril';
import { RawFile, RawFolder } from '../../models/source';
import { FileList } from './files';
import { animations } from '../../../core/animations';
import { readStub } from './stub_read';
import type { StubState } from './stub_read';
import { folderRow } from './tree_rows';

/**
 * Called when a stub folder (no children) is opened, to read it. Resolves true
 * when it put the folder's contents in the tree; false, or a rejection, leaves
 * the folder unread for the next click.
 */
export type FolderExpand = (path: string) => Promise<boolean>;

interface FolderAttrs {
  folderName: string;
  /** Full path from repo root, e.g. "kernel" or "kernel/drivers" */
  folderPath: string;
  folders: RawFolder[];
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
  onFolderExpand?: FolderExpand;
  allowedExtensions?: string[] | null;
}

type FolderState = StubState;

export const Folder: m.Component<FolderAttrs> = {
  oninit(vnode) {
    (vnode.state as FolderState).isOpen = false;
    (vnode.state as FolderState).isLoading = false;
  },

  view(vnode) {
    const { folderName, folderPath, folders, files, onUrlFileClicked, onFolderExpand, allowedExtensions } = vnode.attrs;
    const state = vnode.state as FolderState;
    const isEmpty = folders.length === 0 && files.length === 0;
    const isStub = isEmpty && !!onFolderExpand;  // empty AND can be lazy-loaded

    // Opens or closes the folder, from a click or a key. The folder's element
    // holds its row first and its contents, when open, after it.
    const toggle = () => {
      const button = (vnode as m.VnodeDOM<FolderAttrs, FolderState>).dom.firstElementChild as HTMLElement;
      const folderContent = button.nextElementSibling as HTMLElement | null;

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
          // animejs v4's JSAnimation is itself thenable (resolves on
          // completion) -- v3's separate `.finished` promise property
          // no longer exists, so awaiting that always resolved
          // immediately with undefined instead of waiting for the
          // animation to actually finish.
          Promise.resolve(anim).then(close);
        } else {
          close();
        }
      } else if (isStub && onFolderExpand && !state.isLoading) {
        // Opening an unread folder reads it; the spinner ends when the
        // read does, and a read that failed leaves it unread to click
        // again (`stub_read.ts`).
        void readStub(state, () => onFolderExpand(folderPath), () => m.redraw());
      } else {
        // Opening: set state so Mithril renders the content (oncreate animates it in)
        state.isOpen = true;
        m.redraw();
      }
    };

    return m(`div.folder.folder__${folderName}`, [
      m(
        'div.folder_button',
        {
          ...folderRow(folderName, state.isOpen, isEmpty && !isStub ? null : toggle),
          class: [
            isStub ? 'folder_button--stub' : '',
            isEmpty && !isStub ? 'folder_button--empty' : '',
            state.isOpen ? 'active' : '',
          ].filter(Boolean).join(' '),
        },
        [
          m('span.folder_name', folderName),
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
            m(FileList, { folderName, folderPath, files: files, onUrlFileClicked, allowedExtensions }),
          ])
        : null,
    ]);
  },
};

export function foldersParse(
  folders: RawFolder[],
  onUrlFileClicked: (url: string) => void,
  onFolderExpand?: FolderExpand,
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
