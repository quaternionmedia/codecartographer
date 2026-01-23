/**
 * Tooltip Extension
 *
 * Provides rich tooltip functionality including:
 * - Smart positioning (avoid overflow)
 * - Customizable content
 * - Follow cursor or anchor to node
 * - Delay and fade animations
 */

import * as d3 from 'd3';
import { BaseExtension, ExtensionContext } from './base';
import { logger } from '../../../core/logger';

export interface TooltipOptions {
  /** Enable tooltips */
  enabled?: boolean;

  /** Tooltip delay before showing (ms) */
  showDelay?: number;

  /** Tooltip delay before hiding (ms) */
  hideDelay?: number;

  /** Follow cursor or anchor to node */
  followCursor?: boolean;

  /** Offset from cursor/node (px) */
  offset?: { x: number; y: number };

  /** Maximum tooltip width (px) */
  maxWidth?: number;

  /** Content formatter function */
  formatter?: (node: any) => string | HTMLElement;

  /** Show node metadata */
  showMetadata?: boolean;
}

export class TooltipExtension extends BaseExtension {
  private options: Required<TooltipOptions>;
  private tooltipElement: HTMLDivElement | null = null;
  private showTimeout: number | null = null;
  private hideTimeout: number | null = null;
  private currentNode: any = null;

  constructor(options: TooltipOptions = {}) {
    super('tooltip', 'Rich Tooltips', 'Configurable tooltips with smart positioning');

    this.options = {
      enabled: options.enabled ?? true,
      showDelay: options.showDelay ?? 300,
      hideDelay: options.hideDelay ?? 100,
      followCursor: options.followCursor ?? false,
      offset: options.offset ?? { x: 12, y: 12 },
      maxWidth: options.maxWidth ?? 300,
      formatter: options.formatter ?? this.defaultFormatter.bind(this),
      showMetadata: options.showMetadata ?? true,
    };
  }

  public apply(): void {
    const context = this.assertContext();

    if (!this.enabled) {
      return;
    }

    // Create tooltip element
    this.createTooltipElement(context);

    // Setup listeners
    this.setupTooltipListeners(context);

    logger.debug('TooltipExtension applied');
  }

  public destroy(): void {
    if (this.context) {
      this.context.nodes.on('mouseenter.tooltip', null);
      this.context.nodes.on('mouseleave.tooltip', null);
      this.context.nodes.on('mousemove.tooltip', null);
    }

    if (this.tooltipElement) {
      this.tooltipElement.remove();
      this.tooltipElement = null;
    }

    this.clearTimeouts();
    super.destroy();
  }

  /**
   * Create tooltip DOM element
   */
  private createTooltipElement(context: ExtensionContext): void {
    this.tooltipElement = document.createElement('div');
    this.tooltipElement.className = 'graph-tooltip';
    this.tooltipElement.style.cssText = `
      position: absolute;
      padding: 12px 16px;
      background: var(--c-primary-light, #1a1a1a);
      border: 1px solid var(--c-secondary, #00ff41);
      color: var(--c-font, #00ff41);
      font-family: var(--f-root-font, monospace);
      font-size: 12px;
      border-radius: 4px;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s ease;
      z-index: 10000;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
      max-width: ${this.options.maxWidth}px;
      word-wrap: break-word;
    `;

    context.container.appendChild(this.tooltipElement);
  }

  /**
   * Setup tooltip event listeners
   */
  private setupTooltipListeners(context: ExtensionContext): void {
    context.nodes
      .on('mouseenter.tooltip', (event: MouseEvent, d: any) => {
        this.scheduleShow(d, event, context);
      })
      .on('mouseleave.tooltip', () => {
        this.scheduleHide();
      })
      .on('mousemove.tooltip', (event: MouseEvent, d: any) => {
        if (this.options.followCursor) {
          this.updatePosition(event, context);
        }
      });
  }

  /**
   * Schedule tooltip show
   */
  private scheduleShow(node: any, event: MouseEvent, context: ExtensionContext): void {
    this.clearTimeouts();

    this.showTimeout = window.setTimeout(() => {
      this.show(node, event, context);
    }, this.options.showDelay);
  }

  /**
   * Schedule tooltip hide
   */
  private scheduleHide(): void {
    this.clearTimeouts();

    this.hideTimeout = window.setTimeout(() => {
      this.hide();
    }, this.options.hideDelay);
  }

