# ADR-XXXX — Code-map navigation: source-ordered layout, depth-4 hierarchy, view-source

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

The compound hierarchical layout (dirs → files → symbols) placed symbols
in a ring around their parent file at arbitrary angles. This made the
graph correct as a dependency/containment map but not readable as a
*code map*: there was no spatial correspondence between a symbol's
position in the graph and its position in the source file. Users also
had no path from a graph node back to the originating source line.

Additionally, sub-symbols (depth ≥ 3: function arguments, struct fields,
class attributes) were placed at the file level alongside depth-2 symbols
because `compound_layout.py` had no Pass 4 and the frontend's
`computeChildrenMap` treated all `depth >= 2` nodes as file-level children.
Dragging a dir node propagated to files and depth-2 symbols but left
depth-3 nodes behind.

## Decision

**§1 — Source-ordered arc layout (Pass 3 refactor):** In `compound_layout.py`,
sort each file's symbols by their `line` attribute before placing them.
Arrange them in a 300° arc (clockwise from 12 o'clock, leaving a 60° gap
at the bottom), so the spatial position of a symbol within its file cluster
reflects its position in the source file: earlier lines at top, later lines
at bottom. This makes each file cluster a readable minimap of the source.

**§2 — Pass 4 (sub-symbol nesting):** Add a fourth layout pass that places
depth-3 sub-symbols in the same source-ordered arc pattern around their
nearest depth-2 parent symbol, with a tighter `subsym_orbit_r` (≈0.14√N).
The parent-detection now traces only to the nearest depth-2 ancestor for
depth-3 nodes (rather than depth-1 as before), so sub-symbols correctly
orbit their containing symbol rather than the file.

**§3 — Extend drag hierarchy to depth-4:** `CompoundLayoutManager
.computeChildrenMap()` now distinguishes depth-2 syms from depth-3+
sub-symbols and builds a fully-transitive map: dir → [files + depth-2
syms + depth-3 subsyms]; file → [depth-2 syms + their depth-3 children];
depth-2 sym → [depth-3 children]. Dragging any node now moves its
entire transitive subtree.

**§4 — View Source navigation:** Add `onViewSource(file, line, label)`
to `RadialMenuCallbacks`. A "◉ View Source" item appears in the radial
menu for any depth ≥ 2 node that has a `line` attribute. For GitHub
repos the `file` attribute is a `raw.githubusercontent.com` URL; the
handler converts it to a `github.com/blob/` URL with `#L{line}` anchor
and opens it in a new tab. For local files, a brief in-page toast shows
the file:line info.

## Consequences

- The source-ordered arc makes compound layout genuinely navigatable
  as a code map; the trade-off is that the arc convention (12 o'clock =
  top of file) must be stable across re-renders, which is guaranteed by
  the deterministic line-sort.
- Sub-symbol nesting works for depth-3 only when `depth=3` (deep mode)
  is selected; at the default `depth=2` no sub-symbols are emitted by the
  parsers, so Passes 3 and 4 are indistinguishable from the old behaviour.
- `computeChildrenMap` now does three nearest-neighbour sweeps (files→dirs,
  depth-2→files, depth-3→depth-2) — O(N²) per tier. For a CPython-sized
  graph at depth=3 this could be 10k× operations; if profiling shows this
  is a bottleneck the map should be built once from the graph edges rather
  than re-derived from positions.
- View Source opens GitHub blob URLs in a new tab. This only works when
  the backend fetched the source from GitHub (raw URLs present); local
  uploads show a toast instead.

## Alternatives considered

1. **Linear column layout for symbols** (vertical list, line order) rather
   than arc — rejected: the orbit/arc shape matches the existing compound
   layout visual language and ensures no overlap with neighbouring clusters.
2. **Reverse-proxy source viewer inside the app** rather than opening a new
   tab — deferred: requires fetching and rendering file content, adding
   significant surface area; new-tab navigation achieves the same goal for
   now.
3. **Extend drag to depth-5+** — deferred: no parser currently emits
   depth > 3, so the code handles it via the orphan-ring fallback; proper
   nesting can be added if deeper parsers arrive.

## Revision triggers

- Performance profiling shows `computeChildrenMap`'s nearest-neighbour
  loops are a bottleneck at depth=3 for large repos — switch to edge-based
  parent assignment (matching the backend's approach).
- A third renderer besides `graph_renderer.ts` adds a radial menu —
  `onViewSource` needs to be wired there too.

## Amendments

*None.*
