# Large repositories

**State:** open — delete when a repository the size of `torvalds/linux` parses
whole and can be explored on the canvas.

The goal is one navigable graph of a whole codebase: it starts at the directory
tree, a few hundred nodes even for linux, and grows where the reader expands it.

```
torvalds/linux  depth=0  →  ~300 directory nodes
  Expand kernel/          →  its sub-directories
  Expand kernel/sched/    →  its files
  Expand fair.c           →  its functions
```

Expanding a node is shipped: `POST /parse/expand`, and rad's Expand verb on the
canvas ([UI reference](../ui.md)). What follows is open.

## Content for a whole subtree

A GitHub repository under about 5 MB is fetched with its content, and
`/parse/stream-url` fetches each file's content as it parses; a larger one
arrives as structure only. Open: a parse request that downloads the content of
a chosen subtree in parallel, with a `download_content` flag and a
`max_file_downloads` cap, in `codecarto/services/unified_parser_service.py` and
`codecarto/routers/unified_parser_router.py`.

## A whole repository in one request

`POST /parse/repo?url=<github>&depth=2&extensions=.c,.rs`:

1. `git archive --remote <url> HEAD | tar x` into a temporary directory, one
   request and no GitHub API calls, so no rate limit.
2. Walk the directory and dispatch every file to its parser.
3. Stream gJGF back.

`/c-parser/github` downloads a repository's archive already, for C only. For
linux this is about 1 GB and minutes of parsing, which is what the next section
is for.

`CacheService` keys a graph by url, mode, layout and extensions, with a TTL.
Keying it by the commit as well would re-parse only when the ref moves.

## Parse jobs

A parse of a large repository outlasts a request:

- `POST /parse/job` answers `{job_id}` at once, and a worker thread parses.
- `GET /parse/job/{id}/ws` streams `{type: "progress", pct, message}`,
  `{type: "chunk", data: <partial gJGF>}` and `{type: "done"}`.
- The frontend merges each chunk into the graph on the canvas, as it merges an
  expansion.
- Job state in a small store (SQLite) lets the browser reconnect and continue.

The files: `codecarto/routers/parse_job_router.py` and
`codecarto/services/parse_job_service.py`, new, and `web/src/state/actions.ts`.

## Rendering at scale

The canvas is SVG. Positions come from the server's layout, and the force
simulation runs only when physics is turned on, so the cost past a few thousand
nodes is the DOM. The open option is a renderer that draws to a
`CanvasRenderingContext2D`, or to WebGL for hundreds of thousands of nodes,
registered in `renderers.ts` and chosen above a node count.
