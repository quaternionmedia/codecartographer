/**
 * UploadNav Component
 *
 * File upload interface with drag-and-drop
 */
import m from 'mithril';
import { RawFile } from '../../../components/models/source';
import { Button } from '../../../components/qm_comp_lib/form';

export interface UploadNavAttrs {
  files: RawFile[];
  onFilesSelected: (files: File[]) => void;
  onFileClick: (file: RawFile) => void;
  onPlotAll: () => void;
  onClear: () => void;
}

export const UploadNav: m.Component<UploadNavAttrs> = {
  view(vnode) {
    const { files, onFilesSelected, onFileClick, onPlotAll, onClear } = vnode.attrs;

    const handleFileInput = (e: Event) => {
      const target = e.target as HTMLInputElement;
      if (target.files && target.files.length > 0) {
        onFilesSelected(Array.from(target.files));
      }
    };

    const handleDrop = (e: DragEvent) => {
      e.preventDefault();
      if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
        onFilesSelected(Array.from(e.dataTransfer.files));
      }
    };

    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
    };

    return m('.upload-nav', [
      m('.upload-nav__dropzone', {
        ondrop: handleDrop,
        ondragover: handleDragOver,
      }, [
        m('.upload-nav__icon', '📁'),
        m('p', 'Drag and drop Python files here'),
        m('p.upload-nav__or', 'or'),
        m('label.btn.btn--primary', [
          'Browse Files',
          m('input[type=file]', {
            multiple: true,
            accept: '.py',
            style: 'display: none',
            onchange: handleFileInput,
          }),
        ]),
      ]),

      files.length > 0 && m('.upload-nav__files', [
        m('.upload-nav__header', [
          m('h4', `${files.length} file(s) uploaded`),
          m('.upload-nav__actions', [
            m(Button, {
              onclick: onPlotAll,
              size: 'small',
            }, 'Plot All'),
            m(Button, {
              onclick: onClear,
              variant: 'ghost',
              size: 'small',
            }, 'Clear'),
          ]),
        ]),

        m('ul.upload-nav__list', files.map(file =>
          m('li.upload-nav__item', {
            key: file.name,
            onclick: () => onFileClick(file),
          }, [
            m('span.upload-nav__file-icon', '🐍'),
            m('span.upload-nav__file-name', file.name),
            m('span.upload-nav__file-size', `${Math.round(file.size / 1024)}KB`),
          ])
        )),
      ]),
    ]);
  },
};
