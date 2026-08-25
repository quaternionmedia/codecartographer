/**
 * The shapes every graph in this application is made of.
 *
 * **THEY LIVE HERE BECAUSE THEY OUTLIVED THEIR RENDERER.** These three
 * interfaces were declared at the top of `graph_renderer.ts`, so every file
 * that needed to name a node imported the renderer to get at them — the
 * extensions, the layout context, rad's host half, the compound layout, and the
 * other renderers. A type is not a rendering strategy, and tying the two
 * together meant one renderer could not be retired without touching everything
 * that merely wanted to describe a node. ADR §7.
 */

export interface GraphNode {
  id: string;
  label?: string;
  color?: string;
  shape?: string;
  size?: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  // Unified schema fields (depth 0=dir, 1=file, 2=symbol, 3=sub-symbol)
  depth?: number;
  language?: string;    // 'python' | 'c' | 'unknown'
  kind?: string;        // 'directory' | 'file' | 'class' | 'function' | ...
  meta?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  label?: string;
  color?: string;
  [key: string]: unknown;
}

export interface GraphData {
  graph: {
    nodes: Record<string, GraphNode> | GraphNode[];  // gJGF uses object, but also support array
    edges: GraphEdge[];
    directed?: boolean;
  };
  metadata: {
    layout: string;
    type: string;
    nodeCount: number;
    edgeCount: number;
    palette_id: string;
    background_color?: string;
    edge_color?: string;
    node_label_color?: string;
    edge_label_color?: string;
    arrow_color?: string;
    node_border_color?: string;
    node_label_size?: number;
    edge_label_size?: number;
    [key: string]: unknown;
  };
}
