/**
 * Depth-based node size multiplier, shared by graph_renderer.ts (static
 * D3 render) and streaming_renderer.ts (progressive SSE render) — was
 * defined identically in both files independently; consolidated here so
 * the two renderers can't silently drift on this constant table.
 *
 * Multiplies the user-configured base node size (styling.nodeSize).
 * Unified schema depth: 0 = directory, 1 = file, 2 = symbol, 3 = sub-symbol.
 */
export function depthSizeMultiplier(node: { depth?: unknown }): number {
  const dep = node.depth as number | undefined;
  if (dep === 0) return 3.0;   // directory: 3× larger
  if (dep === 1) return 1.8;   // file: 1.8×
  if (dep === 3) return 0.6;   // sub-symbol: 0.6×
  return 1.0;                  // symbol (depth=2) and legacy: base size
}
