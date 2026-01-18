/**
 * Highlight Extension
 *
 * Provides visual highlighting capabilities including:
 * - Hover highlighting
 * - Neighbor highlighting
 * - Path highlighting
 * - Fade non-highlighted elements
 */

import * as d3 from 'd3';
import { BaseExtension, ExtensionContext } from './base';
import { logger } from '../../../core/logger';

export interface HighlightOptions {
  /** Enable hover highlighting */
  enableHover?: boolean;

  /** Highlight neighbors on hover */
  highlightNeighbors?: boolean;

  /** Fade opacity for non-highlighted elements */
  fadeOpacity?: number;

  /** Highlight color */
  highlightColor?: string;

  /** Highlight stroke width */
  highlightWidth?: number;

  /** Neighbor highlight color */
  neighborColor?: string;

  /** Edge highlight color */
  edgeColor?: string;

  /** Transition duration (ms) */
  transitionDuration?: number;

  /** Callbacks */
  onHighlight?: (node: any) => void;
  onUnhighlight?: () => void;
}

export class HighlightExtension extends BaseExtension {
  private options: Required<HighlightOptions>;
  private highlightedNode: any = null;
  private highlightedNeighbors: Set<any> = new Set();
  private highlightedEdges: Set<any> = new Set();

  constructor(options: HighlightOptions = {}) {
    super('highlight', 'Highlight System', 'Visual highlighting for nodes, neighbors, and paths');

    // Get theme color
    const rootStyles = getComputedStyle(document.documentElement);
    const secondaryColor = rootStyles.getPropertyValue('--c-secondary').trim() || '#00ff41';
    const accentColor = rootStyles.getPropertyValue('--c-accent').trim() || '#00d4ff';

    this.options = {
      enableHover: options.enableHover ?? true,
      highlightNeighbors: options.highlightNeighbors ?? true,
      fadeOpacity: options.fadeOpacity ?? 0.15,
      highlightColor: options.highlightColor ?? secondaryColor,
      highlightWidth: options.highlightWidth ?? 4,
      neighborColor: options.neighborColor ?? accentColor,
      edgeColor: options.edgeColor ?? secondaryColor,
      transitionDuration: options.transitionDuration ?? 200,
      onHighlight: options.onHighlight ?? (() => {}),
      onUnhighlight: options.onUnhighlight ?? (() => {}),
    };
  }

  public apply(): void {
    const context = this.assertContext();

    if (!this.enabled) {
      return;
    }

    if (this.options.enableHover) {
      this.setupHoverListeners(context);
    }

    logger.debug('HighlightExtension applied');
  }

  public destroy(): void {
    if (this.context) {
      this.context.nodes.on('mouseenter.highlight', null);
      this.context.nodes.on('mouseleave.highlight', null);
      this.context.svg.on('mouseleave.highlight', null);
    }

    this.clearHighlight();
    super.destroy();
  }

  /**
   * Setup hover event listeners
   */
  private setupHoverListeners(context: ExtensionContext): void {
    // Node hover
    context.nodes
      .on('mouseenter.highlight', (event: MouseEvent, d: any) => {
        this.highlightNode(d, context);
      })
      .on('mouseleave.highlight', () => {
        // Don't clear immediately - wait for canvas leave
      });

    // Canvas leave
    context.svg.on('mouseleave.highlight', () => {
      this.clearHighlight();
      this.updateVisuals(context);
    });
  }

  /**
   * Highlight a specific node and optionally its neighbors
   */
  public highlightNode(node: any, context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    this.highlightedNode = node;
    this.highlightedNeighbors.clear();
    this.highlightedEdges.clear();

    if (this.options.highlightNeighbors) {
      // Find neighbors
      ctx.data.edges.forEach((edge: any) => {
        const sourceId = edge.source.id || edge.source;
        const targetId = edge.target.id || edge.target;
        const nodeId = node.id || node;

        if (sourceId === nodeId) {
          this.highlightedNeighbors.add(edge.target);
          this.highlightedEdges.add(edge);
        } else if (targetId === nodeId) {
          this.highlightedNeighbors.add(edge.source);
          this.highlightedEdges.add(edge);
        }
      });
    }

    this.updateVisuals(ctx);
    this.options.onHighlight(node);

    logger.debug('Highlighted node:', node.id, 'neighbors:', this.highlightedNeighbors.size);
  }

