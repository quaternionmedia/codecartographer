/**
 * File Tree Panel
 *
 * Mounts the repository / uploaded-file directory browser into a Golden Layout
 * panel: files and folders are added from disk at its head, the loaded
 * repository's tree follows, and the added files after it, each by its path.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { DirectoryContent } from '../../components/qm_comp_lib/directory/directory';
import { hasTree } from '../../features/repository/repo_tree';
import { pressable } from '../../components/codecarto/control_panel/pressable';
import { chosenFiles, droppedFiles } from '../../features/repository/local_drop';

const ACTIVE = 'panel-upload__dropzone--active';

/**
 * Where files and folders are added from disk: dropped on the box, files or a
 * folder alike, or chosen. The box chooses files and the button a folder; a
 * browser's chooser picks one or the other, never both.
 */
function addFiles(ctx: LayoutContext): m.Children {
  const extensions = ctx.appState.state.parserOptions.fileExtensions;
  const chooseFiles = () => document.getElementById('local-files-input')?.click();
  const chooseFolder = () => document.getElementById('local-folder-input')?.click();
  const chosen = (e: Event) => {
    const input = e.target as HTMLInputElement;
    const files = chosenFiles(input.files);
    // The same choice again is a change too.
    input.value = '';
    if (files.length) void ctx.panelCallbacks.onFileUpload(files);
  };
  return m('section.gl-file-tree__add', [
    // A drop target that holds its hidden file input, so not a <button>:
    // `pressable` gives it a button's place in the tab order, its role, and
    // Enter and Space, so files are added from the keyboard too.
    m('div.panel-upload__dropzone', {
      ondrop: (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        (e.currentTarget as HTMLElement).classList.remove(ACTIVE);
        // Read now: the browser empties the transfer once this handler returns.
        const read = droppedFiles(e.dataTransfer);
        void read.then((files) => { if (files.length) void ctx.panelCallbacks.onFileUpload(files); });
      },
      ondragover: (e: DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        (e.currentTarget as HTMLElement).classList.add(ACTIVE);
      },
      ondragleave: (e: DragEvent) => {
        e.preventDefault();
        (e.currentTarget as HTMLElement).classList.remove(ACTIVE);
      },
      onclick: chooseFiles,
      ...pressable(chooseFiles),
    }, [
      m('span.panel-upload__icon', { 'aria-hidden': 'true' }, '📁'),
      m('span.panel-upload__text', 'Drop files or a folder here, or click to choose files'),
      m('input#local-files-input[type=file][multiple]', {
        style: { display: 'none' },
        attrs: extensions.length > 0 ? { accept: extensions.join(',') } : {},
        onchange: chosen,
      }),
    ]),
    m('button.gl-file-tree__action-btn.gl-file-tree__folder-btn', {
      type: 'button',
      onclick: chooseFolder,
      title: "Choose a folder: every file in it is added, its own folders kept, less its version control, dependencies and build output",
    }, '📂 Choose a folder'),
    m('input#local-folder-input[type=file][multiple]', {
      style: { display: 'none' },
      webkitdirectory: true,
      onchange: chosen,
    }),
  ]);
}

export function createFileTreePanel(ctx: LayoutContext): m.Component {
  return {
    view: () => {
      const state = ctx.appState.state;
      const repoDir = state.repo.content;
      const localDir = state.local.content;
      const hasRepo = hasTree(repoDir);
      const hasLocal = hasTree(localDir);

      return m('div.gl-panel.gl-panel--file-tree', [
        addFiles(ctx),

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
                  // A large repository arrives with its folders unread. Given
                  // this, an empty folder is drawn with `…` and reads itself
                  // on click; without it, an empty folder in a partial tree
                  // could not be opened at all.
                  onFolderExpand: repoDir.is_partial
                    ? (path: string) => ctx.panelCallbacks.onFolderExpand(path)
                    : undefined,
                }),
              ]),
              m('div.gl-file-tree__actions', [
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
              // Each by its path under what was added: two files of one
              // name, from two folders, are two rows.
              m('ul.gl-file-tree__list',
                [...ctx.uploadedFiles]
                  .sort((a, b) => (a.url || a.name).localeCompare(b.url || b.name))
                  .map((file) =>
                    m('li.gl-file-tree__file', {
                      key: file.url || file.name,
                      onclick: () => ctx.panelCallbacks.onUploadedFileClick(file),
                      title: file.url || file.name,
                    }, file.url || file.name),
                  ),
              ),
            ])
          : null,

        // Empty-state prompt
        !hasRepo && !hasLocal
          ? m('div.gl-file-tree__empty', [
              m('span.gl-file-tree__empty-icon', '◉'),
              m('p.gl-file-tree__empty-text',
                'No source loaded. Open a repository in the Open panel, or add files or a folder above.',
              ),
            ])
          : null,
      ]);
    },
  };
}
