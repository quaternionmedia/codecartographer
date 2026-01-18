/**
 * GraphControls Component
 *
 * Interactive controls for graph visualization (layout, type, options)
 */
import m from 'mithril';
import { Select } from '../../../components/qm_comp_lib/form';

interface GraphControlsAttrs {
  layout: string;
  type: 'd3' | 'three' | 'vis';
  showLabels: boolean;
  onLayoutChange: (layout: string) => void;
  onTypeChange: (type: 'd3' | 'three' | 'vis') => void;
  onToggleLabels: () => void;
}

export const GraphControls: m.Component<GraphControlsAttrs> = {
  view(vnode) {
    const { layout, type, showLabels, onLayoutChange, onTypeChange, onToggleLabels } = vnode.attrs;

    return m('.graph-controls', [
      m('.control-group', [
        m('label.control-label', 'Layout'),
        m(Select, {
          value: layout,
          options: [
            { value: 'Spring', label: 'Spring (Force-Directed)' },
            { value: 'Spectral', label: 'Spectral' },
            { value: 'Kamada_Kawai', label: 'Kamada-Kawai' },
            { value: 'Circular', label: 'Circular' },
            { value: 'Shell', label: 'Shell' },
          ],
          onChange: onLayoutChange,
        }),
      ]),

      m('.control-group', [
        m('label.control-label', 'Renderer'),
        m(Select, {
          value: type,
          options: [
            { value: 'd3', label: 'D3.js (2D)' },
            { value: 'three', label: 'Three.js (3D)' },
            { value: 'vis', label: 'vis.js' },
          ],
          onChange: onTypeChange,
        }),
      ]),

      m('.control-group', [
        m('label.control-label', [
          m('input[type=checkbox]', {
            checked: showLabels,
            onchange: onToggleLabels,
          }),
          ' Show Labels',
        ]),
      ]),
    ]);
  },
};
