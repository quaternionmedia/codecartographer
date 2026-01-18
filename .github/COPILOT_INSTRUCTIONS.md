# Code Cartographer - AI Assistant Instructions

> Consolidated guide for AI assistants working on this codebase

## Project Overview

**Code Cartographer** is a source code visualization tool that parses Python code and generates interactive graph visualizations of code structure, dependencies, and AST relationships.

- **Version**: 0.3.0
- **License**: MIT
- **Stack**: Python (FastAPI) backend + TypeScript (Mithril.js) frontend

## Architecture

```
Backend (Python/FastAPI)  →  Graph Generation (NetworkX)  →  Frontend (Mithril/D3.js)
     ↓                              ↓                              ↓
  Parse code              Create dependency graphs        Render interactive viz
```

## Quick Start

```bash
# Development (backend + frontend)
uv run codecarto dev

# Backend only
uv run codecarto serve

# Local repo analysis
uv run codecarto repo scan .
uv run codecarto repo graph . -t ast
```

## Directory Structure

```
codecartographer/
├── codecarto/                    # Python backend
│   ├── cli.py                    # CLI commands
│   ├── main.py                   # FastAPI app
│   ├── routers/                  # API endpoints
│   │   └── plotter_router.py     # Graph visualization endpoints
│   ├── services/                 # Business logic
│   │   ├── graph_serializer.py   # NetworkX → JSON
│   │   ├── parser_service.py     # Code parsing orchestration
│   │   └── parsers/              # AST/dependency parsers
│   └── models/                   # Pydantic data models
│
├── web/                          # TypeScript frontend
│   ├── src/
│   │   ├── features/             # Feature modules
│   │   │   ├── graph/            # Visualization feature
│   │   │   │   ├── components/   # Plot, GraphControls
│   │   │   │   ├── services/     # graph_renderer.ts
│   │   │   │   ├── state/        # graph_state, actions
│   │   │   │   └── index.ts      # Barrel export
│   │   │   ├── repository/       # GitHub integration
│   │   │   ├── upload/           # File upload
│   │   │   └── settings/         # App settings
│   │   ├── components/           # Shared/legacy components
│   │   ├── services/             # Shared services
│   │   ├── state/                # Global state
│   │   └── core/                 # Utilities (logger, animations)
│   └── package.json
│
├── docs/                         # User documentation
└── .github/                      # AI assistant & dev documentation
    ├── COPILOT_INSTRUCTIONS.md   # This file
    ├── CONTRIBUTING.md           # Development patterns
    └── development/              # Session logs & history
```

## Key Technologies

### Backend
- **FastAPI** - Web framework
- **NetworkX** - Graph library
- **Click** - CLI framework
- **Pydantic** - Data validation
- **UV** - Package manager

### Frontend
- **Mithril.js** - UI framework
- **Meiosis** - State management pattern
- **D3.js** - Graph rendering
- **Vite** - Build tool
- **TypeScript** - Language

## Data Flow

### Backend API → Frontend
```typescript
// Backend returns gJGF (Graph JSON Format)
{
  graph: {
    nodes: Record<string, { id, label, color, size, x?, y? }>,
    edges: Array<{ source, target, label?, color? }>
  },
  metadata: {
    layout: string,
    type: string,
    nodeCount: number,
    edgeCount: number
  }
}
```

### Frontend State Management
```typescript
// Feature module pattern
features/graph/
├── state/
│   ├── graph_state.ts      // State interface
│   └── graph_actions.ts    // Action creators
└── components/
    └── Plot.ts             // Mithril component
```

### Graph Rendering Pipeline
```
API Response → PlotActions.handlePlotData() → GraphRenderer.renderD3() → DOM
```

## Common Patterns

### Backend: Add API Endpoint
```python
@PlotterRouter.post("/endpoint")
async def my_endpoint(options: PlotOptions) -> dict:
    graph = await ParserService.parse_something()
    gjgf = GraphSerializer.serialize_to_gjgf(graph, options.layout)
    return generate_return(results={"graph": gjgf, "metadata": {...}})
```

### Frontend: Create Feature Module
```typescript
// 1. State interface
export interface FeatureState { ... }

// 2. Action creators
export const featureActions = {
  update: (data) => (state) => ({ ...state, data }),
};

// 3. Component
export const Component: m.Component<Attrs> = {
  view(vnode) { return m('div', vnode.attrs.content); }
};

// 4. Barrel export
export { Component } from './components/Component';
export { featureActions } from './state/feature_actions';
```

### Logging
```typescript
import { logger } from '../core/logger';

logger.debug('Detailed info for development');
logger.info('General information');
logger.warn('Warning message');
logger.error('Error occurred', error);
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/plotter/file` | POST | Plot single file graph |
| `/plotter/url` | POST | Plot file from GitHub URL |
| `/plotter/whole_repo` | POST | Plot directory tree |
| `/plotter/whole_repo_deps` | POST | Plot dependency graph |
| `/repo/tree` | GET | Fetch GitHub repo structure |
| `/local/scan` | GET | Scan local repository |

## Development Workflow

### Frontend Changes
```bash
cd web
npm run dev          # Vite dev server (hot reload)
```

### Backend Changes
```bash
uv run codecarto dev # Backend + frontend
# or
uv run codecarto serve --reload  # Backend only with reload
```

### Full Stack Testing
```bash
# Terminal 1: Backend
uv run codecarto serve --reload

# Terminal 2: Frontend
cd web && npm run dev

# Browser: http://localhost:1234
```

## Code Quality Standards

### TypeScript
- Use Mithril component objects: `m.Component<Attrs>`
- Avoid `any` types - use proper interfaces
- Prefer functional patterns for state updates
- Use logger instead of console.log

### Python
- Follow FastAPI async patterns
- Use Pydantic models for validation
- Type hints required
- Use logger instead of print

### File Organization
- Feature modules: group by feature (graph, repo, upload)
- Shared code: in `services/`, `components/qm_comp_lib/`
- Each feature has: components/, services/, state/, index.ts

## Testing Strategy

### Backend
```bash
pytest                           # Unit tests
pytest tests/test_graph_serializer.py
```

### Frontend E2E
```bash
playwright test                  # Browser tests
playwright test --headed         # Watch tests
```

## Troubleshooting

### Common Issues

**Vite build errors**
- Check import paths (use feature module paths)
- Ensure CSS files exist at correct paths
- Clear `node_modules` and reinstall

**Backend 500 errors**
- Check backend logs for Python exceptions
- Verify NetworkX graph structure
- Check GraphSerializer output format

**Graph not rendering**
- Check browser console for errors
- Verify API response format (should be gJGF)
- Check D3.js container dimensions

## Resources

- **Mithril Docs**: https://mithril.js.org
- **D3.js Docs**: https://d3js.org
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **NetworkX Docs**: https://networkx.org

---

**Last Updated**: 2026-01-17
**Current Branch**: `uv-refactor`
