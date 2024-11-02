import m from 'mithril';

import { RawFile, Directory, RawFolder } from '../../models/source';
import './directory_nav.css';

export class DirectoryNavState {
  navChildComp: m.Vnode[];
  selectedUrl: string;
  content: Directory;
  onUrlFileClicked: (url: string) => void;
  onWholeRepoClicked: () => void;
  updateCell: (upload: DirectoryNavState) => void;

  constructor(
    navChildComp: m.Vnode[] = [],
    selectedUrl: string = '',
    content: Directory = new Directory(),
    onUrlFileClicked: (url: string) => void,
    onWholeRepoClicked: () => void,
    updateCell: (upload: DirectoryNavState) => void
  ) {
    this.navChildComp = navChildComp;
    this.selectedUrl = selectedUrl;
    this.content = content;
    this.onUrlFileClicked = onUrlFileClicked;
    this.onWholeRepoClicked = onWholeRepoClicked;
    this.updateCell = updateCell;
  }

  // Arrow function to automatically bind `this`
  public setSelectedUrl = (url: string) => {
    this.selectedUrl = url;
    this.updateCell(this);
    this.onUrlFileClicked(url);
  };
}

export const DirectoryNav = (directoryNav: DirectoryNavState) => {
  if (directoryNav.content.size > 0) {
    const folder = directoryNav.content.root;
    var owner = directoryNav.content.info.owner;
    var name = directoryNav.content.info.name;
    var tree = m(Folder, {
      isRoot: true,
      folderName: `${owner} ${name}`,
      folders: folder.folders,
      files: folder.files,
      onUrlFileClicked: directoryNav.onUrlFileClicked,
    });

    var plotAll = m(
      'button.plot_whole_repo_btn',
      {
        onclick: function () {
          directoryNav.onWholeRepoClicked();
        },
      },
      'Plot Whole Repo'
    );

    directoryNav.navChildComp = [m('div.directory_tree', tree), plotAll];
  }

  return m('div.directory_nav', [directoryNav.navChildComp]);
};

function foldersParse(
  folders: RawFolder[],
  onUrlFileClicked: (url: string) => void
): m.Children {
  let folderElements: m.Children = [];
  let fileElements: m.Children = [];

  folders.forEach((folder) => {
    fileElements.push();
    folderElements.push(
      m(Folder, {
        isRoot: false,
        folderName: folder.name,
        folders: folder.folders,
        files: folder.files,
        onUrlFileClicked: onUrlFileClicked,
      })
    );
    fileElements.push();
  });

  return folderElements;
}

interface FolderAttrs {
  isRoot: boolean;
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
    const { isRoot, folderName, folders, files, onUrlFileClicked } =
      vnode.attrs;
    let state = vnode.state as FolderState; // Type assertion for state
    state.isOpen = isRoot;

    return m(`div.folder.folder__${folderName}__${isRoot ? 'root' : ''}`, [
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

interface FileAttrs {
  fileName: string;
  fileUrl: string;
  onUrlFileClicked: (url: string) => void;
}

export const File: m.Component<FileAttrs> = {
  view(vnode) {
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
