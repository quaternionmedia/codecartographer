# ADR-XXXX — Compound hierarchical layout (dirs → files → symbols)

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

The unified graph schema treats directories, files, and symbols as nodes
at depths 0/1/2(/3) in one flat graph. Generic force-directed layouts
(spring, kamada-kawai) treat all nodes as peers, so a directory node and
the dozens of symbols inside its files compete for the same visual space —
there is no layout-level signal that a directory is a *container* for its
files, or that a file is a container for its symbols.

## Decision

Add a custom 3-pass layout (`codecarto/models/custom_layouts/compound_layout.py`,
registered in `position_service.py` as `'compound_layout'`):

1. **Pass 1** — spring layout on the directory-only subgraph, scaled by
   `sqrt(N_dirs) * cluster_r * 1.6` so directory clusters don't overlap.
2. **Pass 2** — files orbit their parent directory at
   `max(1.8, sqrt(n_files) * 0.9)` units.
3. **Pass 3** — symbols orbit their parent file at
   `max(0.45, sqrt(n_syms) * 0.28)` units.

Parent detection prefers `relation='contains'` edges, falls back to the
node's `file` attribute, and places true orphans on a fallback ring rather
than failing. The frontend (`compound_layout.ts`'s
`CompoundLayoutManager.computeGroupBounds`) independently re-derives the
same nearest-dir/nearest-file spatial grouping to draw translucent
bounding circles (depth-0 first for correct SVG z-order) — it does not
trust positional metadata round-tripped from the backend, so the visual
grouping stays correct even if a future layout perturbs positions.

## Consequences

- Spacing grows as `sqrt(N)` of *direct* children only, per level — a
  directory with few direct files but one very deep, wide subtree isn't
  given extra room by its grandparent's pass. Tracked as ongoing
  hierarchy-layout work (cumulative-subtree-aware spacing, axis bias
  between directory and file layers, per-depth label toggles).
- The frontend and backend independently compute the same dir/file
  grouping using the same two-tier parent-detection rule. Keeping both in
  sync is a manual discipline, not enforced by shared code — a future
  refactor could extract the parent-detection rule into one place
  consumed by both, but isn't worth the cross-language plumbing yet.

## Alternatives considered

1. **A single global force simulation with custom per-edge weights** (e.g.
   heavier attraction on `contains` edges) — rejected: weight tuning alone
   doesn't produce the "container with orbiting children" visual, it
   produces tighter clusters, not nested ones, and offers no clean way to
   draw a bounding circle around a fuzzy cluster boundary.
2. **Pre-computed treemap-style layout** — rejected for the first pass as
   a bigger algorithmic lift than the orbit approach for comparable visual
   clarity; remains a candidate if orbit spacing proves insufficient at
   scale.

## Revision triggers

- Cumulative-subtree spacing or directory/file axis bias work lands,
  changing the pass-1/pass-2 formulas described here.
- The frontend/backend duplicated parent-detection logic drifts out of
  sync in practice, forcing the shared-code extraction noted above.

## Amendments

*None.*
