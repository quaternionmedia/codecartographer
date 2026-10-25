import m from 'mithril';

import './plot.css';

interface PlotAttrs {
  graphs: m.Vnode[];
}

/** Plot component for displaying graph visualizations */
export const PlotComponent: m.Component<PlotAttrs> = {
  view(vnode) {
    const { graphs } = vnode.attrs;
    const hasContent = graphs && graphs.length > 0;
    
    return m('div.plot', [
      hasContent 
        ? m('div.graph', graphs)
        : m('div.plot--empty', [
            m('span.plot__empty-icon', '◇'),
            m('p.plot__empty-text', 
              'No graph drawn yet. Open a repository, add files or press ⚡ Load Demo in the Open panel.'
            ),
          ])
    ]);
  },
};

/** Legacy function-based Plot for backward compatibility */
export const Plot = (graph: m.Vnode[]) => {
  return m(PlotComponent, { graphs: graph });
};
