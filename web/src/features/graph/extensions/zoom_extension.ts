/**
 * Zoom Extension
 *
 * Provides advanced zoom capabilities including:
 * - Zoom to selection
 * - Zoom to fit
 * - Zoom to specific scale
 * - Animated zoom transitions
 * - Zoom level indicators
 */

import * as d3 from 'd3';
import { BaseExtension, ExtensionContext } from './base';
import { logger } from '../../../core/logger';

export interface ZoomOptions {
  /** Minimum zoom level */
  minZoom?: number;

  /** Maximum zoom level */
  maxZoom?: number;

  /** Default transition duration (ms) */
  transitionDuration?: number;

  /** Padding around content when fitting (0-1) */
  fitPadding?: number;

  /** Enable zoom level indicator */
  showZoomLevel?: boolean;

  /** Callbacks */
  onZoomChange?: (scale: number) => void;
}

export class ZoomExtension extends BaseExtension {
  private options: Required<ZoomOptions>;
  private zoomLevelIndicator: HTMLDivElement | null = null;
  private zoomLevelTimeout: number | null = null;

  constructor(options: ZoomOptions = {}) {
    super('zoom', 'Advanced Zoom', 'Zoom utilities including zoom-to-fit and zoom-to-selection');

    this.options = {
      minZoom: options.minZoom ?? 0.1,
      maxZoom: options.maxZoom ?? 10,
      transitionDuration: options.transitionDuration ?? 750,
      fitPadding: options.fitPadding ?? 0.1,
      showZoomLevel: options.showZoomLevel ?? true,
      onZoomChange: options.onZoomChange ?? (() => {}),
    };
  }

  public apply(): void {
    const context = this.assertContext();

    if (!this.enabled) {
      return;
    }

    // Update zoom extent
    if (context.zoom) {
      context.zoom.scaleExtent([this.options.minZoom, this.options.maxZoom]);

      // Add zoom level indicator
      if (this.options.showZoomLevel) {
        this.createZoomLevelIndicator(context);
        this.attachZoomListener(context);
      }
    }

    logger.debug('ZoomExtension applied');
  }

  public destroy(): void {
    if (this.zoomLevelIndicator) {
      this.zoomLevelIndicator.remove();
      this.zoomLevelIndicator = null;
    }

    if (this.context?.zoom) {
      this.context.zoom.on('zoom.extension', null);
    }

    super.destroy();
  }

  /**
   * Create zoom level indicator UI
   */
  private createZoomLevelIndicator(context: ExtensionContext): void {
    this.zoomLevelIndicator = document.createElement('div');
    this.zoomLevelIndicator.className = 'zoom-level-indicator';
    this.zoomLevelIndicator.style.cssText = `
      position: absolute;
      top: 16px;
      right: 16px;
      padding: 8px 12px;
      background: var(--c-primary-light, #1a1a1a);
      border: 1px solid var(--c-secondary, #00ff41);
      color: var(--c-font, #00ff41);
      font-family: var(--f-root-font, monospace);
      font-size: 12px;
      border-radius: 4px;
      opacity: 0;
      transition: opacity 0.2s ease;
      pointer-events: none;
      z-index: 1000;
    `;

    context.container.appendChild(this.zoomLevelIndicator);
  }

  /**
   * Attach zoom event listener
   */
  private attachZoomListener(context: ExtensionContext): void {
    if (!context.zoom) return;

    context.zoom.on('zoom.extension', (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
      const scale = event.transform.k;
      this.showZoomLevel(scale);
      this.options.onZoomChange(scale);
    });
  }

  /**
   * Show zoom level indicator
   */
  private showZoomLevel(scale: number): void {
    if (!this.zoomLevelIndicator) return;

    const percentage = Math.round(scale * 100);
    this.zoomLevelIndicator.textContent = `${percentage}%`;
    this.zoomLevelIndicator.style.opacity = '1';

    // Hide after delay
    if (this.zoomLevelTimeout) {
      clearTimeout(this.zoomLevelTimeout);
    }

    this.zoomLevelTimeout = window.setTimeout(() => {
      if (this.zoomLevelIndicator) {
        this.zoomLevelIndicator.style.opacity = '0';
      }
    }, 1500);
  }

  /**
   * Zoom to fit all nodes
   */
  public zoomToFit(context: ExtensionContext, animated: boolean = true): void {
    if (!context.zoom || context.data.nodes.length === 0) {
      logger.warn('Cannot zoom to fit: no zoom behavior or no nodes');
      return;
    }

    const bounds = this.calculateBounds(context.data.nodes);
    this.zoomToBounds(context, bounds, animated);

    logger.debug('Zoomed to fit all nodes');
  }

