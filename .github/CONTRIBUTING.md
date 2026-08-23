# Contributing to Code Cartographer

> Development patterns, workflows, and best practices

## Getting Started

### Prerequisites

- Python 3.10+
- [UV](https://github.com/astral-sh/uv) package manager
- Node.js 18+ (for frontend)
- Docker (optional, for database)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/quaternionmedia/codecartographer.git
cd codecartographer
git submodule init && git submodule update

# Create virtual environment with uv
uv venv

# Activate virtual environment
# Windows (Git Bash):
source .venv/Scripts/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Install frontend dependencies
cd web && npm install && cd ..
```

## CLI Commands

```bash
# Show all available commands
uv run codecarto --help

# Development (backend + frontend)
uv run codecarto dev

# Backend only
uv run codecarto serve

# Frontend only
uv run codecarto web

# Local repo analysis
uv run codecarto repo scan .
uv run codecarto repo graph . -t ast
```

---

## Architecture Overview

### Frontend Structure

The frontend combines a feature-based module architecture
(`web/src/features/`) with Golden Layout as the primary application
shell (`web/src/layout/` — dock panel registry, layout persistence).
See `docs/architecture.md` for the current, authoritative structure;
the feature-module shape below still holds for the graph/repository/
upload/settings features themselves, just wrapped by the GL shell now
rather than the older fixed-tab control panel:

```
web/src/features/
├── graph/                   # Graph visualization feature
│   ├── components/
│   │   └── Plot.ts          # Main visualization container
│   ├── services/
│   │   └── graph_renderer.ts
│   ├── state/
│   │   ├── graph_state.ts   # State interface
│   │   └── graph_actions.ts # Action creators
│   └── index.ts             # Barrel export
│
├── repository/              # GitHub repository feature
│   ├── components/
│   │   ├── UrlInput.ts
│   │   └── DirectoryNav.ts
│   ├── services/
│   │   └── repo_service.ts
│   └── state/
│
├── upload/                  # File upload feature
└── settings/                # Settings feature
```

### State Management Pattern

Each feature module exports a consistent interface:

```typescript
// State interface
export interface GraphState {
  content: m.Vnode[];
  isRendering: boolean;
  options: GraphOptions;
  metadata: GraphMetadata | null;
}

// Action creators (functional pattern)
export const graphActions = {
  setContent: (content: m.Vnode[]) => (state: GraphState) => ({
    ...state,
    content,
  }),
  setOptions: (options: Partial<GraphOptions>) => (state: GraphState) => ({
    ...state,
    options: { ...state.options, ...options },
  }),
};
```

---

## Development Patterns

### Adding a New Feature Module

1. **Create directory structure**:
```
features/new-feature/
├── components/
├── services/
├── state/
└── index.ts
```

2. **Define state interface** (`state/new-feature_state.ts`):
```typescript
export interface NewFeatureState {
  data: SomeData | null;
  isLoading: boolean;
}

export const DEFAULT_NEW_FEATURE_STATE: NewFeatureState = {
  data: null,
  isLoading: false,
};
```

3. **Create action creators** (`state/new-feature_actions.ts`):
```typescript
export const newFeatureActions = {
  setData: (data: SomeData) => (state: NewFeatureState) => ({
    ...state,
    data,
    isLoading: false,
  }),
  setLoading: (isLoading: boolean) => (state: NewFeatureState) => ({
    ...state,
    isLoading,
  }),
};
```

4. **Create components** (`components/Component.ts`):
```typescript
interface ComponentAttrs {
  state: NewFeatureState;
  onAction: () => void;
}

export const Component: m.Component<ComponentAttrs> = {
  view(vnode) {
    const { state, onAction } = vnode.attrs;
    return m('div.component', [
      m('button', { onclick: onAction }, 'Action'),
      state.isLoading && m('span', 'Loading...'),
    ]);
  }
};
```

5. **Create barrel export** (`index.ts`):
```typescript
export { Component } from './components/Component';
export { newFeatureActions } from './state/new-feature_actions';
export type { NewFeatureState } from './state/new-feature_state';
export { DEFAULT_NEW_FEATURE_STATE } from './state/new-feature_state';
```

### Adding Backend API Endpoints

```python
from fastapi import APIRouter
from codecarto.models.plot_data import PlotOptions
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.util.utilities import generate_return

Router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@Router.post("/endpoint")
async def my_endpoint(options: PlotOptions) -> dict:
    """Process request and return graph data."""
    # Parse/process
    graph = await some_service_call()
    
    # Serialize to gJGF
    gjgf = GraphSerializer.serialize_to_gjgf(graph, options.layout)
    
    # Return standardized response
    return generate_return(
        results={
            "graph": gjgf,
            "metadata": {
                "nodeCount": graph.number_of_nodes(),
                "edgeCount": graph.number_of_edges(),
            }
        }
    )
```

---

## Graph Styling System

### GraphStylingOptions Interface

```typescript
export interface GraphStylingOptions {
  // Layout Algorithm
  layout: string;            // 'spring_layout', 'spectral_layout', etc.

  // Physics Simulation
  enablePhysics: boolean;    // Enable D3 force simulation
  chargeStrength: number;    // Node repulsion (-500 to -10)
  linkDistance: number;      // Target edge length (10-300px)

  // Node Appearance
  nodeSize: number;          // Radius in pixels (2-30px)
  nodeOpacity: number;       // 0.0 to 1.0
  nodeBorderWidth: number;   // Stroke width (0-8px)

  // Edge Appearance
  edgeWidth: number;         // Line width (0.5-10px)
  edgeOpacity: number;       // 0.0 to 1.0

  // Label Appearance
  showNodeLabels: boolean;
  showEdgeLabels: boolean;
  labelSize: number;         // Font size in pixels (6-24px)
  labelColor: string;        // Hex color
}
```

### Layout Algorithm Mapping

| Frontend Value | Backend Value | NetworkX Function |
|----------------|---------------|-------------------|
| `spring_layout` | `Spring` | `nx.spring_layout()` |
| `spectral_layout` | `Spectral` | `nx.spectral_layout()` |
| `kamada_kawai_layout` | `Kamada_Kawai` | `nx.kamada_kawai_layout()` |
| `circular_layout` | `Circular` | `nx.circular_layout()` |
| `spiral_layout` | `Spiral` | `nx.spiral_layout()` |
| `random_layout` | `Random` | `nx.random_layout()` |
| `shell_layout` | `Shell` | `nx.shell_layout()` |
| `sorted_square_layout` | `Sorted_Square` | Custom implementation |

---

## Logging

### Frontend Logger

```typescript
import { logger } from '../core/logger';

// Use appropriate log levels
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

### Backend Testing (pytest)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=codecarto --cov-report=html

# Run specific test file
pytest tests/services/test_graph_serializer.py
```

**Test Pattern**:
```python
def test_serialize_to_gjgf():
    """Test graph serialization to gJGF format."""
    graph = nx.DiGraph()
    graph.add_node('A', label='Function A')
    graph.add_edge('A', 'B')

    options = PlotOptions(layout='Spectral', type='d3')
    gjgf = GraphSerializer.serialize_to_gjgf(graph, options)

    assert 'nodes' in gjgf
    assert 'edges' in gjgf
    assert len(gjgf['edges']) == 1
```

No frontend E2E test tooling exists in this repo today — `web/
package.json` has no test script and no Playwright (or similar)
dependency. `npm run build` (`vite build`) is the frontend's only
automated check; verify UI changes by actually running the app.

---

## Code Style Guidelines

### TypeScript

- **Components**: Use Mithril component objects with typed attrs
  ```typescript
  export const Component: m.Component<ComponentAttrs> = { view() {...} }
  ```
- **Avoid `any`**: Use proper interfaces and type guards
- **Functional state**: Use action creators that return state transforms
- **Logger over console**: Use `logger` utility for all logging

### Python

- **Async endpoints**: Use `async def` for FastAPI routes
- **Pydantic models**: Use for request/response validation
- **Type hints**: Required for all function signatures
- **UV package manager**: Use `uv pip install` for dependencies

### CSS

- **Terminal theme**: Black background (#0a0a0a), green accents (#00ff00)
- **BEM naming**: `.block__element--modifier`
- **CSS variables**: Use `var(--c-primary)` etc from root.css

---

## PR Checklist

- [ ] TypeScript compiles without errors
- [ ] Python type hints present
- [ ] Logger used instead of console/print
- [ ] Feature module pattern followed (if adding feature)
- [ ] Tests added/updated
- [ ] Documentation updated if needed

---

## Resources

- [Mithril.js Documentation](https://mithril.js.org)
- [D3.js Documentation](https://d3js.org)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [NetworkX Documentation](https://networkx.org)
- [UV Package Manager](https://github.com/astral-sh/uv)
