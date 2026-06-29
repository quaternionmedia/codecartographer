import type { LayoutConfig } from 'golden-layout';

/**
 * Default Golden Layout configuration for Code Cartographer.
 *
 * Panels:
 *   • file-tree   — left sidebar: repository / upload browser
 *   • graph       — main area: D3 / vis-network visualisation
 *   • source      — bottom tab: source loader
 *   • graph-settings — bottom tab: graph styling controls
 */
export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  settings: {
    constrainDragToContainer: true,
    reorderEnabled: true,
    popoutWholeStack: false,
    blockedPopoutsThrowError: false,
    closePopoutsOnUnload: true,
    popInOnClose: true,
    responsiveMode: 'none',
  },
  header: {
    show: 'top',
    popout: 'Pop out',
    popin: 'Pop in',
    maximise: 'Maximise',
    close: 'Close',
    minimise: 'Minimise',
    tabDropdown: 'More tabs',
  },
  dimensions: {
    borderWidth: 4,
    borderGrabWidth: 8,
    defaultMinItemHeight: '60px',
    defaultMinItemWidth: '80px',
  },
  root: {
    type: 'row',
    content: [
      {
        type: 'component',
        componentType: 'file-tree',
        title: '◉ Files',
        width: 22,
        isClosable: true,
      },
      {
        type: 'column',
        width: 78,
        content: [
          {
            type: 'component',
            componentType: 'graph',
            title: '◈ Graph',
            height: 68,
            isClosable: true,
          },
          {
            type: 'stack',
            height: 32,
            id: 'dock-tab-stack',
            content: [
              {
                type: 'component',
                componentType: 'source-panel',
                title: 'Source',
                id: 'source-panel',
                isClosable: true,
              },
              {
                type: 'component',
                componentType: 'graph-settings-panel',
                title: 'Graph Settings',
                id: 'graph-settings-panel',
                isClosable: true,
              },
            ],
          },
        ],
      },
    ],
  },
};
