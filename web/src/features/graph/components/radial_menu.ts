/**
 * Radial/Donut Menu Component
 *
 * Context-aware circular menu for graph interactions
 */

import m from 'mithril';
import * as d3 from 'd3';
import './radial_menu.css';

export interface RadialMenuItem {
  id: string;
  label: string;
  icon?: string;
  action: () => void;
  enabled?: boolean;
  children?: RadialMenuItem[];
}

export interface RadialMenuContext {
  type: 'node' | 'edge' | 'canvas' | 'selection';
  target?: any;
  position: { x: number; y: number };
}

export interface RadialMenuOptions {
  items: RadialMenuItem[];
  context: RadialMenuContext;
  innerRadius?: number;
  outerRadius?: number;
  onClose?: () => void;
}

/**
 * Callback interface for radial menu actions
 */
export interface RadialMenuCallbacks {
  // Node actions
  onPinNode?: (node: any) => void;
  onHideNode?: (node: any) => void;
  onDeleteNode?: (node: any) => void;
  onColorNode?: (node: any, color: string) => void;
  onSelectNeighbors?: (node: any) => void;
  onExpandNode?: (node: any) => void;
  onCollapseNode?: (node: any) => void;

  // View actions
  onFitToScreen?: () => void;
  onCenterView?: () => void;
  onZoomIn?: () => void;
  onZoomOut?: () => void;

  // Layout actions
  onTogglePhysics?: () => void;
  onChangeLayout?: (layout: string) => void;

  // Organization actions
  onClusterByType?: () => void;
  onArrangeByDegree?: () => void;
  onArrangeHierarchical?: () => void;
  onSpreadNodes?: () => void;
  onCompactNodes?: () => void;

  // Filter actions
  onFilterByType?: (type: string) => void;
  onShowOnlyConnected?: () => void;
  onHideIsolated?: () => void;
  onHighlightCriticalPath?: () => void;

  // Selection actions
  onGroupSelection?: (nodes: any[]) => void;
  onAlignNodes?: (direction: 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom') => void;
  onDistributeNodes?: (direction: 'horizontal' | 'vertical') => void;
}

interface RadialMenuState {
  activeItem: string | null;
  submenuItems: RadialMenuItem[] | null;
  hoveredItem: string | null;
}

/**
 * Radial Menu Component
 *
 * Renders a circular/donut menu with context-aware actions
 */
export const RadialMenu: m.Component<RadialMenuOptions> = {
  oncreate(vnode) {
    const { items, context, innerRadius = 60, outerRadius = 120 } = vnode.attrs;
    const state: RadialMenuState = {
      activeItem: null,
      submenuItems: null,
      hoveredItem: null,
    };

    const container = vnode.dom as HTMLElement;
    const svg = d3.select(container).select('svg');

    // Create radial menu
    renderRadialMenu(svg, items, context, innerRadius, outerRadius, state, vnode.attrs.onClose);

    // Close menu on outside click
    const handleOutsideClick = (event: MouseEvent) => {
      if (!container.contains(event.target as Node)) {
        if (vnode.attrs.onClose) {
          vnode.attrs.onClose();
        }
      }
    };

    // Close menu on Escape
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && vnode.attrs.onClose) {
        vnode.attrs.onClose();
      }
    };

    setTimeout(() => {
      document.addEventListener('click', handleOutsideClick);
      document.addEventListener('keydown', handleEscape);
    }, 0);

    vnode.state = {
      cleanup: () => {
        document.removeEventListener('click', handleOutsideClick);
        document.removeEventListener('keydown', handleEscape);
      },
    };
  },

  onremove(vnode) {
    if (vnode.state.cleanup) {
      vnode.state.cleanup();
    }
  },

  view(vnode) {
    const { context } = vnode.attrs;

    return m(
      'div.radial-menu',
      {
        style: {
          position: 'fixed',
          left: `${context.position.x}px`,
          top: `${context.position.y}px`,
          transform: 'translate(-50%, -50%)',
          'z-index': 1000,
          'pointer-events': 'all',
        },
      },
      m('svg', {
        width: 300,
        height: 300,
        viewBox: '-150 -150 300 300',
        style: {
          filter: 'drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3))',
        },
      })
    );
  },
};

/**
 * Render radial menu using D3
 */
