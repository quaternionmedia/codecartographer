# Codecarto documentation

These pages explain how to install, run and extend Codecarto.

## Reference

- [Getting Started](getting-started.md): install, run, and draw a first graph
- [CLI](cli.md): every `codecarto` command, its options, and the environment
  variables the code reads
- [API](api.md): every route the backend serves, and the envelope it answers in
- [Architecture](architecture.md): the backend, the frontend, the parse
  pipelines, the caches, and how a graph gets from one to the other
- [Services](services.md): the service layer, module by module
- [Extending](extending.md): the node schema, the renderers, and adding a
  parser, renderer, styling option, extension or route
- [UI reference](ui.md): the panels, the canvas and the menus
- [Scale](scale.md): what a show export costs a reader, measured; how fast the
  corpus grows; and the budgets and rules that keep its pages manageable

## Open work

- [Roadmap](roadmap/README.md): the index of planned work
- [Rust and the firmware languages](roadmap/rust.md)
- [Lexicons and constructs](roadmap/lexicon.md)
- [C parsing from `compile_commands.json`](roadmap/c_parser_phase3_compile_commands.md)
- [Large repositories](roadmap/large-repos.md)
- [The whole corpus at every depth](roadmap/the-corpus-at-every-depth.md)
- [A page without a server](roadmap/a-page-without-a-server.md)

The panels that draw other projects' data -- the topology, capability and
overview panels -- are built to a plan in the governance corpus, the
organisation's shared decisions vendored here as a submodule:
`governance/qm/plans/the-web-window.md`.
