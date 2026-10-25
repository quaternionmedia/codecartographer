# Services Documentation

Detailed documentation of Codecarto's service layer.

---

## Overview

Services contain the business logic, separated from HTTP routing (routers) and data structures (models).

```
services/
├── github_service.py          # GitHub API integration
├── local_repo_service.py      # Local filesystem parsing
├── unified_parser_service.py  # Depth-based parse orchestration (all languages)
├── cache_service.py           # Parsed-graph + repo-tree cache (filesystem + optional MongoDB)
├── c_parser_service.py        # C-specific parse orchestration (libclang)
├── lexicon_service.py         # Hand-authored language lexicons -> graph
├── construct_service.py       # What a node is across languages; the chrestomathy
├── cargo_service.py           # A Cargo workspace from manifests and recorded cargo documents
├── link_map_service.py        # A linker's map file: sections, symbols, each region's measured use
├── examples_service.py        # The examples bundled under examples/, for the project selector
├── graph_serializer.py        # Graph JSON serialization
├── palette_service.py         # A node's base -> the palette's style; the estate vocabulary
├── position_service.py        # Node positioning
└── parsers/
    ├── language_parser.py     # LanguageParser Protocol + ParserRegistry
    ├── python_language_parser.py
    ├── c_language_parser.py
    ├── rust_language_parser.py   # Rust at the item level: tokenizer, module tree, relations
    ├── linker_script_parser.py   # GNU ld scripts and memory.x: regions, sections, symbols
    ├── regex_language_parser.py  # one regex adapter per language; `_LANGUAGES` is the list
    └── ASTs/
        └── python_custom_ast.py
```

`palette_router.py` serves `DefaultPalette` from `models/plot_data.py`. There
is no palette store, so `/palette/custom` answers `unavailable` (`docs/api.md`).
`palette_service.py` is where a palette is applied; see *palette_service* below.

---

## LocalRepoService

**File:** `local_repo_service.py`

Parses local filesystem directories into Codecarto's data structures.

### Functions

#### `get_local_repo(path, extensions, exclude_dirs)`

Scan a local directory and build a Directory structure.

```python
from codecarto.services.local_repo_service import get_local_repo

directory = get_local_repo(
    path="/path/to/project",
    extensions=[".py", ".js"],
    exclude_dirs=[".git", "node_modules", "__pycache__"]
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | str | - | Path to directory |
| `extensions` | List[str] | `[".py"]` | Extensions to include |
| `exclude_dirs` | List[str] | See below | Directories to skip |

**Default exclusions:** `.git`, `.venv`, `venv`, `__pycache__`, `node_modules`, `.pytest_cache`, `.mypy_cache`, `dist`, `build`, `.eggs`, `*.egg-info`, `.vs`, `.idea`, `.vscode`, `bin`, `obj`, `target`

**Returns:** `Directory` model with `info`, `size`, and `root` (Folder)

---

#### `get_file_stats(directory)`

Get statistics about files in a Directory.

```python
stats = get_file_stats(directory)
# {'total_files': 45, 'total_size': 156234, 'python_files': 45, 'folders': 12}
```

---

## GitHubService

**File:** `github_service.py`

Integrates with GitHub API to fetch repository contents.

### Functions

#### `get_raw_from_repo(url)`

Fetch a GitHub repository's directory tree, cached via `CacheService`
(see `docs/architecture.md`, *The two caches*). On a cache miss, fetches the
full tree in two API calls (`fetch_tree_fast`, the Git Trees API) and then
fetches file content per the repo's size tier — full content for small
repos, structure only for medium repos, a shallow listing for huge ones.

```python
from codecarto.services.github_service import get_raw_from_repo