function renderRadialMenu(
  svg: d3.Selection<SVGSVGElement, unknown, HTMLElement, any>,
  items: RadialMenuItem[],
  context: RadialMenuContext,
  innerRadius: number,
  outerRadius: number,
  state: RadialMenuState,
  onClose?: () => void
) {
  // Clear existing content
  svg.selectAll('*').remove();

  // Create main group
  const g = svg.append('g');

  // Get theme colors from CSS variables
  const rootStyles = getComputedStyle(document.documentElement);
  const secondaryColor = rootStyles.getPropertyValue('--c-secondary').trim() || '#00ff41';
  const primaryColor = rootStyles.getPropertyValue('--c-primary').trim() || '#0a0a0a';
  const primaryLightColor = rootStyles.getPropertyValue('--c-primary-light').trim() || '#1a1a1a';

  // Calculate arc angles
  const arc = d3
    .arc<d3.PieArcDatum<RadialMenuItem>>()
    .innerRadius(innerRadius)
    .outerRadius(outerRadius);

  const pie = d3
    .pie<RadialMenuItem>()
    .value(1)
    .sort(null);

  const arcs = pie(items.filter(item => item.enabled !== false));

  // Create menu segments
  const segments = g
    .selectAll('.menu-segment')
    .data(arcs)
    .enter()
    .append('g')
    .attr('class', 'menu-segment');

  // Draw arc backgrounds
  segments
    .append('path')
    .attr('class', 'menu-arc')
    .attr('d', arc)
    .attr('fill', (d, i) => {
      // Use theme-aware gradient
      const baseColor = d3.color(secondaryColor);
      if (!baseColor) return secondaryColor;
      const lightness = 0.6 - (i / items.length) * 0.3; // Vary lightness
      return d3.hsl(baseColor.formatHsl()).brighter(lightness).formatHex();
    })
    .attr('stroke', secondaryColor)
    .attr('stroke-width', 2)
    .attr('opacity', 0.85)
    .on('mouseenter', function (event, d) {
      state.hoveredItem = d.data.id;
      d3.select(this)
        .transition()
        .duration(150)
        .attr('opacity', 1)
        .attr(
          'd',
          d3
            .arc<d3.PieArcDatum<RadialMenuItem>>()
            .innerRadius(innerRadius)
            .outerRadius(outerRadius + 10) as any
        );
    })
    .on('mouseleave', function (event, d) {
      state.hoveredItem = null;
      d3.select(this)
        .transition()
        .duration(150)
        .attr('opacity', 0.8)
        .attr('d', arc);
    })
    .on('click', function (event, d) {
      event.stopPropagation();

      if (d.data.children && d.data.children.length > 0) {
        // Open submenu
        state.submenuItems = d.data.children;
        state.activeItem = d.data.id;
        // Re-render with submenu
        renderRadialMenu(svg, d.data.children, context, innerRadius + 20, outerRadius + 40, state, onClose);
      } else {
        // Execute action
        d.data.action();
        if (onClose) onClose();
      }
    });

  // Add labels
  segments
    .append('text')
    .attr('class', 'menu-label')
    .attr('transform', (d) => {
      const [x, y] = arc.centroid(d);
      return `translate(${x}, ${y})`;
    })
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .attr('fill', primaryColor)
    .attr('font-size', '12px')
    .attr('font-weight', 'bold')
    .attr('pointer-events', 'none')
    .text((d) => d.data.label);

  // Add icons if provided
  segments
    .filter((d) => d.data.icon)
    .append('text')
    .attr('class', 'menu-icon')
    .attr('transform', (d) => {
      const [x, y] = arc.centroid(d);
      return `translate(${x}, ${y - 15})`;
    })
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'middle')
    .attr('fill', primaryColor)
    .attr('font-size', '18px')
    .attr('pointer-events', 'none')
    .text((d) => d.data.icon || '');

  // Center circle with context info
  g.append('circle')
    .attr('cx', 0)
    .attr('cy', 0)
    .attr('r', innerRadius - 5)
    .attr('fill', primaryLightColor)
    .attr('stroke', secondaryColor)
    .attr('stroke-width', 2);

  g.append('text')
    .attr('x', 0)
    .attr('y', -10)
    .attr('text-anchor', 'middle')
    .attr('fill', secondaryColor)
    .attr('font-size', '10px')
    .attr('font-weight', 'bold')
    .text(context.type.toUpperCase());

  if (context.target?.label || context.target?.id) {
    g.append('text')
      .attr('x', 0)
      .attr('y', 10)
      .attr('text-anchor', 'middle')
      .attr('fill', secondaryColor)
      .attr('fill-opacity', 0.7)
      .attr('font-size', '8px')
      .text(context.target.label || context.target.id || '')
      .call(wrapText, innerRadius * 1.5);
  }

  // Back button if we have active submenu
  if (state.activeItem) {
    const backButton = g.append('g')
      .attr('class', 'back-button')
      .attr('cursor', 'pointer')
      .on('click', function () {
        // Go back to main menu
        state.activeItem = null;
        state.submenuItems = null;
        renderRadialMenu(svg, items, context, innerRadius, outerRadius, state, onClose);
      });

    backButton
      .append('circle')
      .attr('cx', 0)
      .attr('cy', innerRadius / 2)
      .attr('r', 15)
      .attr('fill', primaryLightColor)
      .attr('stroke', secondaryColor)
      .attr('stroke-width', 2);

    backButton
      .append('text')
      .attr('x', 0)
      .attr('y', innerRadius / 2)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .attr('fill', secondaryColor)
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text('←');
  }

  // Animate entrance
  segments
    .style('opacity', 0)
    .transition()
    .duration(300)
    .delay((d, i) => i * 30)
    .style('opacity', 1);
}

