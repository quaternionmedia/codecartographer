import type { LayoutConfig } from 'golden-layout';

/**
 * Default Golden Layout configuration for Code Cartographer.
 *
 * Panels:
 *   • file-tree   — left sidebar: repository / upload browser
 *   • graph       — main area: D3 / vis-network visualisation
 *   • upload-panel    — bottom tab: local file dropzone
 *   • repo-panel      — bottom tab: GitHub URL fetch + recent/examples
 *   • graph-settings  — bottom tab: graph styling controls
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
    type: 'column',
    content: [
      {
        type: 'component',
        componentType: 'graph',
        title: '◈ Graph',
        height: 65,
        isClosable: true,
      },
      {
        type: 'row',
        height: 35,
        content: [
          {
            type: 'component',
            componentType: 'file-tree',
            title: '◉ Files',
            width: 22,
            isClosable: true,
          },
          {
            type: 'stack',
            width: 78,
            id: 'dock-tab-stack',
            content: [
              {
                type: 'component',
                componentType: 'upload-panel',
                title: '↑ Upload',
                id: 'upload-panel',
                isClosable: true,
              },
              {
                type: 'component',
                componentType: 'repo-panel',
                title: '⬇ Repository',
                id: 'repo-panel',
                isClosable: true,
              },
              {
                type: 'component',
                componentType: 'graph-settings-panel',
                title: 'Graph Settings',
                id: 'graph-settings-panel',
                isClosable: true,
              },
              {
                type: 'component',
                componentType: 'plotbar',
                title: '▶ Actions',
                id: 'plotbar',
                isClosable: true,
              },
            ],
          },
        ],
      },
    ],
  },
};
