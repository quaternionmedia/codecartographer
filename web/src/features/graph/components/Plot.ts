/**
 * Plot Component
 *
 * Main graph visualization container
 */
import m from 'mithril';
import './plot/plot.css';

interface PlotAttrs {
  graphs: m.Vnode[];
}

/** Plot component for displaying graph visualizations */
export const Plot: m.Component<PlotAttrs> = {
  view(vnode) {
    const { graphs } = vnode.attrs;
    const hasContent = graphs && graphs.length > 0;

    return m('div.plot', [
      hasContent
        ? m('div.graph', graphs)
        : m('div.plot--empty', [
            m('span.plot__empty-icon', '◇'),
            m('p.plot__empty-text',
              'No visualization loaded. Use the control panel below to load a demo, fetch a GitHub repository, or upload Python files.'
            ),
          ])
    ]);
  },
};
