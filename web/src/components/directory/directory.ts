import m from 'mithril';

import './directory.css';
import { ICell } from '../../state';

export const Directory = (
  cell: ICell,
  setSelectedUrl: (url: string) => void
) => {
  var contents = [];

  if (cell.state.repo_url !== '') {
    var plot_all = m(
      'button.plot_whole_btn',
      {
        onclick: function () {
          setSelectedUrl(cell.state.plot_repo_url);
        },
      },
      'Plot Whole Repo'
    );

    var contents = [
      parseContents(cell.state.repo_data, 'root', setSelectedUrl),
      plot_all,
    ];
  }

  cell.update({ directory_content: contents });

  return m('div.directory', [cell.state.directory_content]);
};

export function parseContents(
  data: Object,
  name: string,
  setSelectedUrl: (url: string) => void
) {
  return Object.entries(data).map(([key, value]) => {
    if (key === 'files') {
      return m(FileList, {
        parent: name,
        children: value,
        setSelectedUrl: setSelectedUrl,
      });
    } else {
      return m(Folder, {
        name: key,
        children: value,
        setSelectedUrl: setSelectedUrl,
      });
    }
  });
}

// ###################### DIRECTORY COMPONENTS ######################
export const Folder = {
  view: function (vnode) {
    let { name, children, setSelectedUrl } = vnode.attrs;
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
      m('div.folder_content', parseContents(children, name, setSelectedUrl)),
    ]);
  },
};

export const FileList = {
  view: function (vnode) {
    let { parent, children, setSelectedUrl } = vnode.attrs;
    return m(`div.files.files__${parent}`, [
      children.map((child: IRepoFile) =>
        m(File, {
          name: child.name,
          url: child.download_url,
          setSelectedUrl: setSelectedUrl,
        })
      ),
    ]);
  },
};

export const File = {
  view: function (vnode) {
    let { name, url, setSelectedUrl } = vnode.attrs;
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
            setSelectedUrl(url);
          }
        },
      },
      name
    );
  },
};

export interface IRepoFile {
  download_url: string;
  name: string;
}
