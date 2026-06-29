/**
 * File Tree Panel
 *
 * Mounts the repository / uploaded-file directory browser into a Golden Layout
 * panel. When a repository is loaded the tree is shown; otherwise a prompt
 * guides the user to the Controls panel.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { DirectoryContent } from '../../components/qm_comp_lib/directory/directory';

export function createFileTreePanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const state = ctx.appState.state;
      const repoDir = state.repo.content;
      const localDir = state.local.content;
      const hasRepo = repoDir && repoDir.size > 0;
      const hasLocal = localDir && localDir.size > 0;

      return m('div.gl-panel.gl-panel--file-tree', [
        // Repository tree
        hasRepo
          ? m('section.gl-file-tree__section', [
              m('header.gl-file-tree__header', [
                m('span.gl-file-tree__icon', '◉'),
                m('span', `${repoDir.info.owner}/${repoDir.info.name}`),
              ]),
              m('div.gl-file-tree__tree', [
                m(DirectoryContent, {
                  folderName: `${repoDir.info.owner}/${repoDir.info.name}`,
                  folders: repoDir.root.folders,
                  files: repoDir.root.files,
                  onUrlFileClicked: (url: string) => ctx.panelCallbacks.onRepoFileClick(url),
                }),
              ]),
              m('div.gl-file-tree__actions', [
                m('button.gl-file-tree__action-btn', {
                  onclick: () => ctx.panelCallbacks.onPlotWholeRepo(),
                  title: 'Plot the entire repository',
                }, '◈ Plot All'),
                ctx.panelCallbacks.onExpandAll
                  ? m('button.gl-file-tree__action-btn', {
                      onclick: () => ctx.panelCallbacks.onExpandAll?.(),
                      title: 'Expand all stub folders',
                    }, '⊞ Expand All')
                  : null,
              ]),
            ])
          : null,

        // Uploaded files tree
        hasLocal
          ? m('section.gl-file-tree__section', [
              m('header.gl-file-tree__header', [
                m('span.gl-file-tree__icon', '⬆'),
                m('span', 'Uploaded Files'),
              ]),
              m('ul.gl-file-tree__list',
                ctx.uploadedFiles.map((file) =>
                  m('li.gl-file-tree__file', {
                    key: file.name,
                    onclick: () => ctx.panelCallbacks.onUploadedFileClick(file),
                    title: file.name,
                  }, file.name),
                ),
              ),
            ])
          : null,

        // Empty-state prompt
        !hasRepo && !hasLocal
          ? m('div.gl-file-tree__empty', [
              m('span.gl-file-tree__empty-icon', '◉'),
              m('p.gl-file-tree__empty-text',
                'No source loaded. Use the Controls panel to fetch a GitHub repo or upload files.',
              ),
            ])
          : null,
      ]);
    },
  };
}