/**
 * Wrap text to fit within a given width
 */
function wrapText(text: d3.Selection<SVGTextElement, any, any, any>, width: number) {
  text.each(function () {
    const textEl = d3.select(this);
    const words = textEl.text().split(/\s+/).reverse();
    let word;
    let line: string[] = [];
    let lineNumber = 0;
    const lineHeight = 1.1;
    const y = textEl.attr('y');
    const dy = 0;
    let tspan = textEl
      .text(null)
      .append('tspan')
      .attr('x', 0)
      .attr('y', y)
      .attr('dy', `${dy}em`);

    while ((word = words.pop())) {
      line.push(word);
      tspan.text(line.join(' '));
      if (tspan.node()!.getComputedTextLength() > width) {
        line.pop();
        tspan.text(line.join(' '));
        line = [word];
        tspan = textEl
          .append('tspan')
          .attr('x', 0)
          .attr('y', y)
          .attr('dy', `${++lineNumber * lineHeight + dy}em`)
          .text(word);
      }
    }
  });
}

/**
 * Get context-aware menu items
 */
export function getContextMenuItems(
  context: RadialMenuContext,
  callbacks?: RadialMenuCallbacks
): RadialMenuItem[] {
  switch (context.type) {
    case 'node':
      return getNodeMenuItems(context.target, callbacks);
    case 'edge':
      return getEdgeMenuItems(context.target, callbacks);
    case 'selection':
      return getSelectionMenuItems(context.target, callbacks);
    case 'canvas':
    default:
      return getCanvasMenuItems(callbacks);
  }
}

/**
 * Node context menu items
 */
function getNodeMenuItems(node: any, callbacks?: RadialMenuCallbacks): RadialMenuItem[] {
  return [
    {
      id: 'actions',
      label: 'Actions',
      icon: '⚡',
      children: [
        {
          id: 'expand',
          label: 'Expand',
          icon: '+',
          action: () => {
            if (callbacks?.onExpandNode) callbacks.onExpandNode(node);
          },
        },
        {
          id: 'collapse',
          label: 'Collapse',
          icon: '−',
          action: () => {
            if (callbacks?.onCollapseNode) callbacks.onCollapseNode(node);
          },
        },
        {
          id: 'neighbors',
          label: 'Select Neighbors',
          icon: '🔗',
          action: () => {
            if (callbacks?.onSelectNeighbors) callbacks.onSelectNeighbors(node);
          },
        },
      ],
    },
    {
      id: 'pin',
      label: node.fx !== undefined ? 'Unpin' : 'Pin',
      icon: '📌',
      action: () => {
        if (callbacks?.onPinNode) callbacks.onPinNode(node);
      },
    },
    {
      id: 'style',
      label: 'Style',
      icon: '🎨',
      children: [
        {
          id: 'color-red',
          label: 'Red',
          action: () => {
            if (callbacks?.onColorNode) callbacks.onColorNode(node, '#ff3333');
          },
        },
        {
          id: 'color-blue',
          label: 'Blue',
          action: () => {
            if (callbacks?.onColorNode) callbacks.onColorNode(node, '#3366ff');
          },
        },
        {
          id: 'color-green',
          label: 'Green',
          action: () => {
            if (callbacks?.onColorNode) callbacks.onColorNode(node, '#00ff41');
          },
        },
        {
          id: 'color-yellow',
          label: 'Yellow',
          action: () => {
            if (callbacks?.onColorNode) callbacks.onColorNode(node, '#ffcc00');
          },
        },
        {
          id: 'color-purple',
          label: 'Purple',
          action: () => {
            if (callbacks?.onColorNode) callbacks.onColorNode(node, '#9b59b6');
          },
        },
        {
          id: 'color-orange',
          label: 'Orange',
          action: () => {
            if (callbacks?.onColorNode) callbacks.onColorNode(node, '#f39c12');
          },
        },
      ],
    },
    {
      id: 'hide',
      label: 'Hide',
      icon: '⊗',
      action: () => {
        if (callbacks?.onHideNode) callbacks.onHideNode(node);
      },
    },
    {
      id: 'delete',
      label: 'Delete',
      icon: '🗑',
      action: () => {
        if (callbacks?.onDeleteNode) callbacks.onDeleteNode(node);
      },
    },
    {
      id: 'info',
      label: 'Info',
      icon: 'ℹ',
      action: () => {
        const info = Object.entries(node)
          .filter(([key]) => !['x', 'y', 'fx', 'fy', 'vx', 'vy', 'index'].includes(key))
          .map(([key, value]) => `${key}: ${value}`)
          .join('\n');
        alert(`Node Information:\n\n${info}`);
      },
    },
  ];
}

