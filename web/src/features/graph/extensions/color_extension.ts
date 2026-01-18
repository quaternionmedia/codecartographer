/**
 * Color Extension
 *
 * Provides color utilities and schemes including:
 * - Color schemes (categorical, sequential, diverging)
 * - Automatic coloring by property
 * - Gradient generation
 * - Color interpolation
 * - Theme-aware palettes
 */

import * as d3 from 'd3';
import { BaseExtension, ExtensionContext } from './base';
import { logger } from '../../../core/logger';

export type ColorScheme =
  | 'category10'
  | 'category20'
  | 'tableau10'
  | 'accent'
  | 'dark2'
  | 'paired'
  | 'pastel1'
  | 'pastel2'
  | 'set1'
  | 'set2'
  | 'set3'
  | 'viridis'
  | 'inferno'
  | 'magma'
  | 'plasma'
  | 'warm'
  | 'cool'
  | 'rainbow'
  | 'sinebow'
  | 'custom';

export interface ColorOptions {
  /** Default color scheme */
  scheme?: ColorScheme;

  /** Custom color array (for 'custom' scheme) */
  customColors?: string[];

  /** Property to color by (e.g., 'type', 'cluster') */
  colorBy?: string;

  /** Min value for sequential/diverging scales */
  minValue?: number;

  /** Max value for sequential/diverging scales */
  maxValue?: number;

  /** Apply colors automatically on initialization */
  autoApply?: boolean;
}

export class ColorExtension extends BaseExtension {
  private options: Required<ColorOptions>;
  private colorScale: d3.ScaleOrdinal<string, string> | d3.ScaleSequential<string> | null = null;

  constructor(options: ColorOptions = {}) {
    super('color', 'Color Utilities', 'Color schemes, gradients, and automatic coloring');

    this.options = {
      scheme: options.scheme ?? 'category10',
      customColors: options.customColors ?? [],
      colorBy: options.colorBy ?? 'type',
      minValue: options.minValue ?? 0,
      maxValue: options.maxValue ?? 100,
      autoApply: options.autoApply ?? false,
    };
  }

  public apply(): void {
    const context = this.assertContext();

    if (!this.enabled) {
      return;
    }

    // Create color scale
    this.colorScale = this.createColorScale();

    // Auto-apply if enabled
    if (this.options.autoApply) {
      this.applyColorScheme(context);
    }

    logger.debug('ColorExtension applied with scheme:', this.options.scheme);
  }

  public destroy(): void {
    this.colorScale = null;
    super.destroy();
  }

  /**
   * Create color scale based on scheme
   */
  private createColorScale(): d3.ScaleOrdinal<string, string> | d3.ScaleSequential<string> {
    switch (this.options.scheme) {
      case 'category10':
        return d3.scaleOrdinal(d3.schemeCategory10);
      case 'category20':
        return d3.scaleOrdinal([
          ...d3.schemeCategory10,
          '#aec7e8',
          '#ffbb78',
          '#98df8a',
          '#ff9896',
          '#c5b0d5',
          '#c49c94',
          '#f7b6d2',
          '#c7c7c7',
          '#dbdb8d',
          '#9edae5',
        ]);
      case 'tableau10':
        return d3.scaleOrdinal(d3.schemeTableau10);
      case 'accent':
        return d3.scaleOrdinal(d3.schemeAccent);
      case 'dark2':
        return d3.scaleOrdinal(d3.schemeDark2);
      case 'paired':
        return d3.scaleOrdinal(d3.schemePaired);
      case 'pastel1':
        return d3.scaleOrdinal(d3.schemePastel1);
      case 'pastel2':
        return d3.scaleOrdinal(d3.schemePastel2);
      case 'set1':
        return d3.scaleOrdinal(d3.schemeSet1);
      case 'set2':
        return d3.scaleOrdinal(d3.schemeSet2);
      case 'set3':
        return d3.scaleOrdinal(d3.schemeSet3);
      case 'viridis':
        return d3.scaleSequential(d3.interpolateViridis).domain([this.options.minValue, this.options.maxValue]);
      case 'inferno':
        return d3.scaleSequential(d3.interpolateInferno).domain([this.options.minValue, this.options.maxValue]);
      case 'magma':
        return d3.scaleSequential(d3.interpolateMagma).domain([this.options.minValue, this.options.maxValue]);
      case 'plasma':
        return d3.scaleSequential(d3.interpolatePlasma).domain([this.options.minValue, this.options.maxValue]);
      case 'warm':
        return d3.scaleSequential(d3.interpolateWarm).domain([this.options.minValue, this.options.maxValue]);
      case 'cool':
        return d3.scaleSequential(d3.interpolateCool).domain([this.options.minValue, this.options.maxValue]);
      case 'rainbow':
        return d3.scaleSequential(d3.interpolateRainbow).domain([this.options.minValue, this.options.maxValue]);
      case 'sinebow':
        return d3.scaleSequential(d3.interpolateSinebow).domain([this.options.minValue, this.options.maxValue]);
      case 'custom':
        return d3.scaleOrdinal(this.options.customColors);
      default:
        return d3.scaleOrdinal(d3.schemeCategory10);
    }
  }

  /**
   * Apply color scheme to all nodes
   */
  public applyColorScheme(context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    if (!this.colorScale) {
      logger.warn('Color scale not initialized');
      return;
    }

    const property = this.options.colorBy;

    ctx.nodes
      .transition()
      .duration(300)
      .attr('fill', (d: any) => {
        const value = d[property];
        if (value === undefined) {
          return d.color || '#999';
        }
        return this.colorScale!(value);
      });

    // Update node data
    ctx.data.nodes.forEach((node: any) => {
      const value = node[property];
      if (value !== undefined) {
        node.color = this.colorScale!(value);
      }
    });

    logger.debug('Applied color scheme to', ctx.data.nodes.length, 'nodes by property:', property);
  }

