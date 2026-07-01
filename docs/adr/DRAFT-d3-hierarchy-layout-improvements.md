# ADR-XXXX — Hierarchical drag propagation, per-depth labels, and compound layout spread improvements

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

The compound hierarchical layout (dirs → files → symbols) produced a
correct three-tier grouping but had three interaction and visual gaps:

1. **Drag**: directory and file nodes are visually presented as cluster
   containers (translucent bounding circles) but dragging one moved only
   that node — its children stayed behind, breaking the spatial grouping
   the layout is meant to communicate.

2. **Label granularity**: the only label toggle was a single
   `showNodeLabels` global boolean. At depth=2 (thousands of symbols in a
   large repo) labels are noise; at depth=0 (a handful of dir nodes) labels
   are navigation. Users had to choose either all or none.

3. **Spread scaling and axis**: `file_orbit_r` grew as `sqrt(n_files)`
   — the number of *direct* file children — but not as a function of how
   large those files' symbol clusters are. A dir with 2 files each carrying
   50 symbols got the same file orbit radius as a dir with 2 empty files,
   causing symbol clusters to overlap. Additionally, the dir spring layout
   was isotropic (no directional bias), so the dir-layer axis and the
   file/symbol cluster axes were indistinguishable.

## Decision

**§1 — Hierarchical drag:** extend `CompoundLayoutManager` in
`compound_layout.ts` with `computeChildrenMap(nodes)` — returns a Map
from parent nodeId to all transitive descendant nodeIds (dir → [files +
their symbols]; file → [its symbols]), using the same nearest-assignment
spatial logic already in `computeGroupBounds`. Store this map in both
`StreamingGraphRenderer._childrenMap` and `GraphRenderer._childrenMap`
(computed when compound backgrounds are drawn). In each renderer's drag
handler, compute the frame-by-frame delta `(dx, dy)` before updating the
dragged node's position, then propagate the same delta to every descendant
node's `x/y/fx/fy` and its SVG element. Redraw compound background circles
on drag end so they follow the moved cluster.

**§2 — Per-depth labels:** add `showLabelsByDepth?: Partial<Record<number,
boolean>>` to `GraphStylingOptions` (both in `state/types.ts` and
`control_panel.ts`'s local copy). When a depth has an entry, it overrides
`showNodeLabels` for that depth; absent entries fall back to the global
flag. Both renderers check this in label `display` style; `StreamingGraph
Renderer.updateStyling()` re-evaluates all labels per-node when either
`showNodeLabels` or `showLabelsByDepth` changes. The control panel's Graph
Settings tab gains 4 per-depth chip-checkboxes (Dir / File / Sym / Sub).

**§3 — Compound layout spread:** in `compound_layout.py`:
- `file_orbit_r(n_files, max_child_sym_r)` now adds `max_child_sym_r`
  (the largest symbol-cluster radius among the dir's files) to the base
  orbit radius, so file-cluster bounding circles don't overlap.
- A per-dir `max_child_sym_r` is computed before pass 1, giving each
  directory's pass-2 orbit its own appropriate size.
- The directory spring layout is stretched by `(x_stretch=1.6,
  y_stretch=0.7)` after the spring positions are computed, so the directory
  layer spreads more along the X axis than the Y axis.

## Consequences

- The `computeChildrenMap` spatial assignment (nearest-dir for files,
  nearest-file for symbols) and the `computeGroupBounds` spatial assignment
  are derived from the same logic but are separate codepaths — in both
  TypeScript and across backend Python. Keeping them in sync is a manual
  discipline (same issue already noted for `computeGroupBounds` and
  `compound_layout.py`'s pass-2/pass-3 parent detection in *Compound
  hierarchical layout*).
- `showLabelsByDepth` is not persisted in the saved GL layout (it is part
  of `graphStyling` in Meiosis state, not `LayoutManager.toConfig()`).
  Saved layouts remember panel arrangement but not graph styling — this is
  consistent with current behavior for all other styling options.
- The x/y axis-stretch values (1.6, 0.7) were tuned empirically on a 2-dir
  25-node test graph; they are not derived from first principles. A repo
  with a very different dir/file/symbol count ratio may look noticeably
  asymmetric.

## Alternatives considered

1. **Propagate drag via edges** (walk the `contains` edges at drag time
   rather than pre-computing a children map) — rejected: O(E) edge-walk on
   every mouse-move event is measurably expensive on large graphs; the
   pre-computed map is O(N) computed once, O(K) per drag event where K is
   the number of descendants.
2. **Replace `showNodeLabels` entirely with `showLabelsByDepth`** — rejected:
   the global toggle is still the right default UX for most users; per-depth
   overrides are an additive refinement, not a replacement.
3. **Derive axis-stretch from the dir/file ratio** (e.g. larger stretch when
   dirs outnumber files proportionally) — deferred: the fixed-coefficient
   approach is sufficient for the observed cases; a data-driven stretch could
   be added as a follow-up if the fixed values prove unsuitable at scale.

## Revision triggers

- The frontend/backend spatial-assignment duplication causes a visible bug
  (drag groups don't match bounding circles, or computeGroupBounds assigns
  nodes to different parents than computeChildrenMap), forcing
  deduplication.
- Per-depth label preferences become a frequently-used feature that warrants
  persistence across sessions (add to the saved styling state).
- The axis-stretch values produce obviously wrong layouts for a real
  repo (e.g., all dirs collapsed onto a line or clustered at origin) —
  revisit the stretch coefficients or derive them dynamically.

## Amendments

*None.*
