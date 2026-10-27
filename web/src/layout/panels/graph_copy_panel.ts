/**
 * A copy of the graph in a window of its own.
 *
 * The Graph window's ⧉ button opens one (`LayoutContext.duplicateGraph`): a tab
 * beside the canvas that can be dragged anywhere in the dock, drawing the graph
 * as it was when the copy was made. It pans and zooms apart from the canvas,
 * and carries its own key; the ring stays with the canvas. Any number can be
 * open, each its own `graph-copy-<n>`. Opened again from a saved layout, with
 * no graph kept for it, a copy draws what is on the canvas.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import type { GraphData } from '../../features/graph/services/graph_types';
import { drawCopy } from '../../features/graph/services/d3_renderer';
import { LegendExtension } from '../../features/graph/extensions/legend_extension';

/** The component type a copy is registered under in the dock. */
export const GRAPH_COPY = 'graph-copy';

export function createGraphCopyPanel(ctx: LayoutContext, snapshot: GraphData | null): m.Component {
  let legend: LegendExtension | null = null;
  return {
    oncreate: (vnode) => {
      const canvas = (vnode.dom as HTMLElement).querySelector<HTMLElement>('.graphRenderer');
      if (!canvas || !snapshot) return;
      const renderer = drawCopy(canvas, snapshot, ctx.appState.state.graphStyling);
      legend = new LegendExtension(() => ctx.appState.state.graphStyling.colorBy);
      legend.initialize(renderer.buildExtensionContext(new Set(), () => m.redraw()));
      // The key reads the scene once it is drawn: a few frames after the nodes are handed over.
      const settled = () => { legend?.apply(); };
      setTimeout(settled, 400);
    },
    onremove: () => {
      legend?.destroy();
      legend = null;
    },
    view: () => m('div.gl-panel.gl-panel--graph.gl-panel--graph-copy', [
      snapshot
        ? m('div.graph_content.graphRenderer.gl-graph-copy__canvas')
        : m('p.gl-graph-copy__empty', 'Nothing was drawn when this copy was made. Draw a graph, and duplicate it again.'),
    ]),
  };
}
