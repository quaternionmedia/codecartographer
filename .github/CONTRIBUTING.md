# Contributing to Code Cartographer

> How to set this repository up, run it, change it and test it.
> [`AGENTS.md`](../AGENTS.md) carries the rules every change follows -- pull
> requests, contributorship, the decision records -- and this page is the
> working detail. Where this page and the tree disagree, the tree is right and
> this page is repaired; `tests/test_docs_routes.py` holds its ports and
> commands to the tree.

## Getting Started

### Prerequisites

- Python 3.10+ (`requires-python` in `pyproject.toml`)
- [uv](https://github.com/astral-sh/uv) -- `uv.lock` is the Python environment
- Node.js 20.19+ or 22.12+ (for the frontend; Vite 8's minimum, from its own
  `engines`)
- Docker (optional, for the MongoDB behind `/db`)

### Initial Setup

```bash
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
git submodule update --init governance/qm   # the decision records and the corpus
git submodule update --init graphbase       # optional: private, and only /db uses it

uv sync --extra dev                         # the lockfile is the environment, in .venv
cd web && npm ci                            # the frontend's lockfile, likewise
npx playwright install chromium             # once, for the browser tests
cd ..
```

`uv run …` runs inside `.venv` with nothing activated. `codecarto dev` and
`codecarto web` run `npm install` themselves when `web/node_modules` is
missing; `npm ci` installs exactly what `web/package-lock.json` pins.

## CLI Commands

```bash
uv run codecarto --help           # every command

uv run codecarto dev              # backend and frontend together
uv run codecarto serve            # backend only, reloading on change
uv run codecarto web              # frontend only, http://localhost:1234

uv run codecarto repo scan .      # a local repository's structure
uv run codecarto repo graph . -t ast

uv run codecarto lint             # ruff; --fix applies what it can
```

**The backend's port is `codecarto.cli.DEFAULT_PORT`, and it is not 8000.**
`serve --help` prints it, `CODECARTO_PORT` or `--port` moves it, and
`codecarto dev` prints both addresses on startup. Before trusting an answer,
ask what is answering: `/openapi.json` names this application `codecarto`.
AGENTS.md says why.

---

## Where Things Are

`docs/architecture.md` is the map of the backend, the frontend and the data
flow; `docs/llm/UI_REFERENCE.md` is the reading of the shell and its panels.
The frontend in outline:

```
web/src/
├── index.html, index.ts       # the page and its entry
├── layout/                    # the Golden Layout shell
│   ├── golden_layout_shell.ts # builds the dock, the "+" menu; loads the saved or built-in layout
│   ├── panel_registry.ts      # every dock panel, once -- a new panel is an entry here
│   ├── default_layout.ts      # the built-in arrangement, and the settings every layout loads with
│   ├── saved_layout.ts        # the check a saved arrangement passes before Golden Layout reads it
│   ├── layout_context.ts      # the state and actions every panel shares
│   ├── components/            # add_panel_menu.ts
│   └── panels/                # one Mithril component per panel
├── features/
│   ├── graph/                 # services/ (streaming_renderer.ts is the one canvas), rad/, extensions/, config/
│   ├── estate/                # the seam client, problem view and provenance the estate panels share
│   └── repository/services/
├── components/codecarto/      # control_panel (the controls the Upload, Repository and
│                              # Graph Settings panels render), help (modal, toasts), plot
├── state/                     # the Meiosis cell: cell_state.ts, state_controller.ts, actions.ts, types.ts
├── services/                  # plot_service.ts (the SSE stream), graphbase_service.ts, topology_service.ts
├── core/                      # logger.ts, animations.ts
└── styles/                    # index.css; root/root.css holds every theme's variables
```

### State

Application state is one Meiosis cell (`state/cell_state.ts`), wrapped by
`StateController` (`state/state_controller.ts`). `createActions`
(`state/actions.ts`) builds the actions that change it, and
`LayoutContext` hands the controller, the actions and the panel callbacks to
every panel. A panel reads `ctx.appState.state` in its `view` and calls an
action; Mithril redraws.

---

## Development Patterns

### Adding a Dock Panel

1. Write the panel in `web/src/layout/panels/` as a factory taking the
   `LayoutContext` and returning a Mithril component.
2. Add one entry to `PANEL_DEFINITIONS` in `web/src/layout/panel_registry.ts`:
   its id, menu label, Golden Layout config (with `id` equal to the registry
   id, which is how the shell finds a panel to focus or re-open), overflow and
   mount. It appears in the `+` menu with nothing else changed.
3. Add a row for it to the panel table in `docs/llm/UI_REFERENCE.md`;
   `tests/test_docs_routes.py` fails until there is one.

Closing a panel unmounts it, so anything it sets up in `oncreate` it takes down
in `onremove`.

### Adding a Feature Module

A feature is a directory under `web/src/features/` holding what it needs --
see `graph/` and `estate/`. Logic that decides what the UI *says*, rather than
how it looks, goes in a DOM-free module listed in `web/tsconfig.pure.json`, with
a test under `web/tests/pure/`: that build compiles it without the DOM and
`node --test` asserts it directly. `tsconfig.pure.json` says why.

A top-level directory under `web/src/` must not share a name with an API
prefix: the dev server proxies that prefix to the backend, so its modules never
load. `tests/test_docs_routes.py` fails when one does.

### Adding a Backend API Endpoint

```python
from fastapi import APIRouter

from codecarto.models.plot_data import PlotOptions
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.util.utilities import generate_return

MyFeatureRouter = APIRouter()


@MyFeatureRouter.post("/endpoint")
async def my_endpoint(options: PlotOptions) -> dict:
    """Process the request and return graph data."""
    graph = await some_service_call()
    gjgf = GraphSerializer.serialize_to_gjgf(graph, options)
    return generate_return(
        results={
            "graph": gjgf,
            "metadata": {
                "nodeCount": graph.number_of_nodes(),
                "edgeCount": graph.number_of_edges(),
            },
        }
    )
```

Register it in `codecarto/main.py` with its prefix --
`app.include_router(MyFeatureRouter, prefix="/my-feature", tags=["my-feature"])`
-- and a new prefix needs three more lines, each checked by
`tests/test_docs_routes.py`: a row in the README's endpoint table, a heading in
`docs/api.md`, and an entry in `API_PATHS` in `web/vite.config.js`, without
which the dev server answers the request itself and cannot.

---

## Graph Styling System

`GraphStylingOptions` in `web/src/state/types.ts` is the authority; the core of
it:

```typescript
export interface GraphStylingOptions {
  layout: string;              // a registry name: 'spring_layout', 'compound_layout', ...

  enablePhysics: boolean;
  chargeStrength: number;      // repulsion, in pixels
  linkDistance: number;        // target edge length, in pixels

  nodeSize: number;            // radius, in pixels
  nodeOpacity: number;         // 0.0 to 1.0
  nodeBorderWidth: number;
  colorBy?: string;            // 'auto' | 'layer' | 'type' | 'degree' | ...

  edgeWidth: number;
  edgeOpacity: number;

  showNodeLabels: boolean;
  showEdgeLabels: boolean;
  labelSize: number;
  labelColor: string;

  interactionProfile: string;  // default, cad, gaming, touch
}
```

### Layout Names

The menu offers the backend's registry names, and one rule
(`web/src/features/graph/services/layout_names.ts`) turns each into the name
the backend's `PlotOptions` speaks: drop `_layout`, capitalise each part, join
with `_`. There is no table and no fallback; an unknown name reaches the
server as written, and the server says what is registered.

| Menu value | Sent as | Laid out by |
|---|---|---|
| `spring_layout` | `Spring` | `nx.spring_layout()` |
| `compound_layout` | `Compound` | `custom_layouts/compound_layout.py` |
| `spectral_layout` | `Spectral` | `nx.spectral_layout()` |
| `kamada_kawai_layout` | `Kamada_Kawai` | `nx.kamada_kawai_layout()` |
| `circular_layout` | `Circular` | `nx.circular_layout()` |
| `spiral_layout` | `Spiral` | `nx.spiral_layout()` |
| `random_layout` | `Random` | `nx.random_layout()` |
| `shell_layout` | `Shell` | `nx.shell_layout()` |
| `sorted_square_layout` | `Sorted_Square` | `custom_layouts/sorted_square_layout.py` |

A new layout is a function in `codecarto/models/custom_layouts/`, registered in
`PositionService.add_custom_layouts()` (`codecarto/services/position_service.py`).

---

## Logging

### Frontend Logger

```typescript
import { logger } from '../core/logger';

logger.debug('Detailed info', data);     // Development only
logger.info('General information');       // Informational
logger.warn('Warning message');           // Warnings
logger.error('Error occurred', error);    // Errors (always shown)
```

### Backend Logger

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed debugging info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

---

## Testing

```bash
uv run pytest tests -q            # the Python suite: pure Python, no browser or Node

cd web
npm run typecheck                 # tsc --noEmit over src and tests
npm run test:pure                 # DOM-free logic, under node --test
npm run test:state                # the state layer, under node --test
npm run test:rad                  # the radial menu: its core lint, build and conformance vectors
npm run test:families             # the corpus's families.json, when it is beside this clone (skips otherwise)
npm run test:e2e                  # Playwright, against servers it starts itself
npm run build                     # typecheck, then vite build
```

**Unset `MONGODB_URI` before running or timing the Python suite.** With it set
and no database listening, the suite waits on server selection and reports
minutes for work that takes under one.

**The browser tests start their own backend and dev server** on ports nobody's
default picks, and refuse to reuse a server they did not start;
`web/playwright.config.ts` says which and why. `tests/e2e/_identity.spec.ts`
asks the API what it is before any other spec believes it.

**A passing test is not evidence until it has been seen to fail.** After
writing a check, break the thing it names and confirm the check goes red; a
spec here names the mutation that breaks it beside the assertion it breaks.

**Test pattern:**
```python
def test_serialize_to_gjgf():
    """The serializer turns a graph into gJGF with its nodes and edges."""
    graph = nx.DiGraph()
    graph.add_node('A', label='Function A')
    graph.add_edge('A', 'B')

    options = PlotOptions(layout='Spectral', type='d3')
    gjgf = GraphSerializer.serialize_to_gjgf(graph, options)

    assert 'nodes' in gjgf
    assert 'edges' in gjgf
    assert len(gjgf['edges']) == 1
```

---

## Code Style Guidelines

### TypeScript

- **Components**: Mithril component objects with typed attrs
  ```typescript
  export const Component: m.Component<ComponentAttrs> = { view() {...} }
  ```
- **Avoid `any`**: use interfaces and type guards
- **Logger over console**: use the `logger` utility for logging
- **`import type` only for types**: a value imported with `import type` is
  erased; `vite build` alone compiles it without a word, and `npm run
  typecheck`, which `npm run build` runs first, refuses it

### Python

- **Async endpoints**: `async def` for FastAPI routes
- **Pydantic models**: for request and response validation
- **Type hints**: on every function signature
- **Dependencies through uv**: `uv add` changes `pyproject.toml` and `uv.lock`
  together; `uv sync` installs what the lock says

### CSS

- **Theme variables**: colours come from `var(--c-primary)` and its siblings in
  `web/src/styles/root/root.css`. Each theme redefines them -- `:root` is
  Terminal, black and green, and the application opens in Forest -- so a
  colour written into a stylesheet is right in one theme only.
- **BEM naming**: `.block__element--modifier`

---

## PR Checklist

- [ ] `uv run pytest tests -q` passes, with `MONGODB_URI` unset
- [ ] `npm run typecheck`, the unit suites and `npm run build` pass in `web/`
- [ ] `npm run test:e2e` passes, or each failure is named in the PR
- [ ] Each new check has been seen to fail
- [ ] `python governance/qm/project-seed/ci/run_workflows_locally.py` has run,
      and the PR says what it does not reproduce
- [ ] Documentation updated where behaviour changed
- [ ] The PR follows AGENTS.md: assigned to whoever asked for the work, no
      review requested, nothing merged by its author

---

## Resources

- [Mithril.js Documentation](https://mithril.js.org)
- [Golden Layout Documentation](https://golden-layout.github.io/golden-layout/)
- [D3.js Documentation](https://d3js.org)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [NetworkX Documentation](https://networkx.org)
- [uv Documentation](https://docs.astral.sh/uv/)