  /**
   * Color nodes by a specific property
   */
  public colorByProperty(property: string, context?: ExtensionContext): void {
    this.options.colorBy = property;
    this.applyColorScheme(context);
  }

  /**
   * Set custom color scheme
   */
  public setColorScheme(scheme: ColorScheme, context?: ExtensionContext): void {
    this.options.scheme = scheme;
    this.colorScale = this.createColorScale();
    if (context) {
      this.applyColorScheme(context);
    }
  }

  /**
   * Set custom colors
   */
  public setCustomColors(colors: string[], context?: ExtensionContext): void {
    this.options.customColors = colors;
    this.options.scheme = 'custom';
    this.colorScale = this.createColorScale();
    if (context) {
      this.applyColorScheme(context);
    }
  }

  /**
   * Generate gradient between two colors
   */
  public generateGradient(startColor: string, endColor: string, steps: number): string[] {
    const interpolator = d3.interpolateRgb(startColor, endColor);
    const colors: string[] = [];

    for (let i = 0; i < steps; i++) {
      colors.push(interpolator(i / (steps - 1)));
    }

    return colors;
  }

  /**
   * Generate theme-aware color palette
   */
  public generateThemePalette(count: number): string[] {
    const rootStyles = getComputedStyle(document.documentElement);
    const secondary = rootStyles.getPropertyValue('--c-secondary').trim() || '#00ff41';
    const accent = rootStyles.getPropertyValue('--c-accent').trim() || '#00d4ff';

    const colors: string[] = [];

    for (let i = 0; i < count; i++) {
      const t = i / (count - 1);
      const interpolator = d3.interpolateRgb(secondary, accent);
      colors.push(interpolator(t));
    }

    return colors;
  }

  /**
   * Color nodes by degree (number of connections)
   */
  public colorByDegree(context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    // Calculate node degrees
    const degrees = new Map<any, number>();

    ctx.data.nodes.forEach((node: any) => {
      degrees.set(node, 0);
    });

    ctx.data.edges.forEach((edge: any) => {
      const source = edge.source.id ? edge.source : ctx.data.nodes.find((n: any) => n.id === edge.source);
      const target = edge.target.id ? edge.target : ctx.data.nodes.find((n: any) => n.id === edge.target);

      if (source) degrees.set(source, (degrees.get(source) || 0) + 1);
      if (target) degrees.set(target, (degrees.get(target) || 0) + 1);
    });

    // Find min/max degrees
    const degreeValues = Array.from(degrees.values());
    const minDegree = Math.min(...degreeValues);
    const maxDegree = Math.max(...degreeValues);

    // Create sequential scale
    const colorScale = d3
      .scaleSequential(d3.interpolateViridis)
      .domain([minDegree, maxDegree]);

    // Apply colors
    ctx.nodes
      .transition()
      .duration(300)
      .attr('fill', (d: any) => {
        const degree = degrees.get(d) || 0;
        return colorScale(degree);
      });

    // Update node data
    ctx.data.nodes.forEach((node: any) => {
      const degree = degrees.get(node) || 0;
      node.color = colorScale(degree);
      node.degree = degree;
    });

    logger.debug('Colored nodes by degree, range:', minDegree, '-', maxDegree);
  }

  /**
   * Color nodes by cluster (requires cluster property)
   */
  public colorByClusters(context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    // Get unique clusters
    const clusters = new Set<string>();
    ctx.data.nodes.forEach((node: any) => {
      if (node.cluster !== undefined) {
        clusters.add(String(node.cluster));
      }
    });

    // Create categorical scale
    const colorScale = d3.scaleOrdinal(d3.schemeTableau10).domain(Array.from(clusters));

    // Apply colors
    ctx.nodes
      .transition()
      .duration(300)
      .attr('fill', (d: any) => {
        if (d.cluster === undefined) return d.color || '#999';
        return colorScale(String(d.cluster));
      });

    // Update node data
    ctx.data.nodes.forEach((node: any) => {
      if (node.cluster !== undefined) {
        node.color = colorScale(String(node.cluster));
      }
    });

    logger.debug('Colored nodes by cluster, found', clusters.size, 'clusters');
  }

  /**
   * Apply random colors
   */
  public randomize(context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    ctx.nodes
      .transition()
      .duration(300)
      .attr('fill', () => {
        return d3.schemeCategory10[Math.floor(Math.random() * 10)];
      });

    // Update node data
    ctx.data.nodes.forEach((node: any) => {
      node.color = d3.schemeCategory10[Math.floor(Math.random() * 10)];
    });

    logger.debug('Randomized node colors');
  }

  /**
   * Reset to original colors
   */
  public reset(context?: ExtensionContext): void {
    const ctx = context || this.assertContext();

    ctx.nodes
      .transition()
      .duration(300)
      .attr('fill', (d: any) => {
        return d.originalColor || d.color || '#999';
      });

    logger.debug('Reset node colors');
  }

  /**
   * Get color for a value
   */
  public getColor(value: any): string {
    if (!this.colorScale) {
      logger.warn('Color scale not initialized');
      return '#999';
    }
    return this.colorScale(value);
  }

  /**
   * Get all colors in current scheme
   */
  public getAllColors(): string[] {
    if (!this.colorScale) {
      return [];
    }

    if ('range' in this.colorScale) {
      return this.colorScale.range();
    }

    return [];
  }
}
