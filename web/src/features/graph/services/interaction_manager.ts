/**
 * Graph Interaction Manager
 *
 * Handles keyboard, mouse, and touch interactions for the graph visualization
 */

import * as d3 from 'd3';
import { InteractionProfile, getProfile } from '../config/interaction_profiles';
import { logger } from '../../../core/logger';

export interface GraphNode {
  id: string;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  [key: string]: unknown;
}

export interface InteractionManagerCallbacks {
  onNodeSelect?: (node: GraphNode, multiSelect: boolean) => void;
  onNodeDeselect?: () => void;
  onEdgeSelect?: (edge: GraphEdge) => void;
  onCanvasClick?: (position: { x: number; y: number }) => void;
  onContextMenu?: (context: { type: string; target?: any; position: { x: number; y: number } }) => void;
  onZoomChange?: (scale: number) => void;
  onFitToScreen?: () => void;
  onCenterSelection?: () => void;
  onDeleteSelected?: () => void;
  onTogglePhysics?: () => void;
  onRestartSimulation?: () => void;
  onSelectAll?: () => void;
}

export interface InteractionManagerOptions {
  profileId?: string;
  enableKeyboard?: boolean;
  enableMouse?: boolean;
  enableTouch?: boolean;
  panSpeed?: number;
  zoomSpeed?: number;
}

/**
 * Manages all graph interactions
 */
export class InteractionManager {
  private profile: InteractionProfile;
  private callbacks: InteractionManagerCallbacks;
  private options: Required<InteractionManagerOptions>;
  private selectedNodes: Set<GraphNode> = new Set();
  private selectedEdges: Set<GraphEdge> = new Set();
  private container: HTMLElement | null = null;
  private svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null;
  private zoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
  private currentTransform: d3.ZoomTransform = d3.zoomIdentity;

  // Touch gesture state
  private touchState: {
    startDistance: number | null;
    startAngle: number | null;
    longPressTimer: number | null;
    startPos: { x: number; y: number } | null;
  } = {
    startDistance: null,
    startAngle: null,
    longPressTimer: null,
    startPos: null,
  };

  constructor(callbacks: InteractionManagerCallbacks, options: InteractionManagerOptions = {}) {
    this.callbacks = callbacks;
    this.options = {
      profileId: options.profileId || 'default',
      enableKeyboard: options.enableKeyboard ?? true,
      enableMouse: options.enableMouse ?? true,
      enableTouch: options.enableTouch ?? true,
      panSpeed: options.panSpeed || 50,
      zoomSpeed: options.zoomSpeed || 0.1,
    };
    this.profile = getProfile(this.options.profileId);
  }

  /**
   * Initialize interactions on the graph
   */
  public initialize(
    container: HTMLElement,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
    zoom?: d3.ZoomBehavior<SVGSVGElement, unknown>
  ): void {
    this.container = container;
    this.svg = svg;
    this.zoom = zoom || null;

    if (this.options.enableKeyboard) {
      this.setupKeyboardListeners();
    }

    if (this.options.enableMouse) {
      this.setupMouseListeners();
    }

    if (this.options.enableTouch) {
      this.setupTouchListeners();
    }

    logger.debug('InteractionManager initialized with profile:', this.profile.name);
  }

  /**
   * Clean up event listeners
   */
  public destroy(): void {
    if (this.options.enableKeyboard) {
      document.removeEventListener('keydown', this.handleKeyDown);
    }

    if (this.touchState.longPressTimer) {
      clearTimeout(this.touchState.longPressTimer);
    }

    logger.debug('InteractionManager destroyed');
  }

  /**
   * Update interaction profile
   */
  public setProfile(profileId: string): void {
    this.profile = getProfile(profileId);
    logger.debug('InteractionManager profile changed to:', this.profile.name);
  }

  /**
   * Get current zoom transform
   */
  public getTransform(): d3.ZoomTransform {
    return this.currentTransform;
  }

  /**
   * Set up keyboard event listeners
   */
  private setupKeyboardListeners(): void {
    document.addEventListener('keydown', this.handleKeyDown);
  }

  /**
   * Handle keyboard events
   */
  private handleKeyDown = (event: KeyboardEvent): void => {
    // Find matching keyboard binding
    const binding = this.profile.keyboard.find(
      (b) =>
        b.key === event.key &&
        (b.ctrl === undefined || b.ctrl === event.ctrlKey) &&
        (b.shift === undefined || b.shift === event.shiftKey) &&
        (b.alt === undefined || b.alt === event.altKey)
    );

    if (!binding) return;

    event.preventDefault();
    this.executeAction(binding.action, event);
  };

