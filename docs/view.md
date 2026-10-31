# The page without a server

`view.html` draws a graph document with no codecarto running anywhere. It is a
second page of the frontend, beside the window: the window's canvas and its
key, drawing what the page is handed, and nothing of the window that asks a
route. Any static host serves it, from any folder.

The decision is the draft record *One page without a server draws the graphs
and addresses other apps hand it*, on `project/codecartographer`
(quaternionmedia/qm#291). What is still to build is
[the roadmap's page](roadmap/a-page-without-a-server.md).

## Handing it a graph

| way in | how |
|---|---|
| a document by URL | `view.html?doc=<url>`, and `&view=<view>` for a show document's view |
| a file | dropped on the page, or chosen with **open a file** |
| a paste | the document's JSON, pasted anywhere on the page |

`&view=` applies to whatever document the page is handed; with none, a show
document opens at its estate view. A `?doc=` is read only from an `http` or
`https` address, and relative to the page, so beside the corpus's site
`view.html?doc=../qm/show/project/carlos/show.json&view=code` draws carlos's
code view. A host serving the document to a page on another origin must
allow it (`access-control-allow-origin`); the corpus's site allows every
origin.

## What it draws

Two shapes, each read once, whatever brought it
(`web/src/features/view/view_document.ts`):

| document | drawn |
|---|---|
| a show document (`show.json`, schema 1, as `codecarto show export` writes it) | one of its views: a subject's estate, a family's or the index's imports, a project's code |
| a gJGF document, `{ "graph": { "nodes", "edges" }, "metadata" }` | the graph, as a `/.../gjgf` route answers it |

Each view is drawn in the layout the window opens it in: a project's code view
as a Showcase, every other show view in compound outlines, and a gJGF
document in the layout its `metadata.layout` names. The page calculates no
layout. Each node is drawn where its document places it, and a node with no
position goes on its depth ring, as the canvas places any such node; the bar
says how many arrived with none.

Beside the graph, the bar says what is drawn (`project:carlos · code`), its
nodes and edges, and who handed it: the URL it was read from, the file's
name, or *pasted*. Under it, the producer's caveat, verbatim, and when and by
what the document was drawn, from which repository and commit. Everything a
document says is set as text, never as markup, and nothing in a document
runs.

## What it refuses

Each refusal says what is wrong and, where there is one, what to do instead.
What is already drawn stays drawn.

| handed | refused because |
|---|---|
| a family's code view | its document holds a pointer to each project's code view, which codecarto composes and lays out again: open it in codecarto at its `?show=` address, or each project's code view here |
| a project's system view | a composed system, which the window's system monitor lays out, and the page does not carry the monitor |
| a view the document marks absent | the document's own problem and remedy, as written |
| a view the document does not hold, such as the index's code and full views, which no export writes | it names the views it does |
| a show document of another schema | it names both schemas |
| anything else | not JSON, not an object, or neither shape; a `?doc=` that is not `http` or `https`, or that its host does not answer |

## Building and serving it

`npm run build:view`, from `web/`, builds the page alone into `dist-view/`:
`view.html`, the same page again as `index.html` so a folder's address opens
it, and the assets they name, relative to the page. The page's script is
34.5 KB gzipped, d3 included, against the 145.8 KB the window loads at once.
Copy the folder to any static host; the dev server (`npm run dev`) serves the
page at `/view.html` beside the window.

The browser suite opens it two ways (`web/tests/e2e/view.spec.ts`): from the
dev server, and built, from a subfolder of a plain static server
(`web/scripts/static-server.mjs`). Every test refuses each request to a path
the backend mounts, on any origin, and counts them: none.

## Not yet

An address (`?show=`), the messages other apps post to it, a project's system
view, and the views the backend composes are each a step of
[the roadmap's page](roadmap/a-page-without-a-server.md).
