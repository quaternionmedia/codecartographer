import m from 'mithril';

import './plot.css';

export const Plot = (graph: m.Vnode[]) => {
  return m('div.plot', [m('div.graph', [graph])]);
};
