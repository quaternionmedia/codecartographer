/**
 * DirectoryNav Component
 *
 * Displays repository directory tree navigation
 */
import m from 'mithril';
import { Directory } from '../../../components/models/source';
import { DirectoryContent } from '../../../components/qm_comp_lib/directory/directory';

export interface DirectoryNavAttrs {
  directory: Directory | null;
  onFileClick: (url: string) => void;
  onPlotWholeRepo: () => void;
  onPlotDependencies: () => void;
}

export const DirectoryNav: m.Component<DirectoryNavAttrs> = {
  view(vnode) {
    const { directory, onFileClick, onPlotWholeRepo, onPlotDependencies } = vnode.attrs;

    if (!directory) {
      return m('.directory-nav--empty', [
        m('p', 'No repository loaded. Enter a GitHub URL to browse files.'),
      ]);
    }

    return m('.directory-nav', [
      m('.directory-nav__header', [
        m('h3', directory.info?.name || 'Repository'),
        m('.directory-nav__stats', [
          m('span', `${directory.size || 0} files`),
        ]),
      ]),

      m('.directory-nav__actions', [
        m('button.btn.btn--primary', {
          onclick: onPlotWholeRepo,
        }, 'Plot Directory Tree'),
        m('button.btn', {
          onclick: onPlotDependencies,
        }, 'Plot Dependencies'),
      ]),

      m('.directory-nav__tree', [
        m(DirectoryContent, {
          folderName: directory.root.name,
          folders: directory.root.folders,
          files: directory.root.files,
          onUrlFileClicked: onFileClick,
        }),
      ]),
    ]);
  },
};
