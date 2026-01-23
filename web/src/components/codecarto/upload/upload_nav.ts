import m, { Vnode } from 'mithril';

import { displayError } from '../../../utility';
import { animations } from '../../../core/animations';
import { RawFile } from '../../models/source';
import { DirectoryNavController } from '../directory/directory_nav';
import './upload_nav.css';

export class UploadNavState {
  navContent: Vnode[];
  selectedFile: RawFile;
  files: RawFile[];
  controller: DirectoryNavController;
  onFileClick: (file: RawFile) => void;
  onWholeSourceClick: () => void;
  updateCell: (upload: UploadNavState) => void;

  // TODO: Remove the this.navContent, this.selectedFile, and this.files
  // now that we could use the controller directly
  constructor(
    controller: DirectoryNavController,
    onFileClick: (file: RawFile) => void,
    onWholeSourceClick: () => void,
    updateCell: (upload: UploadNavState) => void
  ) {
    this.controller = controller;
    this.navContent = controller.component;
    this.selectedFile = controller.selectedFile;
    this.files = controller.content.root.files;
    this.onFileClick = onFileClick;
    this.onWholeSourceClick = onWholeSourceClick;
    this.updateCell = updateCell;
  }

  public setSelectedFile(file: RawFile) {
    if (!file) {
      displayError('Please select a file');
      return;
    }
    this.selectedFile = file;
    this.updateCell(this);
    this.onFileClick(file);
  }

  public addFile(file: RawFile) {
    this.files.push(file);
    this.updateCell(this);
    
    // Animate the new file entry after redraw
    setTimeout(() => {
      const fileContainers = document.querySelectorAll('.upload_files .file_container');
      const lastFile = fileContainers[fileContainers.length - 1];
      if (lastFile) {
        animations.fadeIn(lastFile, { translateY: 10 });
      }
    }, 0);
  }
}

export const UploadNav = (upload: UploadNavState) => {
  var tree = Files(upload, (file: RawFile) => {
    upload.setSelectedFile(file);
  });
  var plotAll = m(
    'button.plot_all_files_btn',
    {
      onclick: function (e: MouseEvent) {
        animations.buttonPress(e.currentTarget as Element);
        upload.onWholeSourceClick();
      },
    },
    'Plot Uploaded Files'
  );

  upload.navContent = [m('div.upload_tree', [UploadHeader(upload), tree])];

  return m('div.upload_nav', [upload.navContent]);
};

export const UploadHeader = (upload: UploadNavState) => {
  return m('div.upload_header', [
    m('div.upload_header_title', 'Uploaded Files'),
    UploadButton(upload),
  ]);
};

export const UploadButton = (upload: UploadNavState) => {
  return m('div.upload_header_button', [
    m('input.upload_header_button_input', {
      type: 'file',
      id: 'fileInput',
      style: 'display:none',
      accept: '.py',
      onchange: async function (e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files !== null) {
          let exists = false;
          const uploadedFile = target.files[0];
          upload.files.forEach((file: RawFile) => {
            if (file.name === uploadedFile.name) {
              exists = true;
            }
          });

          if (!exists) {
            const newFile = new RawFile(
              uploadedFile.name,
              uploadedFile.size,
              await uploadedFile.text()
            );
            upload.addFile(newFile);
          }
        }
      },
    }),
    m('button', {
      class: 'upload_header_button_view',
      innerText: 'Browse',
      onclick: (e: MouseEvent) => {
        animations.buttonPress(e.currentTarget as Element);
        document.getElementById('fileInput')?.click();
      },
    }),
  ]);
};

export const Files = (
  upload: UploadNavState,
  onFileClick: (file: RawFile) => void
) => {
  return m('div.upload_files', [
    upload.files.map((file: RawFile) =>
      m(File_Btn, {
        file: file,
        onFileClick,
      })
    ),
  ]);
};

export const File_Btn: m.Component<{ file: RawFile; onFileClick: (file: RawFile) => void }> = {
  view: function (vnode) {
    const { file, onFileClick } = vnode.attrs;
    let isDisabled = true;
    let ext = file.name.split('.').pop();

    // Check if the file extension is compatible
    const compatibleExtensions = ['py'];
    if (compatibleExtensions.includes(ext)) {
      isDisabled = false;
    }

    return m('div.file_container', [
      m(
        'div.file',
        {
          class: `file__${ext} ${isDisabled ? 'disabled' : ''}`,
          file: file,
          onclick: function (e: MouseEvent) {
            if (!isDisabled) {
              animations.buttonPress(e.currentTarget as Element);
              onFileClick(file);
            }
          },
        },
        file.name
      ),
    ]);
  },
};
