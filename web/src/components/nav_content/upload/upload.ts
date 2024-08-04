import m from 'mithril';

import { ICell } from '../../../state';
import './upload.css';

export const Upload = (
  cell: ICell,
  setUploadedFile: (file: object) => void
) => {
  return m('div.upload', [cell.state.upload_content]);
};
