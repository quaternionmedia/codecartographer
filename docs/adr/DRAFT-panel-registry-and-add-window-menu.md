# ADR-XXXX — Generalize dock panels into a registry; add a window-add menu

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

The fixed 5-panel `DOCK_PANEL_CONFIGS` map was duplicated across
`layout_context.ts` (config) and `golden_layout_shell.ts` (five
near-identical `registerComponentFactoryFunction` calls plus a manual
label switch). There was no way to add a panel except via the header
restore buttons, which only ever appear for a panel the user had already
closed — no "+" control, no right-click, no saved/default layouts.

Separately, the header's closed-panel restore button threw
`ReferenceError: LayoutManager is not defined` on every click.
`layout_context.ts` imported `LayoutManager` via `import type { ...,
LayoutManager } from 'golden-layout'`. `import type` is erased entirely
at compile time, but `restoreDockPanel()` reads
`LayoutManager.defaultLocationSelectors` as a runtime value — a static
property access with no binding left in the emitted JS. The bug predates
this work and is the actual reason restore has never functioned. This
project's build (`vite build`, esbuild) transpiles per file without
cross-module type checking, so the misuse compiled cleanly and shipped
silently every time; it surfaced via a live browser console, not a
source read (the `import type` runtime footgun is now a documented
pattern in this project's implementation-patterns notes).

## Decision

- Extract the panel list into `panel_registry.ts` — one array of
  `{ id, menuLabel, config, overflow, mount }`, replacing the
  `DOCK_PANEL_CONFIGS` map and the five duplicated
  `registerComponentFactoryFunction` calls with a loop over the registry.
  Same registration-table pattern as `ParserRegistry` (backend) and the
  renderer registry (`renderers.ts`, frontend).
- Fix the restore bug at its source: import `LayoutManager` as a value
  (`import { LayoutManager } from 'golden-layout'`), keep `LayoutConfig`
  as `import type` since it is genuinely type-only. `hiddenDockPanels` /
  `hideDockPanel` / `showDockPanel` / `restoreDockPanel` keep their
  existing shape — the defect was the import, not the surrounding logic.
- Add a header "+" button and a right-click handler on the dock area, both
  opening `AddPanelMenu` (`web/src/layout/components/add_panel_menu.ts`)
  — a dropdown listing registered panels not currently in the layout
  (`LayoutContext.addablePanels()`), reusing `restoreDockPanel()` (it
  already handles "add if missing, show if hidden" in one method).
- Add layout persistence: `saveLayoutAsDefault()` serializes
  `LayoutManager.toConfig()` to `localStorage['cc:gl-layout:default']`;
  `loadInitialLayoutConfig()` is consulted on boot instead of always
  loading `DEFAULT_LAYOUT_CONFIG`; `resetLayoutToBuiltinDefault()` clears
  the saved entry. These three actions live in `AddPanelMenu` under a
  "Layout" section, to avoid adding more header chrome than one button.

## Consequences

- Adding a sixth dock panel is one entry in `panel_registry.ts`, not edits
  across three files.
- Restore, add-window, and layout persistence all route through the same
  `restoreDockPanel()` / `LayoutManager` calls, so there is one place to
  reason about dock-panel placement rather than three.
- `saveLayoutAsDefault()` / `resetLayoutToBuiltinDefault()` persist panel
  arrangement and sizing only (`LayoutManager.toConfig()`); they do not
  version or migrate the saved config if `panel_registry.ts`'s panel ids
  change later — a stale saved layout referencing a removed panel id
  simply won't place that panel on load (GL skips unresolvable component
  types), not error.
- No `tsc`-based type-check step exists in this repo's build or CI, so
  `import type`-misused-as-value bugs of this exact shape can recur and
  will not be caught by `vite build` alone. Adding a `tsc --noEmit` step
  is a worthwhile follow-up, tracked separately.

## Alternatives considered

1. **Rewrite the restore mechanism from scratch** instead of fixing the
   import and building alongside it — rejected: the actual defect is a
   one-line import correction; a rewrite would not have been guaranteed
   to touch it and would have discarded a working design (registry +
   menu + persistence) for no benefit.
2. **Add a `tsc --noEmit` CI gate as part of this change** — deferred:
   real value, but a build-pipeline change is a separate decision from
   the panel-registry work and deserves its own review.

## Revision triggers

- A `tsc --noEmit` CI gate is added, closing the `import type` blind spot
  this ADR documents as open.
- A sixth dock panel or a second add-window entry point is built, testing
  whether `panel_registry.ts`'s shape still fits.

## Amendments

*None.*
