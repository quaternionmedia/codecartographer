import m from 'mithril';

import { ICell } from '../../state';
import './plot.css';

export const Plot = (cell: ICell) => {
  return m('div.plot', [Graph(cell)]);
};

const Graph = (cell: ICell) => m('div.graph', [cell.state.graph_content]);
