/**
 * Selection Extension
 *
 * Provides advanced selection capabilities including:
 * - Box selection (drag to select)
 * - Lasso selection (freeform path)
 * - Select by criteria
 * - Select neighbors
 * - Invert selection
 */

import * as d3 from 'd3';
import { BaseExtension, ExtensionContext } from './base';
import { logger } from '../../../core/logger';

export interface SelectionOptions {
  /** Enable box selection (Shift+Drag) */
  enableBoxSelect?: boolean;

  /** Enable lasso selection (Alt+Drag) */
  enableLassoSelect?: boolean;

  /** Box selection stroke color */
  boxStroke?: string;

  /** Box selection fill color */
  boxFill?: string;

  /** Lasso stroke color */
  lassoStroke?: string;

  /** Selection highlight color */
  selectionColor?: string;

  /** Selection highlight width */
  selectionWidth?: number;

  /** Callbacks */
  onSelectionChange?: (selected: Set<any>) => void;
}

export class SelectionExtension extends BaseExtension {
  private options: Required<SelectionOptions>;
  private boxSelection: d3.Selection<SVGRectElement, unknown, null, undefined> | null = null;
  private lassoSelection: d3.Selection<SVGPathElement, unknown, null, undefined> | null = null;
  private isBoxSelecting: boolean = false;
  private isLassoSelecting: boolean = false;
  private boxStart: { x: number; y: number } | null = null;
  private lassoPoints: Array<{ x: number; y: number }> = [];
  private isCtrlPressed: boolean = false;

  constructor(options: SelectionOptions = {}) {
    super('selection', 'Advanced Selection', 'Box selection, lasso selection, and selection utilities');

    // Get theme color for selection
    const rootStyles = getComputedStyle(document.documentElement);
    const secondaryColor = rootStyles.getPropertyValue('--c-secondary').trim() || '#00ff41';

    this.options = {
      enableBoxSelect: options.enableBoxSelect ?? true,
      enableLassoSelect: options.enableLassoSelect ?? true,
      boxStroke: options.boxStroke ?? secondaryColor,
      boxFill: options.boxFill ?? `${secondaryColor}20`,
      lassoStroke: options.lassoStroke ?? secondaryColor,
      selectionColor: options.selectionColor ?? secondaryColor,
      selectionWidth: options.selectionWidth ?? 3,
      onSelectionChange: options.onSelectionChange ?? (() => {}),
    };
  }

  public apply(): void {
    const context = this.assertContext();

    if (!this.enabled) {
      return;
    }

    // Apply selection mode to SVG
    if (this.options.enableBoxSelect || this.options.enableLassoSelect) {
      this.setupSelectionListeners(context);
    }

    logger.debug('SelectionExtension applied');
  }

  public destroy(): void {
    if (this.context) {
      this.context.svg.on('mousedown.selection', null);
      this.context.svg.on('mousemove.selection', null);
      this.context.svg.on('mouseup.selection', null);
    }

    if (this.boxSelection) {
      this.boxSelection.remove();
      this.boxSelection = null;
    }

    if (this.lassoSelection) {
      this.lassoSelection.remove();
      this.lassoSelection = null;
    }

    super.destroy();
  }