  /**
   * Zoom to selected nodes
   */
  public zoomToSelection(context: ExtensionContext, animated: boolean = true): void {
    if (!context.zoom || context.selectedNodes.size === 0) {
      logger.warn('Cannot zoom to selection: no zoom behavior or no selected nodes');
      return;
    }

    const selectedArray = Array.from(context.selectedNodes);
    const bounds = this.calculateBounds(selectedArray);
    this.zoomToBounds(context, bounds, animated);

    logger.debug('Zoomed to selection:', context.selectedNodes.size, 'nodes');
  }

  /**
   * Zoom to specific node
   */
  public zoomToNode(context: ExtensionContext, node: any, scale: number = 2, animated: boolean = true): void {
    if (!context.zoom) {
      logger.warn('Cannot zoom to node: no zoom behavior');
      return;
    }

    const svgWidth = parseFloat(context.svg.attr('width'));
    const svgHeight = parseFloat(context.svg.attr('height'));

    const transform = d3.zoomIdentity
      .translate(svgWidth / 2, svgHeight / 2)
      .scale(scale)
      .translate(-node.x, -node.y);

    this.applyTransform(context, transform, animated);

    logger.debug('Zoomed to node:', node.id, 'at scale:', scale);
  }

  /**
   * Zoom to specific scale
   */
  public zoomToScale(context: ExtensionContext, scale: number, animated: boolean = true): void {
    if (!context.zoom) {
      logger.warn('Cannot zoom to scale: no zoom behavior');
      return;
    }

    const currentTransform = d3.zoomTransform(context.svg.node()!);
    const transform = currentTransform.scale(scale / currentTransform.k);

    this.applyTransform(context, transform, animated);

    logger.debug('Zoomed to scale:', scale);
  }

  /**
   * Zoom in by factor
   */
  public zoomIn(context: ExtensionContext, factor: number = 1.3, animated: boolean = true): void {
    if (!context.zoom) return;

    if (animated) {
      context.svg.transition().duration(200).call(context.zoom.scaleBy as any, factor);
    } else {
      context.zoom.scaleBy(context.svg, factor);
    }

    logger.debug('Zoomed in by factor:', factor);
  }

  /**
   * Zoom out by factor
   */
  public zoomOut(context: ExtensionContext, factor: number = 0.7, animated: boolean = true): void {
    if (!context.zoom) return;

    if (animated) {
      context.svg.transition().duration(200).call(context.zoom.scaleBy as any, factor);
    } else {
      context.zoom.scaleBy(context.svg, factor);
    }

    logger.debug('Zoomed out by factor:', factor);
  }

  /**
   * Reset zoom to 1:1
   */
  public resetZoom(context: ExtensionContext, animated: boolean = true): void {
    if (!context.zoom) return;

    const svgWidth = parseFloat(context.svg.attr('width'));
    const svgHeight = parseFloat(context.svg.attr('height'));

    const transform = d3.zoomIdentity.translate(svgWidth / 2, svgHeight / 2).scale(1).translate(0, 0);

    this.applyTransform(context, transform, animated);

    logger.debug('Reset zoom');
  }

  /**
   * Calculate bounding box for nodes
   */
  private calculateBounds(nodes: any[]): { minX: number; maxX: number; minY: number; maxY: number } {
    const xs = nodes.map((n) => n.x || 0);
    const ys = nodes.map((n) => n.y || 0);

    return {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    };
  }

  /**
   * Zoom to specific bounds
   */
  private zoomToBounds(
    context: ExtensionContext,
    bounds: { minX: number; maxX: number; minY: number; maxY: number },
    animated: boolean
  ): void {
    const width = bounds.maxX - bounds.minX;
    const height = bounds.maxY - bounds.minY;
    const midX = (bounds.minX + bounds.maxX) / 2;
    const midY = (bounds.minY + bounds.maxY) / 2;

    const svgWidth = parseFloat(context.svg.attr('width'));
    const svgHeight = parseFloat(context.svg.attr('height'));

    // Calculate scale to fit
    const padding = this.options.fitPadding;
    const scale = (1 - padding) * Math.min(svgWidth / width, svgHeight / height);

    // Clamp scale to zoom limits
    const clampedScale = Math.max(this.options.minZoom, Math.min(this.options.maxZoom, scale));

    // Calculate translation
    const translate: [number, number] = [
      svgWidth / 2 - clampedScale * midX,
      svgHeight / 2 - clampedScale * midY,
    ];

    const transform = d3.zoomIdentity.translate(translate[0], translate[1]).scale(clampedScale);

    this.applyTransform(context, transform, animated);
  }

  /**
   * Apply zoom transform
   */
  private applyTransform(
    context: ExtensionContext,
    transform: d3.ZoomTransform,
    animated: boolean
  ): void {
    if (!context.zoom) return;

    if (animated) {
      context.svg
        .transition()
        .duration(this.options.transitionDuration)
        .call(context.zoom.transform as any, transform);
    } else {
      context.svg.call(context.zoom.transform as any, transform);
    }
  }

  /**
   * Get current zoom level
   */
  public getCurrentZoom(context: ExtensionContext): number {
    const transform = d3.zoomTransform(context.svg.node()!);
    return transform.k;
  }
}
