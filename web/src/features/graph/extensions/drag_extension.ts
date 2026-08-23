/**
 * Drag Extension
 *
 * Provides advanced dragging capabilities including:
 * - Constrained dragging (grid snap, axis lock)
 * - Multi-node dragging
 * - Drag preview/ghost
 * - Drag callbacks and events
 */

import * as d3 from 'd3';
import { BaseExtension, ExtensionContext } from './base';
import { logger } from '../../../core/logger';

export interface DragOptions {
  /** Enable grid snapping */
  gridSnap?: boolean;

  /** Grid size for snapping (default: 20) */
  gridSize?: number;

  /** Lock dragging to X axis only */
  lockX?: boolean;

  /** Lock dragging to Y axis only */
  lockY?: boolean;

  /** Enable multi-node dragging */
  multiDrag?: boolean;

  /** Show ghost/preview while dragging */
  showGhost?: boolean;

  /** Alpha target for simulation during drag (default: 0.3) */
  alphaTarget?: number;

  /** Callbacks */
  onDragStart?: (node: any, event: d3.D3DragEvent<any, any, any>) => void;
  onDrag?: (node: any, event: d3.D3DragEvent<any, any, any>) => void;
  onDragEnd?: (node: any, event: d3.D3DragEvent<any, any, any>) => void;
}

export class DragExtension extends BaseExtension {
  private dragBehavior: d3.DragBehavior<SVGGElement, any, any> | null = null;
  private options: Required<DragOptions>;
  private draggedNodes: Set<any> = new Set();
  private initialPositions: Map<any, { x: number; y: number }> = new Map();

  constructor(options: DragOptions = {}) {
    super('drag', 'Advanced Drag', 'Enhanced node dragging with constraints and multi-drag support');

    // Set default options
    this.options = {
      gridSnap: options.gridSnap ?? false,
      gridSize: options.gridSize ?? 20,
      lockX: options.lockX ?? false,
      lockY: options.lockY ?? false,
      multiDrag: options.multiDrag ?? true,
      showGhost: options.showGhost ?? false,
      alphaTarget: options.alphaTarget ?? 0.3,
      onDragStart: options.onDragStart ?? (() => {}),
      onDrag: options.onDrag ?? (() => {}),
      onDragEnd: options.onDragEnd ?? (() => {}),
    };
  }

  public apply(): void {
    const context = this.assertContext();

    if (!this.enabled) {
      return;
    }

    // Create drag behavior
    this.dragBehavior = d3
      .drag<SVGGElement, any>()
      .on('start', (event, d) => this.handleDragStart(event, d, context))
      .on('drag', (event, d) => this.handleDrag(event, d, context))
      .on('end', (event, d) => this.handleDragEnd(event, d, context));

    // Apply drag to nodes
    context.nodes.call(this.dragBehavior);

    logger.debug('DragExtension applied with options:', this.options);
  }

  public destroy(): void {
    if (this.context && this.dragBehavior) {
      this.context.nodes.on('.drag', null);
    }
    this.dragBehavior = null;
    this.draggedNodes.clear();
    this.initialPositions.clear();
    super.destroy();
  }

  /**
   * Update drag options
   */
  public updateOptions(options: Partial<DragOptions>): void {
    this.options = { ...this.options, ...options };

    // Reapply if enabled
    if (this.enabled && this.context) {
      this.destroy();
      this.apply();
    }
  }

  /**
   * Snap value to grid
   */
  private snapToGrid(value: number): number {
    if (!this.options.gridSnap) {
      return value;
    }
    return Math.round(value / this.options.gridSize) * this.options.gridSize;
  }

  /**
   * Handle drag start
   */
  private handleDragStart(
    event: d3.D3DragEvent<SVGGraphicsElement, any, any>,
    node: any,
    context: ExtensionContext
  ): void {
    // Prevent event propagation
    event.sourceEvent.stopPropagation();

    // Determine which nodes to drag
    this.draggedNodes.clear();
    this.initialPositions.clear();

    if (this.options.multiDrag && context.selectedNodes.has(node)) {
      // Drag all selected nodes
      context.selectedNodes.forEach((n) => {
        this.draggedNodes.add(n);
        this.initialPositions.set(n, { x: n.x, y: n.y });
      });
    } else {
      // Drag single node
      this.draggedNodes.add(node);
      this.initialPositions.set(node, { x: node.x, y: node.y });
    }

    // Heat up simulation if active
    if (context.simulation) {
      context.simulation.alphaTarget(this.options.alphaTarget).restart();
    }

    // Callback
    this.options.onDragStart(node, event);

    logger.debug('Drag started:', {
      node: node.id,
      draggedCount: this.draggedNodes.size,
    });
  }

  /**
   * Handle drag
   */
  private handleDrag(
    event: d3.D3DragEvent<SVGGraphicsElement, any, any>,
    node: any,
    context: ExtensionContext
  ): void {
    const initialPos = this.initialPositions.get(node);
    if (!initialPos) return;

    // Calculate delta from initial position
    const dx = event.x - initialPos.x;
    const dy = event.y - initialPos.y;

    // Apply drag to all dragged nodes
    this.draggedNodes.forEach((n) => {
      const initial = this.initialPositions.get(n);
      if (!initial) return;

      let newX = initial.x + dx;
      let newY = initial.y + dy;

      // Apply constraints
      if (this.options.lockX) {
        newX = initial.x;
      }
      if (this.options.lockY) {
        newY = initial.y;
      }

      // Apply grid snapping
      newX = this.snapToGrid(newX);
      newY = this.snapToGrid(newY);

      // Update node position
      n.fx = newX;
      n.fy = newY;
      n.x = newX;
      n.y = newY;
    });

    // Update visuals
    this.updateNodePositions(context);

    // Callback
    this.options.onDrag(node, event);
  }

  /**
   * Handle drag end
   */
  private handleDragEnd(
    event: d3.D3DragEvent<SVGGraphicsElement, any, any>,
    node: any,
    context: ExtensionContext
  ): void {
    // Cool down simulation if active
    if (context.simulation) {
      context.simulation.alphaTarget(0);
    }

    // Release fixed positions unless nodes were already pinned
    this.draggedNodes.forEach((n) => {
      // Only release if the node wasn't pinned before dragging
      const initialPos = this.initialPositions.get(n);
      if (initialPos && n.fx === undefined && n.fy === undefined) {
        // Node wasn't pinned, so release it
        n.fx = null;
        n.fy = null;
      }
      // If node has fx/fy, keep it pinned at new position
    });

    // Callback
    this.options.onDragEnd(node, event);

    // Notify graph change
    if (context.onGraphChange) {
      context.onGraphChange();
    }

    logger.debug('Drag ended:', {
      node: node.id,
      draggedCount: this.draggedNodes.size,
    });

    // Clear dragged nodes
    this.draggedNodes.clear();
    this.initialPositions.clear();
  }

  /**
   * Update visual positions of nodes and connected edges
   */
  private updateNodePositions(context: ExtensionContext): void {
    const nodeElement = context.nodes.node();
    const useTransform = !!nodeElement && nodeElement.tagName.toLowerCase() !== 'circle';

    // Update node positions
    if (useTransform) {
      context.nodes.attr('transform', (d: any) => `translate(${d.x}, ${d.y})`);
    } else {
      context.nodes.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);
    }

    // Update label positions
    context.labels.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y);

    // Update edge positions
    context.edges
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y);
  }
}
