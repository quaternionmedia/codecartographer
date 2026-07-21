/**
 * Settings Feature Actions
 *
 * Action creators for settings state updates
 */
import { SettingsState, DEFAULT_SETTINGS_STATE } from './settings_state';

export const settingsActions = {
  /**
   * Set theme (light/dark)
   */
  setTheme: (theme: 'light' | 'dark') => (state: SettingsState): SettingsState => ({
    ...state,
    theme,
  }),

  /**
   * Update graph options
   */
  setGraphOptions: (options: Partial<SettingsState['graphOptions']>) => (state: SettingsState): SettingsState => ({
    ...state,
    graphOptions: { ...state.graphOptions, ...options },
  }),

  /**
   * Update UI preferences
   */
  setUiPreferences: (preferences: Partial<SettingsState['ui']>) => (state: SettingsState): SettingsState => ({
    ...state,
    ui: { ...state.ui, ...preferences },
  }),

  /**
   * Set color palette
   */
  setPalette: (palette: string) => (state: SettingsState): SettingsState => ({
    ...state,
    palette,
  }),

  /**
   * Toggle sidebar collapsed state
   */
  toggleSidebar: () => (state: SettingsState): SettingsState => ({
    ...state,
    ui: { ...state.ui, sidebarCollapsed: !state.ui.sidebarCollapsed },
  }),

  /**
   * Dismiss welcome message
   */
  dismissWelcome: () => (state: SettingsState): SettingsState => ({
    ...state,
    ui: { ...state.ui, showWelcome: false },
  }),

  /**
   * Reset to default settings
   */
  reset: () => (): SettingsState => DEFAULT_SETTINGS_STATE,
};