  /**
   * Show tooltip
   */
  private show(node: any, event: MouseEvent, context: ExtensionContext): void {
    if (!this.tooltipElement) return;

    this.currentNode = node;

    // Update content
    const content = this.options.formatter(node);
    if (typeof content === 'string') {
      this.tooltipElement.innerHTML = content;
    } else {
      this.tooltipElement.innerHTML = '';
      this.tooltipElement.appendChild(content);
    }

    // Update position
    this.updatePosition(event, context);

    // Show with animation
    this.tooltipElement.style.opacity = '1';

    logger.debug('Tooltip shown for node:', node.id);
  }

  /**
   * Hide tooltip
   */
  private hide(): void {
    if (!this.tooltipElement) return;

    this.tooltipElement.style.opacity = '0';
    this.currentNode = null;

    logger.debug('Tooltip hidden');
  }

  /**
   * Update tooltip position
   */
  private updatePosition(event: MouseEvent, context: ExtensionContext): void {
    if (!this.tooltipElement || !this.currentNode) return;

    const containerRect = context.container.getBoundingClientRect();
    const tooltipRect = this.tooltipElement.getBoundingClientRect();

    let x: number;
    let y: number;

    if (this.options.followCursor) {
      // Position relative to cursor
      x = event.clientX - containerRect.left + this.options.offset.x;
      y = event.clientY - containerRect.top + this.options.offset.y;
    } else {
      // Position relative to node
      x = this.currentNode.x + this.options.offset.x;
      y = this.currentNode.y + this.options.offset.y;
    }

    // Prevent overflow
    const maxX = containerRect.width - tooltipRect.width - 8;
    const maxY = containerRect.height - tooltipRect.height - 8;

    x = Math.max(8, Math.min(x, maxX));
    y = Math.max(8, Math.min(y, maxY));

    this.tooltipElement.style.left = `${x}px`;
    this.tooltipElement.style.top = `${y}px`;
  }

  /**
   * Clear all timeouts
   */
  private clearTimeouts(): void {
    if (this.showTimeout) {
      clearTimeout(this.showTimeout);
      this.showTimeout = null;
    }
    if (this.hideTimeout) {
      clearTimeout(this.hideTimeout);
      this.hideTimeout = null;
    }
  }

  /**
   * Default tooltip formatter
   */
  private defaultFormatter(node: any): string {
    const parts: string[] = [];

    // Node label/ID
    parts.push(`<div style="font-weight: bold; font-size: 14px; margin-bottom: 8px;">`);
    parts.push(this.escapeHtml(node.label || node.id || 'Node'));
    parts.push(`</div>`);

    if (this.options.showMetadata) {
      // Node metadata
      const metadata: Array<{ key: string; value: any }> = [];

      if (node.id && node.id !== node.label) {
        metadata.push({ key: 'ID', value: node.id });
      }

      if (node.type) {
        metadata.push({ key: 'Type', value: node.type });
      }

      if (node.size !== undefined) {
        metadata.push({ key: 'Size', value: node.size });
      }

      if (node.color) {
        metadata.push({ key: 'Color', value: node.color });
      }

      // Custom metadata
      Object.keys(node).forEach((key) => {
        if (
          !['id', 'label', 'x', 'y', 'fx', 'fy', 'vx', 'vy', 'index', 'type', 'size', 'color'].includes(
            key
          )
        ) {
          const value = node[key];
          if (value !== null && value !== undefined && typeof value !== 'object') {
            metadata.push({ key, value });
          }
        }
      });

      // Render metadata
      if (metadata.length > 0) {
        parts.push(`<div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--c-border);">`);
        metadata.forEach(({ key, value }) => {
          parts.push(
            `<div style="display: flex; justify-content: space-between; margin-bottom: 4px;">` +
              `<span style="color: var(--c-font-muted); margin-right: 12px;">${this.escapeHtml(
                key
              )}:</span>` +
              `<span>${this.escapeHtml(String(value))}</span>` +
              `</div>`
          );
        });
        parts.push(`</div>`);
      }
    }

    return parts.join('');
  }

  /**
   * Escape HTML to prevent XSS
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Update tooltip options
   */
  public updateOptions(options: Partial<TooltipOptions>): void {
    this.options = { ...this.options, ...options };

    if (this.tooltipElement && options.maxWidth !== undefined) {
      this.tooltipElement.style.maxWidth = `${this.options.maxWidth}px`;
    }
  }

  /**
   * Manually show tooltip for a node
   */
  public showForNode(node: any, context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    // Create synthetic event at node position
    const syntheticEvent = {
      clientX: node.x,
      clientY: node.y,
    } as MouseEvent;

    this.show(node, syntheticEvent, ctx);
  }

  /**
   * Manually hide tooltip
   */
  public hideTooltip(): void {
    this.hide();
  }
}
