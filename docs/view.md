# The page without a server

`view.html` draws a graph document with no codecarto running anywhere. It is a
second page of the frontend, beside the window: the window's canvas and its
key, drawing what the page is handed, and nothing of the window that asks a
route. Any static host serves it, from any folder.

The decision is the draft record *One page without a server draws the graphs
and addresses other apps hand it*, on `project/codecartographer`
(quaternionmedia/qm#291). What is still to build is
[the roadmap's page](roadmap/a-page-without-a-server.md).

## Walking it

The page's own address opens every family, read from the corpus's show
folder published beside it. From there a reader walks it, through the bar:
the trail steps up, the views step across, and the list of families and
projects the drawing names, or a double-click on one, steps down. Every step
rewrites the address and adds a history entry, so a copied address reopens
the drawing and **Back** walks back. [Journeys](journeys.md) is each walk, a
step at a time, and the browser test that walks it.

| address | draws |
|---|---|
| `view.html` | every family, from `../qm/show/`, the corpus's show folder beside the page on GitHub Pages |
| `view.html?show=<address>` | a subject's view, in the window's own grammar (`show_address.ts`): `?show=family:core`, `?show=project:carlos&view=code` |
| `view.html?show=...&docs=<folder>` | the same, from another show folder |
| `view.html?doc=<url>` | a document by URL, and `&view=<view>` for a show document's view |

A subject's document is `<folder>/index/show.json`,
`<folder>/family/<name>/show.json` or `<folder>/project/<name>/show.json`, as
`codecarto show export` writes them (`web/src/features/view/view_walk.ts`).
The trail is the window's, told what nests in what by the documents read: a
project's document names its families, a family's its subfamilies and
projects, and the index every family and what holds it. A family's own
document does not say what holds it, so the page reads the index once a visit,
in the background, to complete a trail; it reads each document once a visit,
so a step back draws at once.

The index is 19 KB gzipped as this codecartographer exports it, its estate
and imports views. The corpus's site serves 715 KB, with the whole corpus's
code view in it, until it exports again (measured 2026-10-31).

## Handing it a graph

| way in | how |
|---|---|
| a document by URL | `view.html?doc=<url>`, and `&view=<view>` for a show document's view |
| a file | dropped on the page, or chosen with **open a file** |
| a paste | the document's JSON, pasted anywhere on the page but the list's filter |

`&view=` applies to whatever document the page is handed; with none, a show
document opens at its estate view. A `?doc=` is read only from an `http` or
`https` address, and relative to the page, so beside the corpus's site
`view.html?doc=../qm/show/project/carlos/show.json&view=code` draws carlos's
code view. A host serving the document to a page on another origin must
allow it (`access-control-allow-origin`); the corpus's site allows every
origin. A file or a paste has no address: its views are drawn from the
document in hand, and the page offers no trail, list or link to copy.

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

Beside the graph, the bar says where it is (the trail, or for a document
with no address its title: `carlos · code map`), its views, the one drawn
pressed and named as the window's Show panel names them, its nodes and
edges, and who handed it: the URL it was read from, the file's name, or
*pasted*. Under it, *What this drawing can say* folds the producer's caveat,
verbatim, and when and by what the document was drawn, from which repository
and commit. Everything a document says is set as text, never as markup, and
nothing in a document runs.

## What it refuses

Each refusal says what is wrong and, where there is one, what to do instead;
**dismiss** folds it away. What is already drawn stays drawn. Arriving at a
view it refuses, with nothing drawn yet, the page draws the subject's first
view it can draw under the refusal, and the address names what is drawn. A
view its subject's document holds but the page does not draw is offered with
a dashed border, and pressed, says why.

Where the window draws what the page does not, a refusal links to it,
**Open it in codecarto ↗**, at the same `?show=` address on
`http://localhost:2718/app`: the window, where `codecarto serve` runs on the
reader's machine at its default port.

| handed | refused because |
|---|---|
| a family's code view | its document holds a pointer to each project's code view, which codecarto composes and lays out again: open it in codecarto at its `?show=` address, or each project's code view here |
| a subject the show folder holds no document for | the window draws it from its clone |
| a project's system view | a composed system, which the window's system monitor lays out, and the page does not carry the monitor |
| a view the document marks absent | the document's own problem and remedy, as written |
| a view the document does not hold, such as the index's code and full views, which no export writes | it names the views it does |
| a show document of another schema | it names both schemas |
| anything else | not JSON, not an object, or neither shape; a `?doc=` that is not `http` or `https`, or that its host does not answer |

## Building and serving it

`npm run build:view`, from `web/`, builds the page alone into `dist-view/`:
`view.html`, the same page again as `index.html` so a folder's address opens
it, and the assets they name, relative to the page. The page's script is
38.6 KB gzipped, d3 included, against the 145.8 KB the window loads at once.
Copy the folder to any static host, as the workflow below does; the dev
server (`npm run dev`) serves the page at `/view.html` beside the window.

The browser suite opens it two ways (`web/tests/e2e/view.spec.ts`): from the
dev server, and built, from a subfolder of a plain static server
(`web/scripts/static-server.mjs`). Every test refuses each request to a path
the backend mounts, on any origin, and counts them: none.

## Published

`.github/workflows/pages.yml` publishes the page to this repository's GitHub
Pages, at `https://quaternionmedia.github.io/codecartographer/view.html`, and
the same page at the folder's own address. It builds `npm run build:view` on
each push to `main` that changes `web/`, uploads the folder the build writes,
and deploys it; it can be run again by hand from `main`. No pull request is
published: the browser suite opens the same built folder instead.

The repository's owner sets GitHub Actions as Pages's source, in the
repository's settings under Pages. Until then the deploy job fails, and
nothing else does.

The page shares `quaternionmedia.github.io` with the corpus's site, so a
relative address reaches the corpus's show documents:
`view.html?doc=../qm/show/project/carlos/show.json&view=code`.

## Not yet

The messages other apps post to it, a project's system view, and the views
the backend composes are each a step of
[the roadmap's page](roadmap/a-page-without-a-server.md).
