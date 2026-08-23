import type m from 'mithril';

import { Directory, RawFile, RawFolder } from '../../models/source';

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