directory = await get_raw_from_repo("https://github.com/user/repo")
```

**Returns:** `Directory` (file contents present only for small repos)

---

#### `get_raw_from_url(url)`

Fetch raw content from a specific file URL.

```python
content = await get_raw_from_url(
    "https://raw.githubusercontent.com/user/repo/main/file.py"
)
```

**Returns:** File content as string

---

### GitHub Token

`resolve_github_token()`, cached by `get_github_token()` and used by
`create_headers()`. Resolution order (first non-empty wins):
`CC_GITHUB_TOKEN` env var → `gh auth token` (keyring) → `GITHUB_TOKEN`/
`GH_TOKEN` env vars → `/run/secrets/github_token` (Docker secret) →
unauthenticated, at 60 requests an hour, with a warning in the log. `gh auth
token` runs with `GITHUB_TOKEN` and `GH_TOKEN` removed from its environment, so
it answers from the keyring; to use another token, set `CC_GITHUB_TOKEN`. See
`governance/qm/adr/DRAFT-github-token-resolution.md` for why the order is
keyring-before-env-var, and `GET /auth/github` (`docs/api.md`) to inspect the
resolved source at runtime.

---

## UnifiedParserService

**File:** `unified_parser_service.py`

The language-agnostic parse orchestrator behind `/parse/*`. Dispatches
each file to its registered `LanguageParser` (via `ParserRegistry`,
keyed by extension), walks folders to the requested depth, and — for
languages needing cross-file context (`batch_whole_tree = True`, e.g.
C) — batches all of that language's files into one parser call instead
of one-at-a-time. `docs/architecture.md` has the pipeline.

### Methods

#### `parse(source, depth, extensions, layout)`

Parse a `Directory`/`Folder` structure at the given depth (1 =
dirs/files only, 2 = symbols and cross-file edges too).

```python
graph = UnifiedParserService.parse(directory, depth=2, extensions=None, layout="Spring")
```

**Returns:** gJGF-ready graph dict

---

#### `stream_parse(...)` / `stream_parse_url(...)` (async generators)

SSE variants of `parse()` — yield `meta`/`node`/`edge`/`done` events as
parsing progresses, for the local-directory and GitHub-URL cases
respectively. Cache-hit replay (`CacheService`) short-circuits both to
an instant replay of the saved graph.

#### `expand_node(...)`

Lazily expand a single node's children on demand (used by the
compound-hierarchical layout's drill-down).

---

## Parsers

### PythonCustomAST

**File:** `parsers/ASTs/python_custom_ast.py`

Parses Python source code into AST-based graph.

```python
from codecarto.services.parsers.ASTs.python_custom_ast import PythonCustomAST

parser = PythonCustomAST()
graph = parser.parse(folder)
```

**Node Types Generated:**

| Type | Description |
|------|-------------|
| `Module` | Python module (file) |
| `Function` | Function definition |
| `Class` | Class definition |
| `Import` | Import statement |
| `Name` | Variable/name reference |
| `Call` | Function call |
| `Constant` | Literal value |
| `Argument` | Function argument |

---

`UnifiedParserService` builds the directory and file hierarchy itself (depth
1), and `_add_python_dependency_edges()` adds Python's `depends_on` edges between
files at depth 2 and deeper.

### RustLanguageParser

**File:** `parsers/rust_language_parser.py`

A tokenizer and a brace matcher, standard library only. Items, their nesting,
visibility, qualifiers, attributes, `extern` blocks and ABIs, receivers, field
types and the calls in a body are what it reads. Name resolution, types and
macro expansion are the compiler's, and each relation it draws says how it was
found (`resolution` on the edge): `module-tree` for a `use` walked through the
`mod` declarations, `crate-by-directory` for a sibling crate recognised by its
directory, `unique-name` for a call, impl or field type resolved only because
exactly one local item has the name. Its module docstring lists every relation.

It does not expand macros (an item inside `cfg_if!` or `bitflags!` is a
`macro_invocation`), resolve a method call on anything but `self`, or follow a
`use` through a re-export it cannot see.

---

## LexiconService

**File:** `lexicon_service.py`

Loads a hand-authored per-language lexicon (reserved words/operators on
a hierarchy of abstraction layers, from `data/lexicons/<language>.yaml`)
and projects it into the same graph pipeline the parsers use. See
`docs/architecture.md`, *Lexicons and the construct vocabulary*, and the
`/lexicon/*` endpoints in `docs/api.md`.

### Methods

| Method | Description |
|--------|-------------|
| `available()` | List language ids with a lexicon on disk |
| `load(language)` | Load + validate a language's YAML into a `Lexicon` |
| `to_graph(lexicon)` | Project to an `nx.DiGraph` |
| `to_json(lexicon)` | Project to the node-link `{nodes, links}` shape the plotter consumes |

---

## construct_service

**File:** `construct_service.py`, data in `data/constructs.yaml`

What a parsed node *is*, said once for every language the vocabulary lists.
`annotate(graph)` stamps `construct` and `meta.facets` and gives a node with no
look of its own its construct's; the unified pipeline runs it on every parse.
`reading(id)`, `table()` and `as_graph(id)` are the chrestomathy behind
`/lexicon/constructs` and `/lexicon/chrestomathy/*`. `layer_color(ordinal)` is
the one abstraction-layer ramp.

---

## cargo_service

**File:** `cargo_service.py`

A Cargo workspace read without running cargo: `read(path)` returns a `Reading`
(packages, dependencies, targets, features, firmware facts, the recorded
documents and their staleness, diagnostics, build-script facts) or a reason.
`as_graph`, `as_gjgf`, `metadata` and `as_data` serve `/cargo/*`;
`recorded_diagnostics(root)` and `annotate_diagnostics(graph, reading)` put
rustc's diagnostics on a parsed code map. The CLI's `cargo record` is the only
code that runs cargo.

---

## link_map_service

**File:** `link_map_service.py`

A linker's map file in GNU ld's or LLD's shape: `read(path)` returns a `LinkMap`
(output sections with their run and load addresses, input sections, symbols
with their sizes, and GNU ld's memory table) or a reason. `usage(map, regions)`
measures each region's use at run time and as load images; `annotate(graph,
map, ...)` puts the figures on a parsed code map's regions, sections, functions
and statics; `demangle` and `symbol_key` turn a Rust symbol back into the path,
type and function it was compiled from. A map is stale when something the link
reads changed after it was written: `link_input(path)` says which files those
are -- Rust, C, C++ and assembly sources (`.rs`, `.c`, `.h`, `.cc`, `.cpp`,
`.hpp`, `.s`, `.S`), linker scripts (`.ld`, `.lds`, `.x`, so `memory.x`),
`Cargo.toml`, `Cargo.lock` and `.cargo/config[.toml]`, and never a README or
other docs -- and `newest_input(root)` is the newest of them under a repository,
outside `target/`, `build/` and `dist/`. The code map and `cargo_service` both
judge a map by `newest_input`, so they cannot disagree about one; a recorded
`check.jsonl` or `metadata.json` is judged by `cargo_service`'s own walk, which a
linker script does not move.

It reads both shapes firmware is linked with: GNU ld's (`arm-none-eabi-gcc
-Wl,-Map=...`, which also prints the memory table) and LLD's (`rust-lld`, the
default for Rust's embedded targets, which does not). `codecarto cargo record
--map <bin>` links with `--profile release`, the build that is flashed, and
keeps the map; a C build passing `-Wl,-Map=target/codecarto/<name>.map` writes
one read the same way.

- **A region's use** is the sections the link placed in it at run time, plus
  the load images of sections run from elsewhere (`.data`, a `.ram_func`).
  Neither map prints a section's type, so a section has no load image when it
  holds nothing with contents -- only zeroed input (`.bss.*`, `COMMON`), or no
  input at all, as a stack reserved with `. = . + size` has -- or is named for
  zeroed memory (`.bss`, `.uninit`). Against a real link it agrees with
  `arm-none-eabi-size`.
- **On the code map**, the linker script's regions and sections carry
  `meta.measured`, and functions and statics carry `meta.bytes`. A symbol is
  demangled (Rust's legacy mangling, and the half-demangled form LLD prints)
  and joined within the crate it was compiled in, by name and, for a method,
  its impl's type, only where one item answers. A file's crate is the target
  whose root reaches it through `mod` items, cargo's targets naming the roots,
  so a package need not sit in a directory named after it; an unmangled name is
  looked for in the map's own binary only. A C name one file declares and
  another defines is joined to the file the map's object names. GNU ld lists no
  `static`; built with `-fdata-sections` and `-ffunction-sections`, one is read
  from the section GCC named for it (`.bss.rx_buffer`). A symbol from outside
  the parse (`core`, a runtime, the C library) is counted, not drawn.
- **Only placed sections count.** Both linkers print debug information, symbol
  tables, `.comment` and build attributes at address 0, inside any region that
  starts there (nRF52, SAMD, LPC, Kinetis); they are told by name, or by lying
  on addresses a placed section already holds (an `(INFO)` section such as
  defmt's).
- **On the crate graph**, the binary's target says its fill per region, and
  the map is a document row with its age. Once anything the link reads
  changes after it -- a source, a linker script, a manifest; not a README --
  the map is not used, as a stale `metadata.json` is not, and the row, the
  caveat and the code map's regions say why. Both judge it by
  `link_map_service.link_input`.

What it cannot see: inlined code has no symbol, so its bytes are its caller's;
and a map is only as current as the link that wrote it. Two of the test maps
under `tests/fixtures/linkmaps/` are ones the linkers wrote: rust-lld's for a
Cortex-M `blinky` and arm-none-eabi-ld's for a small C firmware.

---

## examples_service

**File:** `examples_service.py`

The examples bundled with a checkout, for the project selector: `bundled()`
lists each one `BUNDLED` names whose directory exists under `examples/`, with
the absolute path it is read from and whether it is a Cargo workspace. Only what
is named is offered, and an installed package, which has no `examples/`, offers
none. `examples/rust-firmware` carries the records real cargo and rust-lld wrote
for it, its absolute paths rewritten; its README says how to record it afresh,
with `scripts/record_example.py`, which records and rewrites them.

---

## CacheService

**File:** `cache_service.py`

Content-addressed cache for parsed graphs and fetched repo trees —
filesystem-backed, with an optional MongoDB backend when `MONGODB_URI`
is set. Key = `SHA256(schema version + url + mode + layout + extensions)[:16]`;
`GRAPH_SCHEMA_VERSION` is bumped when a parse's nodes change what they carry, so
a graph cached in an older shape is a miss rather than a reply. Distinct
from `graphbase` (a separate, user-named durable store) — see
`governance/qm/adr/DRAFT-cache-service-vs-graphbase.md` for why they're kept
separate.

### Methods

| Method | Description |
|--------|-------------|
| `cache_key(url, mode, layout, extensions)` | Compute the cache key |
| `get(key)` / `set(key, ...)` | Read/write a cached parsed graph |
| `list_cached()` | List all cached entries |
| `evict(key)` | Remove one cached entry |
| `get_tree(url)` / `set_tree(url, data)` | Cache a fetched repo tree separately from parsed graphs |
| `evict_repo(url)` | Remove a cached repo tree |

---

## CParserService

**File:** `c_parser_service.py`

C-specific parse orchestration via libclang, used by the dedicated
`/c-parser/*` endpoints (distinct from C files going through the
generic `/parse/*` path via `c_language_parser.py` — see
`docs/architecture.md`, *The two caches*).

### Methods

| Method | Description |
|--------|-------------|
| `parse_file(path)` | Parse a single C/H file |
| `parse_directory(path, ...)` | Parse a local directory, with an optional per-file progress callback |
| `parse_github(...)` | Parse a GitHub repo's C/H files |
| `list_cached_repos()` / `evict_repo_cache(key)` | Manage this service's own repo-tree cache |

---

## GraphSerializer

**File:** `graph_serializer.py`

Serializes NetworkX graphs to JSON format for client-side rendering.

### Methods

#### `serialize_to_gjgf(graph, options, isDependencyPlot)`

Convert NetworkX graph to Graph JSON Format (gJGF) with layout positions. A
multigraph keeps every edge between a pair of nodes, and a node that already
has a `size` keeps it.

```python
from codecarto.services.graph_serializer import GraphSerializer

gjgf = GraphSerializer.serialize_to_gjgf(
    graph=nx_graph,
    options=plot_options,
    isDependencyPlot=False
)
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `graph` | `nx.DiGraph` | NetworkX directed graph |
| `options` | `PlotOptions` | Layout, type, palette settings |
| `isDependencyPlot` | `bool` | Whether to color external dependencies |

**Returns:** Graph in gJGF format with node positions and styling

#### `create_metadata(graph, options)`

Generate metadata about the graph.

```python
metadata = GraphSerializer.create_metadata(graph, options)
# {'layout': 'Spectral', 'type': 'd3', 'nodeCount': 50, 'edgeCount': 75}
```

**Layouts Available:**

| Layout | Description |
|--------|-------------|
| `Spring` | Force-directed (default) |
| `Circular` | Circular arrangement |
| `Shell` | Concentric circles |
| `Kamada_Kawai` | Energy-based layout |
| `Spectral` | Eigenvector-based |

**Client-side Rendering:** The gJGF format is consumed by the frontend D3.js renderer for interactive visualization.

---

## palette_service

**File:** `palette_service.py`

Resolves a node's dotted `base` (`control.cond.if`) into the style a `Palette`
gives it, walking the dots leftwards to `unknown`: `style_for(base)`,
`style_for_type(node_type)`, and `apply_to(graph)`, which puts the shape, colour
and size on every node. `vocabulary(node_type)` is the one place an estate kind
becomes a shape, colour and size.

---

## PositionService

**File:** `position_service.py`

Calculates node positions for graph layouts.

### Custom Layouts

Located in `models/custom_layouts/`; `Positions(include_custom=True)` registers
whatever is there, and `/topology/available` lists the result.

| Layout | File | Description |
|--------|------|-------------|
| Compound | `compound_layout.py` | Hierarchical: dirs, then files, then symbols in nested orbits |
| Sorted Square | `sorted_square_layout.py` | Grid arrangement |

---

## Creating New Services

### Template

```python
# services/my_service.py

class MyService:
    
    @staticmethod
    async def my_operation(param: str) -> dict:
        """
        Description of operation.
        
        Args:
            param: Description
            
        Returns:
            Result description
        """
        # Implementation
        result = {"key": "value"}
        return result
```

### Integration

1. Create service in `services/`
2. Import in router
3. Call from endpoint

```python
# routers/my_router.py

from fastapi import APIRouter
from codecarto.services.my_service import MyService

MyRouter = APIRouter()

@MyRouter.get("/operation")
async def my_endpoint(param: str):
    return await MyService.my_operation(param)
```

---

## Service Dependencies

```
┌─────────────────┐
│     Routers     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Services     │
│(UnifiedParser-  │
│Service, GraphSe-│
│rializer)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│    Parsers      │     │     Models      │
│ (PythonCustomAST│     │ (Directory,     │
│  via ParserReg- │     │  Graph, Plot)   │
│  istry)         │     │                 │
└─────────────────┘     └─────────────────┘
```

---

## Error Handling

Services use custom exceptions from `util/exceptions.py`:

```python
from codecarto.util.exceptions import CodeCartoException

class GithubError(CodeCartoException):
    pass

class Github404Error(GithubError):
    pass
```

### Exception Pattern

```python
try:
    result = await service_operation()
except CodeCartoException as exc:
    return proc_exception(exc.source, exc.message, exc.params, exc)
except Exception as exc:
    return proc_exception("operation", "Unexpected error", {}, exc)
```
