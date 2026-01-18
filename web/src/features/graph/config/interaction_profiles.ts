/**
 * Graph Interaction Profiles
 *
 * Configurable control schemes for keyboard, mouse, and touch interactions
 */

export type InteractionMode = 'pan' | 'select' | 'zoom' | 'edit';

export interface KeyboardBinding {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  action: string;
  description: string;
}

export interface MouseBinding {
  button?: 'left' | 'right' | 'middle';
  modifier?: 'ctrl' | 'shift' | 'alt';
  gesture?: 'click' | 'doubleclick' | 'drag' | 'wheel';
  action: string;
  description: string;
}

export interface TouchBinding {
  gesture: 'tap' | 'doubletap' | 'longpress' | 'pinch' | 'pan' | 'swipe';
  fingers?: number;
  action: string;
  description: string;
}

export interface InteractionProfile {
  id: string;
  name: string;
  description: string;
  keyboard: KeyboardBinding[];
  mouse: MouseBinding[];
  touch: TouchBinding[];
}

/**
 * Default interaction profile - Standard graph navigation
 */
export const DEFAULT_PROFILE: InteractionProfile = {
  id: 'default',
  name: 'Standard',
  description: 'Standard graph navigation and interaction',
  keyboard: [
    // Navigation
    { key: 'ArrowUp', action: 'pan-up', description: 'Pan up' },
    { key: 'ArrowDown', action: 'pan-down', description: 'Pan down' },
    { key: 'ArrowLeft', action: 'pan-left', description: 'Pan left' },
    { key: 'ArrowRight', action: 'pan-right', description: 'Pan right' },
    { key: '+', action: 'zoom-in', description: 'Zoom in' },
    { key: '=', action: 'zoom-in', description: 'Zoom in' },
    { key: '-', action: 'zoom-out', description: 'Zoom out' },
    { key: '0', action: 'zoom-reset', description: 'Reset zoom' },

    // Selection
    { key: 'a', ctrl: true, action: 'select-all', description: 'Select all nodes' },
    { key: 'Escape', action: 'deselect-all', description: 'Clear selection' },

    // Node manipulation
    { key: 'Delete', action: 'delete-selected', description: 'Delete selected nodes' },
    { key: 'f', action: 'fit-to-screen', description: 'Fit graph to screen' },
    { key: 'c', action: 'center-selection', description: 'Center on selection' },

    // Physics
    { key: ' ', action: 'toggle-physics', description: 'Toggle physics simulation' },
    { key: 'r', action: 'restart-simulation', description: 'Restart simulation' },

    // Context menu
    { key: 'm', action: 'open-menu', description: 'Open radial menu' },
    { key: 's', ctrl: true, action: 'save-layout', description: 'Save layout' },
  ],
  mouse: [
    // Click actions
    { button: 'left', gesture: 'click', action: 'select-node', description: 'Select node' },
    { button: 'left', gesture: 'click', modifier: 'ctrl', action: 'toggle-select-node', description: 'Toggle node selection' },
    { button: 'left', gesture: 'doubleclick', action: 'expand-node', description: 'Expand/collapse node' },
    { button: 'right', gesture: 'click', action: 'open-context-menu', description: 'Open context menu' },

    // Drag actions
    { button: 'left', gesture: 'drag', action: 'drag-node', description: 'Drag node' },
    { button: 'left', gesture: 'drag', modifier: 'shift', action: 'box-select', description: 'Box selection' },
    { button: 'middle', gesture: 'drag', action: 'pan-canvas', description: 'Pan canvas' },

    // Wheel
    { gesture: 'wheel', action: 'zoom', description: 'Zoom in/out' },
    { gesture: 'wheel', modifier: 'shift', action: 'pan-horizontal', description: 'Pan horizontally' },
  ],
  touch: [
    { gesture: 'tap', fingers: 1, action: 'select-node', description: 'Select node' },
    { gesture: 'doubletap', fingers: 1, action: 'expand-node', description: 'Expand/collapse node' },
    { gesture: 'longpress', fingers: 1, action: 'open-context-menu', description: 'Open context menu' },
    { gesture: 'pan', fingers: 1, action: 'drag-node', description: 'Drag node' },
    { gesture: 'pan', fingers: 2, action: 'pan-canvas', description: 'Pan canvas' },
    { gesture: 'pinch', fingers: 2, action: 'zoom', description: 'Pinch to zoom' },
    { gesture: 'swipe', fingers: 3, action: 'open-menu', description: 'Open radial menu' },
  ],
};

/**
 * CAD-style profile - Focus on precision and editing
 */
