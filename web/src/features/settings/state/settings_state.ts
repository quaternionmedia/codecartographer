/**
 * Settings Feature State
 *
 * State interface for application settings (theme, preferences, etc.)
 */

export interface SettingsState {
  theme: 'light' | 'dark';
  graphOptions: {
    defaultLayout: string;
    defaultType: 'd3' | 'three' | 'vis';
    showLabels: boolean;
    nodeSize: number;
    edgeWidth: number;
  };
  ui: {
    sidebarCollapsed: boolean;
    showWelcome: boolean;
  };
  palette: string;
}

export const DEFAULT_SETTINGS_STATE: SettingsState = {
  theme: 'dark',
  graphOptions: {
    defaultLayout: 'Spectral',
    defaultType: 'd3',
    showLabels: true,
    nodeSize: 1.0,
    edgeWidth: 1.0,
  },
  ui: {
    sidebarCollapsed: false,
    showWelcome: true,
  },
  palette: '0',
};
