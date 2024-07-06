import m from 'mithril';

import './directory.css';
import { ICell } from '../../state';

export const Directory = (cell: ICell) =>
  m('div.directory', [cell.state.directory_content]);

export function parseContents(data: Object, name: string) {
  return Object.entries(data).map(([key, value]) => {
    if (key === 'files') {
      return m(FileList, {
        parent: name,
        children: value,
      });
    } else {
      return m(Folder, {
        name: key,
        children: value,
      });
    }
  });
}

// ###################### DIRECTORY COMPONENTS ######################
export const Folder = {
  view: function (vnode) {
    let { name, children } = vnode.attrs;
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
      m('div.folder_content', parseContents(children, name)),
    ]);
  },
};

export const FileList = {
  view: function (vnode) {
    let { parent, children } = vnode.attrs;
    return m(`div.files.files__${parent}`, [
      children.map((child: IRepoFile) =>
        m(File, {
          name: child.name,
          url: child.download_url,
        })
      ),
    ]);
  },
};

export const File = {
  view: function (vnode) {
    let { name, url } = vnode.attrs;
    let isDisabled = true;
    let ext = name.split('.').pop();
    const compatibleExtensions = ['py'];
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
            console.log('clicked', url);
            // TODO plot file content
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