/**
 * Edge context menu items
 */
function getEdgeMenuItems(edge: any, callbacks?: RadialMenuCallbacks): RadialMenuItem[] {
  return [
    {
      id: 'select-path',
      label: 'Select Path',
      icon: '↔',
      action: () => {
        // Select source and target nodes
        console.log('Select path', edge);
      },
    },
    {
      id: 'highlight',
      label: 'Highlight',
      icon: '✦',
      action: () => {
        console.log('Highlight edge', edge);
      },
    },
    {
      id: 'delete',
      label: 'Delete',
      icon: '🗑',
      action: () => {
        console.log('Delete edge', edge);
      },
    },
    {
      id: 'info',
      label: 'Info',
      icon: 'ℹ',
      action: () => {
        const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
        const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
        alert(`Edge: ${sourceId} → ${targetId}\nLabel: ${edge.label || 'none'}`);
      },
    },
  ];
}

/**
 * Selection context menu items
 */
function getSelectionMenuItems(selection: any, callbacks?: RadialMenuCallbacks): RadialMenuItem[] {
  return [
    {
      id: 'group',
      label: 'Group',
      icon: '▢',
      action: () => {
        if (callbacks?.onGroupSelection) callbacks.onGroupSelection(selection);
      },
    },
    {
      id: 'align',
      label: 'Align',
      icon: '⫴',
      children: [
        {
          id: 'align-left',
          label: 'Left',
          action: () => {
            if (callbacks?.onAlignNodes) callbacks.onAlignNodes('left');
          },
        },
        {
          id: 'align-center',
          label: 'Center H',
          action: () => {
            if (callbacks?.onAlignNodes) callbacks.onAlignNodes('center');
          },
        },
        {
          id: 'align-right',
          label: 'Right',
          action: () => {
            if (callbacks?.onAlignNodes) callbacks.onAlignNodes('right');
          },
        },
        {
          id: 'align-top',
          label: 'Top',
          action: () => {
            if (callbacks?.onAlignNodes) callbacks.onAlignNodes('top');
          },
        },
        {
          id: 'align-middle',
          label: 'Middle V',
          action: () => {
            if (callbacks?.onAlignNodes) callbacks.onAlignNodes('middle');
          },
        },
        {
          id: 'align-bottom',
          label: 'Bottom',
          action: () => {
            if (callbacks?.onAlignNodes) callbacks.onAlignNodes('bottom');
          },
        },
      ],
    },
    {
      id: 'distribute',
      label: 'Distribute',
      icon: '⫼',
      children: [
        {
          id: 'distribute-horizontal',
          label: 'Horizontal',
          action: () => {
            if (callbacks?.onDistributeNodes) callbacks.onDistributeNodes('horizontal');
          },
        },
        {
          id: 'distribute-vertical',
          label: 'Vertical',
          action: () => {
            if (callbacks?.onDistributeNodes) callbacks.onDistributeNodes('vertical');
          },
        },
      ],
    },
    {
      id: 'delete',
      label: 'Delete All',
      icon: '🗑',
      action: () => {
        selection.forEach((node: any) => {
          if (callbacks?.onDeleteNode) callbacks.onDeleteNode(node);
        });
      },
    },
  ];
}

