import m from 'mithril';

import { ICell } from '../../../state';
import './upload.css';

export const Upload = (
  cell: ICell,
  setSelectedUploadedFile: (file: File) => void
) => {
  var contents = [];

  if (cell.state.uploaded_files.length > 0) {
    var plot = m(
      'button.plot_btn',
      {
        onclick: function () {
          if (cell.state.uploaded_files[0] !== undefined) {
            setSelectedUploadedFile(cell.state.uploaded_files[0]);
          }
        },
      },
      'Plot Uploaded File'
    );

    var contents = [m('div.upload_tree', [cell.state.uploaded_files]), plot];
  }

  cell.update({ upload_content: contents });

  return m('div.upload', [
    UploadHeader(cell),
    cell.state.upload_content.length > 0
      ? UploadedFiles(cell, setSelectedUploadedFile)
      : null,
  ]);
};

export const UploadHeader = (cell: ICell) => {
  var title = 'Uploaded Files';
  return m('div.upload_header', [
    m('div.upload_header_title', title),
    UploadButton(cell),
  ]);
};

export const UploadButton = (cell: ICell) => {
  return m('div.upload_header_button', [
    m('input.upload_header_button_input', {
      type: 'file',
      id: 'fileInput',
      style: 'display:none',
      accept: '.py',
      onchange: function (e) {
        if (e.target.files !== null) {
          // Make sure selected file is not already in the list
          let exists = false;
          cell.state.uploaded_files.forEach((file: File) => {
            if (file.name === e.target.files[0].name) {
              exists = true;
            }
          });

          if (!exists) {
            // Add files to the cell state
            cell.state.uploaded_files.push(e.target.files[0]);
          }
        }
      },
    }),
    m('button', {
      class: 'upload_header_button_view',
      innerText: 'Browse',
      onclick: () => {
        document.getElementById('fileInput')?.click();
      },
    }),
  ]);
};

export const UploadedFiles = (
  cell: ICell,
  setSelectedUploadedFile: (file: File) => void
) => {
  return m('div.upload_files', [
    cell.state.uploaded_files.map((file: File) =>
      m(File, {
        file: file,
        setSelectedUploadedFile: setSelectedUploadedFile,
      })
    ),
  ]);
};

export const File = {
  view: function (vnode) {
    let { file, setSelectedUploadedFile } = vnode.attrs;
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
          onclick: function () {
            if (!isDisabled) {
              setSelectedUploadedFile(file);
            }
          },
        },
        file.name
      ),
    ]);
  },
};
