/**
 * SettingsPanel Component
 *
 * Configuration panel for application settings (theme, defaults, preferences)
 */
import m from 'mithril';
import { Select, Button } from '../../../components/qm_comp_lib/form';

export interface SettingsPanelAttrs {
  theme: 'light' | 'dark';
  palette: string;
  defaultLayout: string;
  defaultType: 'd3' | 'three' | 'vis';
  showLabels: boolean;
  onThemeChange: (theme: 'light' | 'dark') => void;
  onPaletteChange: (palette: string) => void;
  onDefaultLayoutChange: (layout: string) => void;
  onDefaultTypeChange: (type: 'd3' | 'three' | 'vis') => void;
  onToggleLabels: () => void;
  onReset: () => void;
}

export const SettingsPanel: m.Component<SettingsPanelAttrs> = {
  view(vnode) {
    const {
      theme,
      palette,
      defaultLayout,
      defaultType,
      showLabels,
      onThemeChange,
      onPaletteChange,
      onDefaultLayoutChange,
      onDefaultTypeChange,
      onToggleLabels,
      onReset,
    } = vnode.attrs;

    return m('.settings-panel', [
      m('.settings-panel__header', [
        m('h3', 'Settings'),
      ]),

      m('.settings-panel__section', [
        m('h4', 'Appearance'),

        m('.control-group', [
          m('label.control-label', 'Theme'),
          m(Select, {
            value: theme,
            options: [
              { value: 'dark', label: 'Dark' },
              { value: 'light', label: 'Light' },
            ],
            onChange: onThemeChange,
          }),
        ]),

        m('.control-group', [
          m('label.control-label', 'Color Palette'),
          m(Select, {
            value: palette,
            options: [
              { value: '0', label: 'Default' },
              { value: '1', label: 'Vibrant' },
              { value: '2', label: 'Pastel' },
              { value: '3', label: 'Monochrome' },
            ],
            onChange: onPaletteChange,
          }),
        ]),
      ]),

      m('.settings-panel__section', [
        m('h4', 'Graph Defaults'),

        m('.control-group', [
          m('label.control-label', 'Default Layout'),
          m(Select, {
            value: defaultLayout,
            options: [
              { value: 'Spring', label: 'Spring (Force-Directed)' },
              { value: 'Spectral', label: 'Spectral' },
              { value: 'Kamada_Kawai', label: 'Kamada-Kawai' },
              { value: 'Circular', label: 'Circular' },
              { value: 'Shell', label: 'Shell' },
            ],
            onChange: onDefaultLayoutChange,
          }),
        ]),

        m('.control-group', [
          m('label.control-label', 'Default Renderer'),
          m(Select, {
            value: defaultType,
            options: [
              { value: 'd3', label: 'D3.js (2D)' },
              { value: 'three', label: 'Three.js (3D)' },
              { value: 'vis', label: 'vis.js' },
            ],
            onChange: onDefaultTypeChange,
          }),
        ]),

        m('.control-group', [
          m('label.control-label', [
            m('input[type=checkbox]', {
              checked: showLabels,
              onchange: onToggleLabels,
            }),
            ' Show labels by default',
          ]),
        ]),
      ]),

      m('.settings-panel__footer', [
        m(Button, {
          label: 'Reset to Defaults',
          onClick: onReset,
          variant: 'ghost',
          size: 'small',
        }),
      ]),
    ]);
  },
};
