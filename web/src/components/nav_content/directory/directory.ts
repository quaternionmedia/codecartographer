import m from 'mithril';

import { ICell } from '../../../state';
import './directory.css';

export const Directory = (
  cell: ICell,
  setSelectedFile: (url: string) => void
) => {
  var contents = [];

  if (cell.state.repo_url !== '') {
    var plot_all = m(
      'button.plot_whole_btn',
      {
        onclick: function () {
          setSelectedFile(cell.state.plot_repo_url);
        },
      },
      'Plot Whole Repo'
    );

    var tree = parseContents(cell.state.repo_data, 'root', setSelectedFile);
    var contents = [m('div.directory_tree', [tree]), plot_all];
  }

  cell.update({ directory_content: contents });

  return m('div.directory', [cell.state.directory_content]);
};

export function parseContents(
  data: Object,
  name: string,
  setSelectedFile: (url: string) => void
) {
  return Object.entries(data).map(([key, value]) => {
    if (key === 'files') {
      return m(FileList, {
        parent: name,
        children: value,
        setSelectedFile: setSelectedFile,
      });
    } else {
      return m(Folder, {
        name: key,
        children: value,
        setSelectedFile: setSelectedFile,
      });
    }
  });
}

// ###################### DIRECTORY COMPONENTS ######################
export const Folder = {
  view: function (vnode) {
    let { name, children, setSelectedFile } = vnode.attrs;
    return m(`div.folder.folder__${name}`, [
      m(
        'div.folder_button',
        {
          onclick: function () {
            this.classList.toggle('active');
            vnode.state.isOpen = !vnode.state.isOpen;
            m.redraw(); // Trigger a redraw to update the view
          },
        },
        name
      ),
      m('div.folder_content', parseContents(children, name, setSelectedFile)),
    ]);
  },
};

export const FileList = {
  view: function (vnode) {
    let { parent, children, setSelectedFile } = vnode.attrs;
    return m(`div.files.files__${parent}`, [
      children.map((child: IRepoFile) =>
        m(File, {
          name: child.name,
          url: child.download_url,
          setSelectedFile: setSelectedFile,
        })
      ),
    ]);
  },
};

export const File = {
  view: function (vnode) {
    let { name, url, setSelectedFile } = vnode.attrs;
    let isDisabled = true;
    let ext = name.split('.').pop();
    const compatibleExtensions = ['py'];
    // Check if the file extension is compatible
    if (compatibleExtensions.includes(ext)) {
      isDisabled = false;
    }
    return m(
      'div.file',
      {
        class: `file__${ext} ${isDisabled ? 'disabled' : ''}`,
        url: url,
        onclick: function () {
          if (!isDisabled) {
            setSelectedFile(url);
          }
        },
      },
      [m('a.file_raw_btn', { href: url, target: '_blank' }), name]
    );
  },
};

export interface IRepoFile {
  download_url: string;
  name: string;
}