  /**
   * Highlight path between two nodes
   */
  public highlightPath(startNode: any, endNode: any, context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    // Find path using BFS
    const path = this.findPath(startNode, endNode, ctx);

    if (path.length === 0) {
      logger.warn('No path found between nodes');
      return;
    }

    this.highlightedNode = null;
    this.highlightedNeighbors.clear();
    this.highlightedEdges.clear();

    // Highlight all nodes in path
    path.forEach((node) => this.highlightedNeighbors.add(node));

    // Highlight edges in path
    for (let i = 0; i < path.length - 1; i++) {
      const source = path[i];
      const target = path[i + 1];

      ctx.data.edges.forEach((edge: any) => {
        const sourceId = edge.source.id || edge.source;
        const targetId = edge.target.id || edge.target;
        const srcId = source.id || source;
        const tgtId = target.id || target;

        if (
          (sourceId === srcId && targetId === tgtId) ||
          (sourceId === tgtId && targetId === srcId)
        ) {
          this.highlightedEdges.add(edge);
        }
      });
    }

    this.updateVisuals(ctx);

    logger.debug('Highlighted path:', path.length, 'nodes');
  }

  /**
   * Clear all highlights
   */
  public clearHighlight(): void {
    this.highlightedNode = null;
    this.highlightedNeighbors.clear();
    this.highlightedEdges.clear();
    this.options.onUnhighlight();
  }

  /**
   * Update visual representation
   */
  private updateVisuals(context: ExtensionContext): void {
    const hasHighlight = this.highlightedNode !== null || this.highlightedNeighbors.size > 0;

    // Update nodes
    context.nodes
      .transition()
      .duration(this.options.transitionDuration)
      .attr('opacity', (d: any) => {
        if (!hasHighlight) return 1;

        if (d === this.highlightedNode) return 1;
        if (this.highlightedNeighbors.has(d)) return 1;
        return this.options.fadeOpacity;
      })
      .attr('stroke', (d: any) => {
        if (d === this.highlightedNode) return this.options.highlightColor;
        if (this.highlightedNeighbors.has(d)) return this.options.neighborColor;
        // Keep existing stroke for selected nodes
        const isSelected = context.selectedNodes.has(d);
        return isSelected ? this.options.highlightColor : '#fff';
      })
      .attr('stroke-width', (d: any) => {
        if (d === this.highlightedNode) return this.options.highlightWidth;
        if (this.highlightedNeighbors.has(d)) return this.options.highlightWidth - 1;
        // Keep existing width for selected nodes
        const isSelected = context.selectedNodes.has(d);
        return isSelected ? 3 : 1;
      });

    // Update edges
    context.edges
      .transition()
      .duration(this.options.transitionDuration)
      .attr('opacity', (d: any) => {
        if (!hasHighlight) return 0.6;
        if (this.highlightedEdges.has(d)) return 1;
        return this.options.fadeOpacity;
      })
      .attr('stroke', (d: any) => {
        if (this.highlightedEdges.has(d)) return this.options.edgeColor;
        return d.color || '#999';
      })
      .attr('stroke-width', (d: any) => {
        if (this.highlightedEdges.has(d)) return 2;
        return 1;
      });

    // Update labels
    context.labels
      .transition()
      .duration(this.options.transitionDuration)
      .attr('opacity', (d: any) => {
        if (!hasHighlight) return 1;
        if (d === this.highlightedNode) return 1;
        if (this.highlightedNeighbors.has(d)) return 1;
        return this.options.fadeOpacity * 2; // Labels slightly more visible
      });
  }

  /**
   * Find shortest path between two nodes using BFS
   */
  private findPath(startNode: any, endNode: any, context: ExtensionContext): any[] {
    const queue: Array<{ node: any; path: any[] }> = [{ node: startNode, path: [startNode] }];
    const visited = new Set<any>();

    while (queue.length > 0) {
      const { node, path } = queue.shift()!;

      if (node === endNode) {
        return path;
      }

      if (visited.has(node)) {
        continue;
      }

      visited.add(node);

      // Find neighbors
      context.data.edges.forEach((edge: any) => {
        const sourceId = edge.source.id || edge.source;
        const targetId = edge.target.id || edge.target;
        const nodeId = node.id || node;

        let neighbor = null;

        if (sourceId === nodeId) {
          neighbor = edge.target;
        } else if (targetId === nodeId) {
          neighbor = edge.source;
        }

        if (neighbor && !visited.has(neighbor)) {
          queue.push({ node: neighbor, path: [...path, neighbor] });
        }
      });
    }

    return []; // No path found
  }

  /**
   * Pulse effect on highlighted elements
   */
  public pulse(context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    if (this.highlightedNode) {
      ctx.nodes
        .filter((d: any) => d === this.highlightedNode)
        .transition()
        .duration(300)
        .attr('r', function (d: any) {
          const currentR = parseFloat(d3.select(this).attr('r'));
          return currentR * 1.5;
        })
        .transition()
        .duration(300)
        .attr('r', function (d: any) {
          return Math.sqrt((d.size || 400) / Math.PI);
        });
    }
  }
}
