# Contributing to Codecarto

Every change arrives as a pull request. This page says where each part of the
work is described; it repeats none of it.

- **Set up and run it:** [Getting Started](../docs/getting-started.md).
- **Process and gates:** [`AGENTS.md`](../AGENTS.md). It says how a change is
  proposed and recorded, gives the test commands and the governance gates, and
  holds the contributorship rule: bylines are human, and tool use is disclosed
  as a `Tools:` note.
- **Patterns:** [Extending](../docs/llm/EXTENDING.md), for a new parser,
  renderer, styling option, extension or route.
- **How the pieces fit:** [Architecture](../docs/architecture.md).
- **Why it is built this way:** the decision records in `governance/qm/adr/`.

Before a pull request is opened, the checks `AGENTS.md` lists pass for what it
touches, and a check it adds has been seen to fail. A document that names a
route, command, path or environment variable is read against the tree by
`tests/test_docs_routes.py`.
