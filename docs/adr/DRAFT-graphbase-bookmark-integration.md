# ADR-XXXX — Wire graphbase as a named bookmark store via /db/bookmarks

| | |
|---|---|
| **Status** | Proposed |
| **Date** | 2026-06-30 |

## Context

The graphbase submodule (`graphbase/src/main.py`, mounted at `/db/*`) has
provided full graph CRUD since it was added, but nothing in the frontend
called it — confirmed by a `web/src/` grep in the 2026-06-27 architectural
unification pass. The underlying MongoDB collection stores
`nx.node_link_data` format graphs. Two problems stopped naive wiring:

1. The existing `/db/graph/insert` endpoint requires
   `{"nodes": [...], "links": [...]}` in NetworkX format. The frontend
   holds gJGF format (`{"nodes": {id: {metadata: ...}}, "edges": [...]}`),
   so storing and retrieving the full graph would require format conversion
   in both directions with a meaningful round-trip cost.

2. Replaying a stored full graph would need a new render path that bypasses
   the streaming pipeline — more surface area, and the CacheService already
   provides short-lived graph-result caching (TTL 24h) better suited to
   "don't re-parse what you just saw."

## Decision

Add a `bookmarks` collection in the same `graphbase` MongoDB database with
three new backend routes (`POST /db/bookmarks`, `GET /db/bookmarks`,
`DELETE /db/bookmarks/{name}`) that store lightweight parse-input records
(`{name, url, layout, depth, extensions, saved_at}`) rather than the full
graph payload. Loading a bookmark reuses the existing `_startStreamFromUrl`
path already used by repo fetch and cache recall — the graph is re-parsed
(and will hit CacheService if still cached) rather than replayed from a
stored artifact. The graphbase panel (`graphbase_panel.ts`) is registered
as an addable GL panel (not in the default layout — requires MONGODB_URI)
and shows a clear "unavailable" state when the backend has no `MONGODB_URI`
configured.

## Consequences

- Storing bookmarks costs essentially nothing (a few dozen bytes per
  entry vs. potentially hundreds of KB for a full gJGF graph).
- The re-stream on load means the graph re-parses from GitHub; if the
  CacheService TTL has expired the wait returns but the user gets a
  live-fresh graph. This is a deliberate trade-off: bookmarks are
  "names for repos I want to revisit," not "snapshots of exactly what I
  saw last time."
- Full gJGF graph storage (snapshots) remains a valid future direction
  for cases where parse reproducibility or offline replay matters — it
  would likely use the existing `/db/graph/insert` endpoint with a
  frontend-side gJGF → node_link_data conversion, not this bookmark path.
- The `graphbase_panel.ts` is not in `DEFAULT_LAYOUT_CONFIG` by design:
  adding it to the default would show a non-functional "unavailable" panel
  to every user without MongoDB. It is discoverable via the "+" add-window
  menu for users who have configured it.

## Alternatives considered

1. **Store full gJGF graphs in graphbase** — rejected for this version:
   format conversion adds round-trip complexity, and the graph output
   already has short-lived caching via CacheService. Deferred, not ruled
   out.
2. **Add a "Save to graphbase" action in the existing repo/actions panels
   rather than a dedicated panel** — rejected: the bookmark list (list,
   load, delete) needs its own surface; mixing it into repo-panel or
   actions-panel would violate the single-domain principle established by
   the panel split in *Generalize dock panels into a registry; add a
   window-add menu*.

## Revision triggers

- The "re-stream on load" latency becomes a real UX complaint (e.g.
  bookmarked repos that are slow to parse), prompting full graph snapshot
  storage rather than URL re-streaming.
- A user wants graphbase bookmarks in the default layout, suggesting enough
  uptake to warrant changing the default configuration.

## Amendments

*None.*
