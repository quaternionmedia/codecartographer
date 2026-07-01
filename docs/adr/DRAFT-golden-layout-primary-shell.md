# ADR-XXXX — Golden Layout as the primary application shell

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

The original frontend shell (`web/src/components/codecarto/codecarto.ts`,
741 lines, plus `codecarto.css`, 268 lines) hand-rolls panel layout, tab
switching, and panel sizing as a monolithic Mithril component tree. Adding
any new dockable panel means threading new state and DOM through that one
file. Two independent local branches converged on the same fix in roughly
the same window — direct evidence the old shell is a known pain point, not
a stylistic preference.

## Decision

Adopt Golden Layout 2.x (`golden-layout` npm package) as the primary
application shell. `web/src/layout/golden_layout_shell.ts` is the
top-level component; `codecarto.ts` is deleted entirely. Each dockable
area (graph, file tree, source panel, graph settings, actions/plotbar) is
registered as a GL component factory function
(`glInstance.registerComponentFactoryFunction(panelId, ...)`), mounting a
small dedicated Mithril component into the container GL gives it. Panel
lifecycle hooks use GL2's `beforeComponentRelease` event (not `close`,
which GL2 does not emit on `ComponentContainer` — confirmed by trial, and
called out in an inline comment so it isn't "fixed" back to `close` later
by someone trusting the more intuitive name).

## Consequences

- New panels are a registration, not a rewrite of the shell — see
  *Generalize dock panels into a registry; add a window-add menu*, which
  extracts the per-panel config into `panel_registry.ts`.
- GL2 pop-out windows are a known limitation: `registerComponentFactoryFunction`
  callbacks are bound to the *original* window's Mithril instance and are
  not replayed in a popped-out window, so popped-out panels render only
  the GL frame chrome with an empty content area.
  `popInOnClose: true` (`default_layout.ts`) works around this by
  auto-returning panels when their pop-out closes, rather than fixing the
  underlying binding gap.
- The header's restore-closed-panel mechanism (`hiddenDockPanels` /
  `restoreDockPanel` in `layout_context.ts`) used the structurally correct
  `beforeComponentRelease` event but imported `LayoutManager` as a
  type-only import while using it as a runtime value
  (`LayoutManager.defaultLocationSelectors`) — every restore click threw a
  `ReferenceError`, silently, since the shell's adoption. See *Generalize
  dock panels into a registry; add a window-add menu* for the fix and the
  detection method (a live console error, not static review).

## Alternatives considered

1. **Incrementally refactor `codecarto.ts`** instead of replacing the
   shell — rejected: the state-threading problem is structural (manual
   DOM/Mithril coordination for dock/undock/resize), not a matter of file
   organization.
2. **Roll a custom minimal docking layout** — rejected: GL2 already solves
   drag-to-dock, resizable splits, and stack/tab grouping; reimplementing
   that well is a large surface area for a project this size to own.

## Revision triggers

- GL2 ships a fix for the pop-out Mithril-binding gap, making the
  `popInOnClose` workaround unnecessary.
- Panel count or layout complexity grows enough that GL2's API surface
  becomes a bottleneck rather than a convenience.

## Amendments

*None.*
