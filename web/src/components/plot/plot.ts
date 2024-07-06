import m from 'mithril';

import { ICell } from '../../state';
import { Directory } from '../directory/directory';
import { Nav } from '../navigation/nav';

export const Plot = (cell: ICell) =>
  m('div', { class: 'plot' }, DirectoryNav(cell));

const DirectoryNav = (cell: ICell) =>
  Nav(cell, 'showContentNav', Directory(cell));