  /**
   * Setup selection event listeners
   */
  private setupSelectionListeners(context: ExtensionContext): void {
    // Track Ctrl key state
    document.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.ctrlKey || e.metaKey) {
        this.isCtrlPressed = true;
      }
    });
    document.addEventListener('keyup', (e: KeyboardEvent) => {
      if (!e.ctrlKey && !e.metaKey) {
        this.isCtrlPressed = false;
      }
    });

    context.svg
      .on('mousedown.selection', (event: MouseEvent) => {
        // Track Ctrl state from event
        this.isCtrlPressed = event.ctrlKey || event.metaKey;

        // Only activate on background (not on nodes)
        if ((event.target as SVGElement).tagName === 'svg' ||
            (event.target as SVGElement).tagName === 'g') {

          if (event.shiftKey && this.options.enableBoxSelect) {
            this.startBoxSelection(event, context);
          } else if (event.altKey && this.options.enableLassoSelect) {
            this.startLassoSelection(event, context);
          }
        }
      })
      .on('mousemove.selection', (event: MouseEvent) => {
        // Update Ctrl state
        this.isCtrlPressed = event.ctrlKey || event.metaKey;

        if (this.isBoxSelecting) {
          this.updateBoxSelection(event, context);
        } else if (this.isLassoSelecting) {
          this.updateLassoSelection(event, context);
        }
      })
      .on('mouseup.selection', (event: MouseEvent) => {
        if (this.isBoxSelecting) {
          this.endBoxSelection(event, context);
        } else if (this.isLassoSelecting) {
          this.endLassoSelection(event, context);
        }
      });
  }

  /**
   * Start box selection
   */
  private startBoxSelection(event: MouseEvent, context: ExtensionContext): void {
    this.isBoxSelecting = true;

    const [x, y] = d3.pointer(event, context.svg.node());
    this.boxStart = { x, y };

    // Create selection box
    this.boxSelection = context.graphGroup
      .append('rect')
      .attr('class', 'selection-box')
      .attr('x', x)
      .attr('y', y)
      .attr('width', 0)
      .attr('height', 0)
      .attr('stroke', this.options.boxStroke)
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,5')
      .attr('fill', this.options.boxFill)
      .style('pointer-events', 'none');

    logger.debug('Box selection started at', this.boxStart);
  }

  /**
   * Update box selection
   */
  private updateBoxSelection(event: MouseEvent, context: ExtensionContext): void {
    if (!this.boxSelection || !this.boxStart) return;

    const [x, y] = d3.pointer(event, context.svg.node());

    const x1 = Math.min(this.boxStart.x, x);
    const y1 = Math.min(this.boxStart.y, y);
    const x2 = Math.max(this.boxStart.x, x);
    const y2 = Math.max(this.boxStart.y, y);

    this.boxSelection
      .attr('x', x1)
      .attr('y', y1)
      .attr('width', x2 - x1)
      .attr('height', y2 - y1);

    // Update selection in real-time
    this.selectNodesInBox({ x1, y1, x2, y2 }, context);
  }

  /**
   * End box selection
   */
  private endBoxSelection(event: MouseEvent, context: ExtensionContext): void {
    if (this.boxSelection) {
      this.boxSelection.remove();
      this.boxSelection = null;
    }

    this.isBoxSelecting = false;
    this.boxStart = null;

    logger.debug('Box selection ended, selected:', context.selectedNodes.size);
  }

  /**
   * Select nodes within box
   */
  private selectNodesInBox(
    box: { x1: number; y1: number; x2: number; y2: number },
    context: ExtensionContext
  ): void {
    const { x1, y1, x2, y2 } = box;

    // Clear previous selection if not holding Ctrl
    if (!this.isCtrlPressed) {
      this.clearSelection(context);
    }

    // Select nodes within box
    context.data.nodes.forEach((node: any) => {
      if (node.x >= x1 && node.x <= x2 && node.y >= y1 && node.y <= y2) {
        context.selectedNodes.add(node);
      }
    });

    // Update visual selection
    this.updateSelectionVisuals(context);

    // Callback
    this.options.onSelectionChange(context.selectedNodes);
  }

  /**
   * Start lasso selection
   */
  private startLassoSelection(event: MouseEvent, context: ExtensionContext): void {
    this.isLassoSelecting = true;
    this.lassoPoints = [];

    const [x, y] = d3.pointer(event, context.svg.node());
    this.lassoPoints.push({ x, y });

    // Create lasso path
    this.lassoSelection = context.graphGroup
      .append('path')
      .attr('class', 'selection-lasso')
      .attr('stroke', this.options.lassoStroke)
      .attr('stroke-width', 2)
      .attr('fill', 'none')
      .style('pointer-events', 'none');

    logger.debug('Lasso selection started');
  }

  /**
   * Update lasso selection
   */
  private updateLassoSelection(event: MouseEvent, context: ExtensionContext): void {
    if (!this.lassoSelection) return;

    const [x, y] = d3.pointer(event, context.svg.node());
    this.lassoPoints.push({ x, y });

    // Update lasso path
    const line = d3
      .line<{ x: number; y: number }>()
      .x((d) => d.x)
      .y((d) => d.y)
      .curve(d3.curveCatmullRomClosed.alpha(0.5));

    this.lassoSelection.attr('d', line(this.lassoPoints) || '');
  }

  /**
   * End lasso selection
   */
  private endLassoSelection(event: MouseEvent, context: ExtensionContext): void {
    if (this.lassoSelection && this.lassoPoints.length > 2) {
      // Select nodes within lasso
      this.selectNodesInLasso(this.lassoPoints, context);
    }

    if (this.lassoSelection) {
      this.lassoSelection.remove();
      this.lassoSelection = null;
    }

    this.isLassoSelecting = false;
    this.lassoPoints = [];

    logger.debug('Lasso selection ended');
  }

  /**
   * Select nodes within lasso using point-in-polygon test
   */
  private selectNodesInLasso(
    points: Array<{ x: number; y: number }>,
    context: ExtensionContext
  ): void {
    // Clear previous selection if not holding Ctrl
    if (!this.isCtrlPressed) {
      this.clearSelection(context);
    }

    // Select nodes within lasso path
    context.data.nodes.forEach((node: any) => {
      if (this.pointInPolygon({ x: node.x, y: node.y }, points)) {
        context.selectedNodes.add(node);
      }
    });

    // Update visual selection
    this.updateSelectionVisuals(context);

    // Callback
    this.options.onSelectionChange(context.selectedNodes);
  }

  /**
   * Point-in-polygon test (ray casting algorithm)
   */
  private pointInPolygon(
    point: { x: number; y: number },
    polygon: Array<{ x: number; y: number }>
  ): boolean {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].x;
      const yi = polygon[i].y;
      const xj = polygon[j].x;
      const yj = polygon[j].y;

      const intersect =
        yi > point.y !== yj > point.y &&
        point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;

      if (intersect) inside = !inside;
    }
    return inside;
  }

  /**
   * Clear all selections
   */
  private clearSelection(context: ExtensionContext): void {
    context.selectedNodes.clear();
    this.updateSelectionVisuals(context);
  }

  /**
   * Update visual representation of selected nodes
   */
  private updateSelectionVisuals(context: ExtensionContext): void {
    context.nodes
      .attr('stroke', (d: any) => {
        return context.selectedNodes.has(d) ? this.options.selectionColor : '#fff';
      })
      .attr('stroke-width', (d: any) => {
        return context.selectedNodes.has(d) ? this.options.selectionWidth : 1;
      });
  }

  /**
   * Public API: Select neighbors of currently selected nodes
   */
  public selectNeighbors(context: ExtensionContext): void {
    const newSelection = new Set(context.selectedNodes);

    context.selectedNodes.forEach((node: any) => {
      // Find all edges connected to this node
      context.data.edges.forEach((edge: any) => {
        if (edge.source === node || edge.source.id === node.id) {
          newSelection.add(edge.target);
        }
        if (edge.target === node || edge.target.id === node.id) {
          newSelection.add(edge.source);
        }
      });
    });

    // Update selection
    newSelection.forEach((node) => context.selectedNodes.add(node));
    this.updateSelectionVisuals(context);

    this.options.onSelectionChange(context.selectedNodes);

    logger.debug('Selected neighbors, total:', context.selectedNodes.size);
  }

  /**
   * Public API: Invert selection
   */
  public invertSelection(context: ExtensionContext): void {
    const newSelection = new Set<any>();

    context.data.nodes.forEach((node: any) => {
      if (!context.selectedNodes.has(node)) {
        newSelection.add(node);
      }
    });

    context.selectedNodes.clear();
    newSelection.forEach((node) => context.selectedNodes.add(node));

    this.updateSelectionVisuals(context);
    this.options.onSelectionChange(context.selectedNodes);

    logger.debug('Inverted selection, total:', context.selectedNodes.size);
  }

  /**
   * Public API: Select all nodes
   */
  public selectAll(context: ExtensionContext): void {
    context.selectedNodes.clear();
    context.data.nodes.forEach((node: any) => context.selectedNodes.add(node));

    this.updateSelectionVisuals(context);
    this.options.onSelectionChange(context.selectedNodes);

    logger.debug('Selected all nodes:', context.selectedNodes.size);
  }
}
