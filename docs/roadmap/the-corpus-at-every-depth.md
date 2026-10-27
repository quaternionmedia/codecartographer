# The whole corpus at every depth

**State:** open — delete when the index's full view can be drawn to every
symbol, and to every member, and each is published as the corpus's pages show
the first.

The index's full view (`?show=index&view=full`, `full.svg`) draws every node of
every project's code map as its page draws it, no deeper than holds the floor's
100 nodes (`stream_floor.py`), with no names: about ten thousand nodes. Two
deeper drawings of the same corpus are stubbed here: every symbol, and every
member. Each is a step past what the export has drawn, and neither is begun.

## Every symbol

Each project's code to its functions, classes and types, whatever its size.
Counted on clones beside this one, a project's symbols run about nine times its
directories and files, so the corpus is about thirty-five thousand nodes.

- **Where its graphs come from.** The corpus reads each project's code map from
  its show document (`show_service._code_map`), and a large project's is its
  files alone. A deeper corpus needs a deeper parse of every project, not kept
  in the documents (a large project's would be megabytes each): the export
  parses each at depth 2 into a folder of its own and hands the server that
  folder, as `CODECARTO_SHOW_DOCS` hands it the code maps now.
- **Whether the canvas draws it.** The streaming renderer has drawn the corpus
  at four thousand nodes in seconds; thirty-five thousand nodes and their edges
  in one SVG is untried. Measure the export at that size before choosing; the
  picture may want to be a PNG at twice the canvas's resolution, as the system
  view is, rather than an SVG of that many elements.
- **Done when** the export draws it from the host's default branches, the
  document says how deep it is and how many nodes it holds, and the corpus's
  codecartographer page shows it.

## Every member

The same to fields, methods and module-level names: about a hundred and sixty
thousand nodes, forty times the directories and files.

- **Past the browser.** The canvas draws each node as an SVG group; at this
  size the drawing is likely to exceed what a headless page holds in time. The
  likelier path is a raster drawn from the same packed places
  (`show_layout.pack`) outside the browser -- which is a second renderer, and
  the reason to try every symbol first and measure.
- **The fetch.** Every file of every public project is fetched from the host.
  The export's parses are cached by `CacheService`, and a second run reads
  them; the first is bounded by the host's rate limits.
- **Done when** a picture of it is drawn, stated as drawn by which renderer,
  and published beside the other two.
