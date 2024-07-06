import m from 'mithril';

import './codecarto.css';
import { ICell } from '../../state';
import { Plot } from '../plot/plot';
import { UrlInput } from '../url_input/url_input';

export const CodeCarto = (cell: ICell) => [title, UrlInput(cell), Plot(cell)];

const title = m('div.header', 'Code Cartographer');