/**
 * Canvas context menu items
 */
function getCanvasMenuItems(callbacks?: RadialMenuCallbacks): RadialMenuItem[] {
  return [
    {
      id: 'view',
      label: 'View',
      icon: '👁',
      children: [
        {
          id: 'fit',
          label: 'Fit to Screen',
          icon: '⛶',
          action: () => {
            if (callbacks?.onFitToScreen) callbacks.onFitToScreen();
          },
        },
        {
          id: 'center',
          label: 'Center',
          icon: '⊙',
          action: () => {
            if (callbacks?.onCenterView) callbacks.onCenterView();
          },
        },
        {
          id: 'zoom-in',
          label: 'Zoom In',
          icon: '+',
          action: () => {
            if (callbacks?.onZoomIn) callbacks.onZoomIn();
          },
        },
        {
          id: 'zoom-out',
          label: 'Zoom Out',
          icon: '−',
          action: () => {
            if (callbacks?.onZoomOut) callbacks.onZoomOut();
          },
        },
      ],
    },
    {
      id: 'organize',
      label: 'Organize',
      icon: '⚡',
      children: [
        {
          id: 'cluster-type',
          label: 'Cluster by Type',
          icon: '◈',
          action: () => {
            if (callbacks?.onClusterByType) callbacks.onClusterByType();
          },
        },
        {
          id: 'arrange-degree',
          label: 'Arrange by Degree',
          icon: '◆',
          action: () => {
            if (callbacks?.onArrangeByDegree) callbacks.onArrangeByDegree();
          },
        },
        {
          id: 'arrange-hierarchical',
          label: 'Hierarchical',
          icon: '⫸',
          action: () => {
            if (callbacks?.onArrangeHierarchical) callbacks.onArrangeHierarchical();
          },
        },
        {
          id: 'spread',
          label: 'Spread Out',
          icon: '⤨',
          action: () => {
            if (callbacks?.onSpreadNodes) callbacks.onSpreadNodes();
          },
        },
        {
          id: 'compact',
          label: 'Compact',
          icon: '⤧',
          action: () => {
            if (callbacks?.onCompactNodes) callbacks.onCompactNodes();
          },
        },
      ],
    },
    {
      id: 'filter',
      label: 'Filter',
      icon: '⚑',
      children: [
        {
          id: 'show-connected',
          label: 'Only Connected',
          icon: '🔗',
          action: () => {
            if (callbacks?.onShowOnlyConnected) callbacks.onShowOnlyConnected();
          },
        },
        {
          id: 'hide-isolated',
          label: 'Hide Isolated',
          icon: '⊗',
          action: () => {
            if (callbacks?.onHideIsolated) callbacks.onHideIsolated();
          },
        },
        {
          id: 'critical-path',
          label: 'Critical Path',
          icon: '⚠',
          action: () => {
            if (callbacks?.onHighlightCriticalPath) callbacks.onHighlightCriticalPath();
          },
        },
      ],
    },
    {
      id: 'layout',
      label: 'Layout',
      icon: '⚙',
      children: [
        {
          id: 'physics',
          label: 'Toggle Physics',
          icon: '⚡',
          action: () => {
            if (callbacks?.onTogglePhysics) callbacks.onTogglePhysics();
          },
        },
        {
          id: 'layout-spring',
          label: 'Spring',
          action: () => {
            if (callbacks?.onChangeLayout) callbacks.onChangeLayout('spring_layout');
          },
        },
        {
          id: 'layout-circular',
          label: 'Circular',
          action: () => {
            if (callbacks?.onChangeLayout) callbacks.onChangeLayout('circular_layout');
          },
        },
        {
          id: 'layout-kamada',
          label: 'Kamada-Kawai',
          action: () => {
            if (callbacks?.onChangeLayout) callbacks.onChangeLayout('kamada_kawai_layout');
          },
        },
        {
          id: 'layout-spectral',
          label: 'Spectral',
          action: () => {
            if (callbacks?.onChangeLayout) callbacks.onChangeLayout('spectral_layout');
          },
        },
      ],
    },
  ];
}