export const CAD_PROFILE: InteractionProfile = {
  id: 'cad',
  name: 'CAD',
  description: 'CAD-style controls with precision editing',
  keyboard: [
    // Navigation
    { key: 'w', action: 'pan-up', description: 'Pan up' },
    { key: 's', action: 'pan-down', description: 'Pan down' },
    { key: 'a', action: 'pan-left', description: 'Pan left' },
    { key: 'd', action: 'pan-right', description: 'Pan right' },
    { key: 'q', action: 'zoom-in', description: 'Zoom in' },
    { key: 'e', action: 'zoom-out', description: 'Zoom out' },
    { key: 'z', action: 'zoom-reset', description: 'Reset zoom' },
    { key: 'f', action: 'fit-to-screen', description: 'Fit to screen' },

    // Selection
    { key: 'Escape', action: 'deselect-all', description: 'Clear selection' },
    { key: 'i', action: 'invert-selection', description: 'Invert selection' },

    // Edit mode
    { key: 'm', action: 'move-mode', description: 'Move mode' },
    { key: 'r', action: 'rotate-mode', description: 'Rotate mode' },
    { key: 'g', action: 'grab-mode', description: 'Grab mode' },
    { key: 'Delete', action: 'delete-selected', description: 'Delete selected' },

    // Context menu
    { key: 'Tab', action: 'open-menu', description: 'Open radial menu' },
  ],
  mouse: [
    { button: 'left', gesture: 'click', action: 'select-node', description: 'Select node' },
    { button: 'left', gesture: 'drag', action: 'drag-node', description: 'Drag node' },
    { button: 'middle', gesture: 'drag', action: 'pan-canvas', description: 'Pan canvas' },
    { button: 'right', gesture: 'click', action: 'open-context-menu', description: 'Context menu' },
    { gesture: 'wheel', action: 'zoom', description: 'Zoom' },
  ],
  touch: [
    { gesture: 'tap', fingers: 1, action: 'select-node', description: 'Select' },
    { gesture: 'longpress', fingers: 1, action: 'open-context-menu', description: 'Context menu' },
    { gesture: 'pan', fingers: 1, action: 'drag-node', description: 'Drag node' },
    { gesture: 'pan', fingers: 2, action: 'pan-canvas', description: 'Pan' },
    { gesture: 'pinch', fingers: 2, action: 'zoom', description: 'Zoom' },
  ],
};

/**
 * Gaming profile - Familiar WASD controls
 */
export const GAMING_PROFILE: InteractionProfile = {
  id: 'gaming',
  name: 'Gaming',
  description: 'WASD controls familiar to gamers',
  keyboard: [
    // WASD navigation
    { key: 'w', action: 'pan-up', description: 'Move up' },
    { key: 's', action: 'pan-down', description: 'Move down' },
    { key: 'a', action: 'pan-left', description: 'Move left' },
    { key: 'd', action: 'pan-right', description: 'Move right' },

    // Zoom
    { key: 'q', action: 'zoom-out', description: 'Zoom out' },
    { key: 'e', action: 'zoom-in', description: 'Zoom in' },
    { key: 'r', action: 'zoom-reset', description: 'Reset view' },
    { key: 'f', action: 'fit-to-screen', description: 'Fit to screen' },

    // Selection
    { key: 'Shift', action: 'multi-select-mode', description: 'Multi-select mode' },
    { key: 'Escape', action: 'deselect-all', description: 'Deselect' },

    // Actions
    { key: ' ', action: 'toggle-physics', description: 'Toggle physics' },
    { key: 'Tab', action: 'open-menu', description: 'Open menu' },
    { key: 'c', action: 'center-selection', description: 'Center on selection' },
  ],
  mouse: [
    { button: 'left', gesture: 'click', action: 'select-node', description: 'Select' },
    { button: 'left', gesture: 'drag', action: 'drag-node', description: 'Drag' },
    { button: 'right', gesture: 'drag', action: 'pan-canvas', description: 'Pan' },
    { button: 'right', gesture: 'click', action: 'open-context-menu', description: 'Menu' },
    { gesture: 'wheel', action: 'zoom', description: 'Zoom' },
  ],
  touch: [
    { gesture: 'tap', fingers: 1, action: 'select-node', description: 'Select' },
    { gesture: 'doubletap', fingers: 2, action: 'open-menu', description: 'Menu' },
    { gesture: 'pan', fingers: 1, action: 'drag-node', description: 'Drag' },
    { gesture: 'pan', fingers: 2, action: 'pan-canvas', description: 'Pan' },
    { gesture: 'pinch', fingers: 2, action: 'zoom', description: 'Zoom' },
  ],
};

/**
 * Touch-optimized profile - Large targets, simple gestures
 */
export const TOUCH_PROFILE: InteractionProfile = {
  id: 'touch',
  name: 'Touch',
  description: 'Optimized for touchscreen devices',
  keyboard: [
    { key: 'Escape', action: 'deselect-all', description: 'Clear selection' },
    { key: ' ', action: 'toggle-physics', description: 'Toggle physics' },
  ],
  mouse: [
    { button: 'left', gesture: 'click', action: 'select-node', description: 'Select' },
    { button: 'left', gesture: 'drag', action: 'drag-node', description: 'Drag' },
    { gesture: 'wheel', action: 'zoom', description: 'Zoom' },
  ],
  touch: [
    // Simple, clear gestures
    { gesture: 'tap', fingers: 1, action: 'select-node', description: 'Tap to select' },
    { gesture: 'doubletap', fingers: 1, action: 'expand-node', description: 'Double-tap to expand' },
    { gesture: 'longpress', fingers: 1, action: 'open-context-menu', description: 'Long-press for menu' },

    // Navigation
    { gesture: 'pan', fingers: 1, action: 'drag-node', description: 'Drag node' },
    { gesture: 'pan', fingers: 2, action: 'pan-canvas', description: 'Two-finger pan' },
    { gesture: 'pinch', fingers: 2, action: 'zoom', description: 'Pinch to zoom' },

    // Menu
    { gesture: 'swipe', fingers: 3, action: 'open-menu', description: 'Three-finger swipe for menu' },
  ],
};

/**
 * All available profiles
 */
export const INTERACTION_PROFILES: InteractionProfile[] = [
  DEFAULT_PROFILE,
  CAD_PROFILE,
  GAMING_PROFILE,
  TOUCH_PROFILE,
];

/**
 * Get profile by ID
 */
export function getProfile(id: string): InteractionProfile {
  return INTERACTION_PROFILES.find(p => p.id === id) || DEFAULT_PROFILE;
}

/**
 * Get profile names for UI selection
 */
export function getProfileOptions(): Array<{ value: string; label: string; description: string }> {
  return INTERACTION_PROFILES.map(p => ({
    value: p.id,
    label: p.name,
    description: p.description,
  }));
}
