import m from 'mithril';

import { ICell } from '../../state';
import { Directory } from '../directory/directory';
import { Nav } from '../navigation/nav';

export const Plot = (cell: ICell, setSelectedUrl: (url: string) => void) =>
  m('div', { class: 'plot' }, DirectoryNav(cell, setSelectedUrl));

const DirectoryNav = (cell: ICell, setSelectedUrl: (url: string) => void) =>
  Nav(cell, 'showContentNav', Directory(cell, setSelectedUrl));
