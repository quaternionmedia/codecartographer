import type { LayoutConfig } from 'golden-layout';

/**
 * Default Golden Layout configuration for Code Cartographer.
 *
 * Panels:
 *   • file-tree   — left sidebar: repository / upload browser
 *   • graph       — main area: D3 / vis-network visualisation
 *   • control-panel — bottom drawer: source loader + graph controls
 */
export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  settings: {
    constrainDragToContainer: true,
    reorderEnabled: true,
    popoutWholeStack: false,
    blockedPopoutsThrowError: false,
    closePopoutsOnUnload: true,
    responsiveMode: 'none',
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
        isClosable: false,
      },
      {
        type: 'column',
        width: 78,
        content: [
          {
            type: 'component',
            componentType: 'graph',
            title: '◈ Graph',
            height: 70,
            isClosable: false,
          },
          {
            type: 'component',
            componentType: 'control-panel',
            title: '⚙ Controls',
            height: 30,
            isClosable: false,
          },
        ],
      },
    ],
  },
};
