/**
 * D3 Extensions System
 *
 * Provides a plugin-based architecture for adding interactive functionality
 * to D3 graph visualizations in a modular, composable way.
 */

// Export base classes and interfaces
export { type GraphExtension, type ExtensionContext, BaseExtension } from './base';

/**
 * Extension registry for managing graph extensions
 */
export class ExtensionRegistry {
  private extensions: Map<string, GraphExtension> = new Map();
  private context: ExtensionContext | null = null;

  /**
   * Register a new extension
   */
  public register(extension: GraphExtension): void {
    if (this.extensions.has(extension.id)) {
      console.warn(`Extension ${extension.id} is already registered. Replacing.`);
    }

    this.extensions.set(extension.id, extension);

    // Initialize if context is available
    if (this.context) {
      extension.initialize(this.context);
    }
  }

  /**
   * Unregister an extension
   */
  public unregister(extensionId: string): void {
    const extension = this.extensions.get(extensionId);
    if (extension) {
      extension.destroy();
      this.extensions.delete(extensionId);
    }
  }

  /**
   * Get extension by ID
   */
  public get(extensionId: string): GraphExtension | undefined {
    return this.extensions.get(extensionId);
  }

  /**
   * Get all registered extensions
   */
  public getAll(): GraphExtension[] {
    return Array.from(this.extensions.values());
  }

  /**
   * Get all enabled extensions
   */
  public getEnabled(): GraphExtension[] {
    return this.getAll().filter((ext) => ext.isEnabled());
  }

  /**
   * Set context for all extensions
   */
  public setContext(context: ExtensionContext): void {
    this.context = context;

    // Initialize all extensions with new context
    this.extensions.forEach((extension) => {
      extension.initialize(context);
    });
  }

  /**
   * Apply all enabled extensions
   */
  public applyAll(): void {
    this.getEnabled().forEach((extension) => {
      try {
        extension.apply();
      } catch (error) {
        console.error(`Error applying extension ${extension.id}:`, error);
      }
    });
  }

  /**
   * Destroy all extensions
   */
  public destroyAll(): void {
    this.extensions.forEach((extension) => {
      try {
        extension.destroy();
      } catch (error) {
        console.error(`Error destroying extension ${extension.id}:`, error);
      }
    });
    this.extensions.clear();
  }

  /**
   * Enable extension by ID
   */
  public enable(extensionId: string): void {
    const extension = this.extensions.get(extensionId);
    if (extension) {
      extension.enable();
      extension.apply();
    }
  }

  /**
   * Disable extension by ID
   */
  public disable(extensionId: string): void {
    const extension = this.extensions.get(extensionId);
    if (extension) {
      extension.disable();
    }
  }
}

// Create global registry instance
export const graphExtensions = new ExtensionRegistry();

// Export layer 1 extensions
export { DragExtension } from './drag_extension';
export { SelectionExtension } from './selection_extension';
export { ZoomExtension } from './zoom_extension';
export { HighlightExtension } from './highlight_extension';
export { TooltipExtension } from './tooltip_extension';
export { ColorExtension } from './color_extension';
