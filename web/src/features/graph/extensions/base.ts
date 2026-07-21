/**
 * Base classes and interfaces for D3 extensions
 */

import * as d3 from 'd3';

/**
 * Base interface for all graph extensions
 */
export interface GraphExtension<TNode extends d3.SimulationNodeDatum = any, TEdge = any> {
  /** Unique identifier for this extension */
  id: string;

  /** Human-readable name */
  name: string;

  /** Extension description */
  description: string;

  /** Initialize the extension with graph context */
  initialize(context: ExtensionContext<TNode, TEdge>): void;

  /** Apply the extension to the graph */
  apply(): void;

  /** Remove the extension and clean up */
  destroy(): void;

  /** Check if extension is currently enabled */
  isEnabled(): boolean;

  /** Enable the extension */
  enable(): void;

  /** Disable the extension */
  disable(): void;
}

/**
 * Context provided to extensions
 */
export interface ExtensionContext<TNode extends d3.SimulationNodeDatum = any, TEdge = any> {
  /** SVG container selection */
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;

  /** Graph data group selection */
  graphGroup: d3.Selection<SVGGElement, unknown, null, undefined>;

  /** Node selections. Element type is SVGGElement, not a shape-specific
   * element -- graph_renderer.ts wraps every node's shape in a <g
   * class="graph-node"> to hold the shape path, label, and drag/selection
   * behavior together, matching how nodes are actually built. */
  nodes: d3.Selection<SVGGElement, TNode, SVGGElement, unknown>;

  /** Edge selections */
  edges: d3.Selection<SVGLineElement, TEdge, SVGGElement, unknown>;

  /** Label selections */
  labels: d3.Selection<SVGTextElement, TNode, SVGGElement, unknown>;

  /** D3 zoom behavior */
  zoom?: d3.ZoomBehavior<SVGSVGElement, unknown>;

  /** D3 force simulation (if active). Edge-datum type intentionally left as
   * `any` rather than threading TEdge through -- d3.Simulation's second
   * generic must satisfy SimulationLinkDatum<TNode>, a constraint real edge
   * data (source/target as string | GraphNode) doesn't cleanly satisfy, and
   * nothing here actually operates on simulation.force('link')'s data with
   * TEdge-specific typing. */
  simulation?: d3.Simulation<TNode, any>;

  /** Container element */
  container: HTMLElement;

  /** Current graph data */
  data: {
    nodes: TNode[];
    edges: TEdge[];
  };

  /** Selected nodes set */
  selectedNodes: Set<TNode>;

  /** Callback when graph changes */
  onGraphChange?: () => void;
}

/**
 * Base class for creating extensions
 */
export abstract class BaseExtension<TNode extends d3.SimulationNodeDatum = any, TEdge = any> implements GraphExtension<TNode, TEdge> {
  protected context: ExtensionContext<TNode, TEdge> | null = null;
  protected enabled: boolean = true;

  constructor(
    public readonly id: string,
    public readonly name: string,
    public readonly description: string
  ) {}

  public initialize(context: ExtensionContext<TNode, TEdge>): void {
    this.context = context;
  }

  public abstract apply(): void;

  public destroy(): void {
    this.context = null;
  }

  public isEnabled(): boolean {
    return this.enabled;
  }

  public enable(): void {
    this.enabled = true;
  }

  public disable(): void {
    this.enabled = false;
  }

  protected assertContext(): ExtensionContext<TNode, TEdge> {
    if (!this.context) {
      throw new Error(`Extension ${this.id} not initialized with context`);
    }
    return this.context;
  }
}
