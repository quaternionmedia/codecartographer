import m from 'mithril';
import { RawFile, RawFolder } from '../../models/source';
import { FileList } from './files';
import { foldersParse } from './folder';

interface DirectoryAttrs {
  folderName: string;
  folders: RawFolder[];
  files: RawFile[];
  onUrlFileClicked: (url: string) => void;
  onFolderExpand?: (path: string) => void;
}

export const DirectoryContent: m.Component<DirectoryAttrs> = {
  view(vnode) {
    const { folderName, folders, files, onUrlFileClicked, onFolderExpand } = vnode.attrs;

    return m('div.directory_content', {}, [
      foldersParse(folders, onUrlFileClicked, onFolderExpand, ''),
      m(FileList, {
        folderName: folderName,
        files: files,
        onUrlFileClicked: onUrlFileClicked,
      }),
    ]);
  },
};