  /**
   * Set up mouse event listeners
   * Note: Zoom/pan is handled by D3 in graph_renderer.ts to avoid conflicts
   */
  private setupMouseListeners(): void {
    if (!this.svg) return;

    // Mouse interactions are handled directly in graph_renderer.ts
    // to avoid conflicts with D3's zoom behavior
    // Only keyboard and touch gestures are managed here
    logger.debug('Mouse interactions managed by D3 zoom in graph_renderer');
  }

  /**
   * Set up touch event listeners
   */
  private setupTouchListeners(): void {
    if (!this.container) return;

    this.container.addEventListener('touchstart', this.handleTouchStart, { passive: false });
    this.container.addEventListener('touchmove', this.handleTouchMove, { passive: false });
    this.container.addEventListener('touchend', this.handleTouchEnd, { passive: false });
  }

  /**
   * Handle touch start
   */
  private handleTouchStart = (event: TouchEvent): void => {
    const touches = event.touches;

    if (touches.length === 1) {
      // Single touch - possibly tap or long press
      const touch = touches[0];
      this.touchState.startPos = { x: touch.clientX, y: touch.clientY };

      // Set up long press timer
      this.touchState.longPressTimer = window.setTimeout(() => {
        const binding = this.profile.touch.find((b) => b.gesture === 'longpress' && b.fingers === 1);
        if (binding) {
          this.executeAction(binding.action, event);
        }
      }, 500);
    } else if (touches.length === 2) {
      // Two finger touch - pinch zoom or pan
      event.preventDefault();

      const touch1 = touches[0];
      const touch2 = touches[1];

      this.touchState.startDistance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );
      this.touchState.startAngle = Math.atan2(
        touch2.clientY - touch1.clientY,
        touch2.clientX - touch1.clientX
      );

      // Clear long press timer
      if (this.touchState.longPressTimer) {
        clearTimeout(this.touchState.longPressTimer);
        this.touchState.longPressTimer = null;
      }
    }
  };

  /**
   * Handle touch move
   */
  private handleTouchMove = (event: TouchEvent): void => {
    const touches = event.touches;

    // Clear long press timer on move
    if (this.touchState.longPressTimer) {
      clearTimeout(this.touchState.longPressTimer);
      this.touchState.longPressTimer = null;
    }

    if (touches.length === 2 && this.touchState.startDistance !== null) {
      // Two finger pinch/pan
      event.preventDefault();

      const touch1 = touches[0];
      const touch2 = touches[1];

      const currentDistance = Math.hypot(
        touch2.clientX - touch1.clientX,
        touch2.clientY - touch1.clientY
      );

      if (this.touchState.startDistance !== null) {
        const scale = currentDistance / this.touchState.startDistance;
        const binding = this.profile.touch.find((b) => b.gesture === 'pinch' && b.fingers === 2);
        if (binding && scale !== 1) {
          this.executeAction(binding.action, { scale, event });
        }
      }

      this.touchState.startDistance = currentDistance;
    }
  };

  /**
   * Handle touch end
   */
  private handleTouchEnd = (event: TouchEvent): void => {
    // Clear long press timer
    if (this.touchState.longPressTimer) {
      clearTimeout(this.touchState.longPressTimer);
      this.touchState.longPressTimer = null;
    }

    const touches = event.changedTouches;

    if (touches.length === 1 && this.touchState.startPos) {
      // Single tap
      const touch = touches[0];
      const distance = Math.hypot(
        touch.clientX - this.touchState.startPos.x,
        touch.clientY - this.touchState.startPos.y
      );

      if (distance < 10) {
        // It's a tap, not a drag
        const binding = this.profile.touch.find((b) => b.gesture === 'tap' && b.fingers === 1);
        if (binding) {
          this.executeAction(binding.action, event);
        }
      }
    }

    // Reset touch state
    this.touchState.startDistance = null;
    this.touchState.startAngle = null;
    this.touchState.startPos = null;
  };

  /**
   * Execute an action based on binding
   */
  private executeAction(action: string, event: any): void {
    logger.debug('Executing action:', action);

    switch (action) {
      // Navigation
      case 'pan-up':
        this.pan(0, -this.options.panSpeed);
        break;
      case 'pan-down':
        this.pan(0, this.options.panSpeed);
        break;
      case 'pan-left':
        this.pan(-this.options.panSpeed, 0);
        break;
      case 'pan-right':
        this.pan(this.options.panSpeed, 0);
        break;

      // Zoom
      case 'zoom-in':
        this.zoomBy(1 + this.options.zoomSpeed);
        break;
      case 'zoom-out':
        this.zoomBy(1 - this.options.zoomSpeed);
        break;
      case 'zoom-reset':
        this.zoomTo(1);
        break;
      case 'zoom':
        if (event.scale !== undefined) {
          this.zoomBy(event.scale);
        }
        break;

      // Selection
      case 'select-all':
        if (this.callbacks.onSelectAll) {
          this.callbacks.onSelectAll();
        }
        break;
      case 'deselect-all':
        this.clearSelection();
        break;

      // View
      case 'fit-to-screen':
        if (this.callbacks.onFitToScreen) {
          this.callbacks.onFitToScreen();
        }
        break;
      case 'center-selection':
        if (this.callbacks.onCenterSelection) {
          this.callbacks.onCenterSelection();
        }
        break;

      // Physics
      case 'toggle-physics':
        if (this.callbacks.onTogglePhysics) {
          this.callbacks.onTogglePhysics();
        }
        break;
      case 'restart-simulation':
        if (this.callbacks.onRestartSimulation) {
          this.callbacks.onRestartSimulation();
        }
        break;

      // Edit
      case 'delete-selected':
        if (this.callbacks.onDeleteSelected) {
          this.callbacks.onDeleteSelected();
        }
        break;

      // Context menu
      case 'open-menu':
      case 'open-context-menu':
        if (this.callbacks.onContextMenu) {
          const position = this.getEventPosition(event);
          this.callbacks.onContextMenu({
            type: 'canvas',
            position,
          });
        }
        break;

      default:
        logger.warn('Unknown action:', action);
    }
  }

  /**
   * Pan the view
   */
  private pan(dx: number, dy: number): void {
    if (!this.svg || !this.zoom) return;

    const newTransform = this.currentTransform.translate(dx / this.currentTransform.k, dy / this.currentTransform.k);
    this.svg.transition().duration(200).call(this.zoom.transform, newTransform);
  }

  /**
   * Zoom by a factor
   */
  private zoomBy(factor: number): void {
    if (!this.svg || !this.zoom) return;

    const newTransform = this.currentTransform.scale(factor);
    this.svg.transition().duration(200).call(this.zoom.transform, newTransform);
  }

  /**
   * Zoom to a specific level
   */
  private zoomTo(scale: number): void {
    if (!this.svg || !this.zoom) return;

    const newTransform = d3.zoomIdentity.translate(
      this.currentTransform.x,
      this.currentTransform.y
    ).scale(scale);
    this.svg.transition().duration(200).call(this.zoom.transform, newTransform);
  }

  /**
   * Clear all selections
   */
  private clearSelection(): void {
    this.selectedNodes.clear();
    this.selectedEdges.clear();
    if (this.callbacks.onNodeDeselect) {
      this.callbacks.onNodeDeselect();
    }
  }

  /**
   * Get position from event (works for mouse and touch)
   */
  private getEventPosition(event: any): { x: number; y: number } {
    if (event.touches && event.touches.length > 0) {
      return { x: event.touches[0].clientX, y: event.touches[0].clientY };
    }
    if (event.clientX !== undefined) {
      return { x: event.clientX, y: event.clientY };
    }
    return { x: 0, y: 0 };
  }

  /**
   * Select a node
   */
  public selectNode(node: GraphNode, multiSelect: boolean = false): void {
    if (!multiSelect) {
      this.clearSelection();
    }

    this.selectedNodes.add(node);

    if (this.callbacks.onNodeSelect) {
      this.callbacks.onNodeSelect(node, multiSelect);
    }
  }

  /**
   * Deselect a node
   */
  public deselectNode(node: GraphNode): void {
    this.selectedNodes.delete(node);

    if (this.selectedNodes.size === 0 && this.callbacks.onNodeDeselect) {
      this.callbacks.onNodeDeselect();
    }
  }

  /**
   * Get selected nodes
   */
  public getSelectedNodes(): Set<GraphNode> {
    return this.selectedNodes;
  }

  /**
   * Select an edge
   */
  public selectEdge(edge: GraphEdge): void {
    this.clearSelection();
    this.selectedEdges.add(edge);

    if (this.callbacks.onEdgeSelect) {
      this.callbacks.onEdgeSelect(edge);
    }
  }

  /**
   * Get selected edges
   */
  public getSelectedEdges(): Set<GraphEdge> {
    return this.selectedEdges;
  }
}
