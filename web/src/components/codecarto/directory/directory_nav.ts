import m from 'mithril';

import { displayError } from '../../../utility';
import { Directory, RawFile, RawFolder } from '../../models/source';
import { DirectoryContent } from '../../qm_comp_lib/directory/directory';
import './directory_nav.css';

export class DirectoryNavController {
  public isLocal: boolean = false;
  public isMenuOpen: boolean = false;
  public selectedUrl: string = '';
  public selectedFile: RawFile = new RawFile();
  public selectedFolder: RawFolder = new RawFolder();
  public content: Directory = new Directory();
  public component: m.Vnode[] = [];

  constructor(isLocal: boolean) {
    this.isLocal = isLocal;
  }

  public clearSelectedFile() {
    this.selectedFile = new RawFile();
  }

  public clearSelectedFolder() {
    this.selectedFolder = new RawFolder();
  }

  public clear() {
    this.content = new Directory();
    this.clearSelectedFile();
    this.clearSelectedFolder();
  }
}

export class DirectoryNavState {
  public controller: DirectoryNavController;
  private onUrlClicked: (url: string) => void;
  private onWholeRepoClicked: () => void;
  private updateCell: (upload: DirectoryNavState) => void;

  constructor(
    controller: DirectoryNavController,
    onUrlFileClicked: (url: string) => void,
    onWholeRepoClicked: () => void,
    updateCell: (upload: DirectoryNavState) => void
  ) {
    this.controller = controller;
    this.onUrlClicked = onUrlFileClicked;
    this.onWholeRepoClicked = onWholeRepoClicked;
    this.updateCell = updateCell;
  }

  public setSelectedUrl = (url: string) => {
    if (this.checkUrl(url)) {
      this.controller.selectedUrl = url;
      this.updateCell(this);
      this.onUrlClicked(url);
    }
  };

  public wholeRepoClicked = () => {
    this.onWholeRepoClicked();
  };

  private checkUrl(url: string): boolean {
    if (!url || url === '') {
      displayError('Please enter a URL');
      return false;
    }
    return true;
  }
}

export const DirectoryNav = (state: DirectoryNavState) => {
  if (state.controller.content.size > 0) {
    const folder = state.controller.content.root;
    const owner = state.controller.content.info.owner;
    const name = state.controller.content.info.name;

    const tree = m(DirectoryContent, {
      folderName: `${owner}/${name}`,
      folders: folder.folders,
      files: folder.files,
      onUrlFileClicked: state.setSelectedUrl,
    });

    const plotAll = m(
      'button.plot_whole_repo_btn',
      {
        onclick: function () {
          state.wholeRepoClicked();
        },
      },
      'Plot Whole Repo'
    );

    state.controller.component = [m('div.directory_tree', tree), plotAll];
  }

  return m('div.directory_nav', [state.controller.component]);
};
