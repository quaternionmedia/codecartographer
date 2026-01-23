import m from 'mithril';
import { GraphStylingOptions } from '../../../state/types';

/**
 * Base interface for all graph renderers
 * Each renderer implementation must follow this contract
 */
export interface IGraphRenderer {
  /**
   * Unique identifier for this renderer type
   */
  readonly type: string;

  /**
   * Human-readable name for this renderer
   */
  readonly name: string;

  /**
   * Render the graph data into the provided container element
   *
   * @param container - HTML element to render into
   * @param data - Graph data (format varies by renderer)
   * @param styling - Optional styling options
   */
  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void;

  /**
   * Check if this renderer can handle the given data format
   *
   * @param data - Data to check
   * @returns true if this renderer can handle the data
   */
  canHandle(data: unknown): boolean;

  /**
   * Clean up any resources when the renderer is destroyed
   */
  cleanup?(): void;
}

/**
 * Factory function type for creating renderer instances
 */
export type RendererFactory = () => IGraphRenderer;

/**
 * Registry of available graph renderers
 */
export class GraphRendererRegistry {
  private static renderers: Map<string, RendererFactory> = new Map();
  private static defaultRenderer: string | null = null;

  /**
   * Register a new renderer type
   */
  static register(type: string, factory: RendererFactory): void {
    this.renderers.set(type, factory);

    // First registered renderer becomes default
    if (!this.defaultRenderer) {
      this.defaultRenderer = type;
    }
  }

  /**
   * Set the default renderer type
   */
  static setDefault(type: string): void {
    if (!this.renderers.has(type)) {
      throw new Error(`Renderer type '${type}' is not registered`);
    }
    this.defaultRenderer = type;
  }

  /**
   * Get a renderer instance by type
   */
  static get(type: string): IGraphRenderer {
    const factory = this.renderers.get(type);
    if (!factory) {
      throw new Error(`Renderer type '${type}' is not registered`);
    }
    return factory();
  }

  /**
   * Get the default renderer
   */
  static getDefault(): IGraphRenderer {
    if (!this.defaultRenderer) {
      throw new Error('No default renderer set');
    }
    return this.get(this.defaultRenderer);
  }

  /**
   * Find a renderer that can handle the given data
   */
  static findForData(data: unknown): IGraphRenderer | null {
    for (const [type, factory] of this.renderers) {
      const renderer = factory();
      if (renderer.canHandle(data)) {
        return renderer;
      }
    }
    return null;
  }

  /**
   * Get all registered renderer types
   */
  static getTypes(): string[] {
    return Array.from(this.renderers.keys());
  }
}
