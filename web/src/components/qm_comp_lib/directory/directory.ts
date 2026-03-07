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
  allowedExtensions?: string[] | null;
}

export const DirectoryContent: m.Component<DirectoryAttrs> = {
  view(vnode) {
    const { folderName, folders, files, onUrlFileClicked, onFolderExpand, allowedExtensions } = vnode.attrs;

    return m('div.directory_content', {}, [
      foldersParse(folders, onUrlFileClicked, onFolderExpand, '', allowedExtensions),
      m(FileList, {
        folderName: folderName,
        files: files,
        onUrlFileClicked: onUrlFileClicked,
        allowedExtensions: allowedExtensions,
      }),
    ]);
  },
};
