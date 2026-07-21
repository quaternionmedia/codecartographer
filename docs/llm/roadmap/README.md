# Roadmap

Forward-looking design docs for work that's been scoped but not fully
built — distinct from `docs/llm/archive/legacy/`, which holds
completed-and-shipped survey/implementation write-ups.

| Doc | What it's about |
|---|---|
| [`topology-functionality-abstraction-maps.md`](topology-functionality-abstraction-maps.md) | What "useful, practical maps of code and the systems it represents" already means concretely in this codebase, and the next concrete step toward more of it |
| [`lexicon.md`](lexicon.md) | The Language Lexicon feature: hand-authored per-language ontologies on a hierarchy of abstraction layers, for C and Python. Option A (static reference graph) and a first slice of Option B (joining real parsed code to abstraction layers) are both shipped; extending `annotate_lexicon` into the main parse UI and adding a third language are natural next steps, not yet done |
| [`c_parser_phase3_compile_commands.md`](c_parser_phase3_compile_commands.md) | Using a real `compile_commands.json` (or a sandboxed build to generate one) instead of naive directory-walking, for more accurate C parse graphs on the GitHub-example flow |
