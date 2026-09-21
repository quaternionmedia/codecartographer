import type { LayoutConfig } from 'golden-layout';

/**
 * Default Golden Layout configuration for Code Cartographer.
 *
 * Panels:
 *   • file-tree   — left sidebar: repository / upload browser
 *   • graph       — main area: the streaming canvas
 *   • upload-panel    — bottom tab, active: local file dropzone and Load Demo
 *   • repo-panel      — bottom tab: GitHub URL fetch + recent/examples
 *   • graph-settings  — bottom tab: graph styling controls
 *   • plotbar         — bottom tab: plot/cancel/status
 *   • estate-panel    — bottom tab: which seams are up, before anything is drawn
 *
 * The other estate panels (Topology, Capabilities, Overview) are reached from
 * the "+" menu or from a live row in the Estate panel; they are not opened by
 * default because each asks its seam on open, and a fresh workstation has none.
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
      // `id` on every entry, equal to its registry id. `findFirstComponentItemById`
      // is how a panel is found to be focused or re-opened, and an entry without
      // one is invisible to it: bringing the canvas to the front after a draw
      // silently did nothing, and re-opening it would have added a second one.
      {
        type: 'component',
        componentType: 'graph',
        title: '◈ Graph',
        id: 'graph',
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
            id: 'file-tree',
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
              // Present in the dock so a cold reader finds it, and not the
              // active tab: Upload stays active because Load Demo lives there
              // and is the first thing a new reader is told to press.
              {
                type: 'component',
                componentType: 'estate-panel',
                title: '⌂ Estate',
                id: 'estate-panel',
                isClosable: true,
              },
            ],
          },
        ],
      },
    ],
  },
};
