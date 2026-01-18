# Frontend Modernization

> Complete history of frontend architecture improvements

## Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation Cleanup | ✅ Complete |
| 2 | State Refactoring | ✅ Complete |
| 3 | Component Library | ✅ Complete |
| 4 | Feature Modules | ✅ Complete |
| 5 | New Features | ✅ Complete |
| 6 | Testing Infrastructure | ✅ Setup Complete |

---

## Phase 1: Foundation Cleanup

### TypeScript Type Safety

Fixed 20+ `any` types:

- `request_handler.ts` - Created `RequestData` type
- `actions.ts` - Added type guards for runtime checking
- `nav.ts` - Changed `content: any` → `content: m.Children`
- `upload_nav.ts` - Properly typed event handlers
- `url_input.ts` - Properly typed keyboard/mouse events
- `file.ts` - Typed vnode parameter
- `index.ts` - Typed cells return type

### Logging Infrastructure

Created centralized logger:

```typescript
// web/src/core/logger.ts
export const logger = {
  debug: (msg, ...args) => { /* env-aware */ },
  info: (msg, ...args) => { /* always */ },
  warn: (msg, ...args) => { /* always */ },
  error: (msg, ...args) => { /* always */ },
};
```

Replaced ~21 console statements across:
- `plot_service.ts` (9)
- `repo_service.ts` (1)
- `demo_service.ts` (1)
- `state_controller.ts` (2)
- `graph_renderer.ts` (7)
- Feature module repo_service (1)

### Barrel Exports

Created index.ts files for clean imports:
- `web/src/core/index.ts`
- `web/src/services/index.ts`
- `web/src/state/index.ts`
- `web/src/features/*/index.ts`

---

## Phase 2: State Refactoring

### State Types

```typescript
// web/src/state/types.ts
export interface AppState {
  config: ConfigState;
  debug: DebugState;
  ui: UIState;
  repo: RepoState;
  local: LocalState;
  graph: GraphState;
}
```

### Selectors

```typescript
// web/src/state/selectors.ts
export const selectors = {
  hasRepoContent: (state) => state.repo.directory !== null,
  hasLocalFiles: (state) => state.local.files.length > 0,
  canPlotRepo: (state) => hasRepoContent(state) && !state.ui.isLoading,
  activeFile: (state) => state.repo.selectedFile ?? state.local.selectedFile,
};
```

### Action Creators

```typescript
// web/src/state/actions.ts
export class PlotActions {
  async loadDemo(): Promise<void>
  async plotUrlFile(url: string): Promise<void>
  async plotWholeRepo(content: Directory): Promise<void>
  async plotRepoDeps(content: Directory): Promise<void>
  async plotUploadedFile(file: RawFile): Promise<void>
}

export class RepoActions {
  async fetchRepository(url: string): Promise<void>
  selectFile(file: RawFile): void
  clearRepository(): void
}
```

---

## Phase 3: Component Library

### Form Components (`qm_comp_lib/form/`)

- `Input` - Text input with label, error state
- `Button` - Variants (default, primary, danger, ghost)
- `Select` - Dropdown with custom styling
- `Toggle` - Switch component
- `Textarea` - Multiline with character counter

### Feedback Components (`qm_comp_lib/feedback/`)

- `Loading` - Spinner with message, sizes, overlay mode
- `LoadingInline` - Inline dot animation
- `ErrorDisplay` - Error/warning/info with retry/dismiss
- `ErrorBoundary` - Catches errors in children
- `Toast` - Transient notifications

---

## Phase 4: Feature Modules

### Structure

```
web/src/features/
├── graph/
│   ├── components/
│   │   ├── Plot.ts
│   │   └── GraphControls.ts
│   ├── services/
│   │   └── graph_renderer.ts
│   ├── state/
│   │   ├── graph_state.ts
│   │   └── graph_actions.ts
│   └── index.ts
│
├── repository/
│   ├── components/
│   │   ├── UrlInput.ts
│   │   └── DirectoryNav.ts
│   ├── services/
│   │   └── repo_service.ts
│   ├── state/
│   │   ├── repo_state.ts
│   │   └── repo_actions.ts
│   └── index.ts
│
├── upload/
│   ├── components/
│   │   └── UploadNav.ts
│   ├── state/
│   │   ├── upload_state.ts
│   │   └── upload_actions.ts
│   └── index.ts
│
└── settings/
    ├── components/
    │   └── SettingsPanel.ts
    ├── state/
    │   ├── settings_state.ts
    │   └── settings_actions.ts
    └── index.ts
```

### Import Migration

Updated all imports to use feature modules:

```typescript
// Before
import { Plot } from './plot/plot';
import { GraphRenderer } from '../services/graph_renderer';

// After
import { Plot } from '../../features/graph';
import { GraphRenderer } from '../features/graph';
```

---

## Phase 5: New Features

### Client-Side Graph Rendering

- D3.js force-directed graph rendering
- Support for custom layouts
- Interactive zoom, pan, drag
- Proper TypeScript types for D3 simulation

### Graph Styling Controls (16 total)

**Layout**:
- Layout algorithm dropdown (8 options)
- Enable physics toggle
- Charge strength slider
- Link distance slider

**Nodes**:
- Show labels toggle
- Size slider (px)
- Opacity slider
- Border width slider

**Edges**:
- Show labels toggle
- Width slider (px)
- Opacity slider

**Labels**:
- Font size slider (px)
- Color picker

### Animation System

```typescript
// web/src/core/animations.ts
export const animations = {
  fadeIn: (target, options?) => anime({...}),
  fadeOut: (target, options?) => anime({...}),
  slideNav: (target, isOpen, side) => anime({...}),
  staggerIn: (target, options?) => anime({...}),
  buttonPress: (target) => anime({...}),
  shake: (target) => anime({...}),
};
```

### Interactive Graph System

- 4 interaction profiles (Standard, CAD, Gaming, Touch)
- Context-aware radial menu
- Keyboard navigation
- Touch gestures
- Multi-select with visual feedback

---

## Phase 6: Testing Infrastructure

### Backend (pytest)

```bash
pytest
pytest --cov=codecarto --cov-report=html
pytest tests/services/test_graph_serializer.py
```

### Frontend (Playwright)

```bash
npm run test:e2e
npm run test:e2e:ui
npx playwright test graph-visualization.spec.ts
```

### Test Patterns Documented

Backend:
```python
def test_serialize_to_gjgf():
    graph = nx.DiGraph()
    graph.add_node('A', label='Function A')
    # ...
    assert 'nodes' in gjgf
```

Frontend E2E:
```typescript
test('loads demo visualization', async ({ page }) => {
  await page.goto('/');
  await page.click('.control-panel__toggle');
  // ...
  await expect(svg).toBeVisible();
});
```

---

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Feature modules | 0 | 4 |
| Console statements | ~21 | 0 |
| TypeScript `any` | ~31 | ~11 |
| Logger calls | 0 | 21 |
| Barrel exports | 2 | 7 |

---

## Key Decisions

### Feature-Based vs Type-Based Structure

**Chose feature-based** because:
- Related code grouped together
- Easier navigation
- Better scalability
- Clear boundaries between features

### pytest + Playwright vs Vitest

**Chose pytest + Playwright** because:
- pytest is standard Python testing
- Playwright provides real browser testing
- Better integration with existing backend
- More comprehensive E2E coverage

### Mithril Component Objects vs Functions

**Standardized on component objects**:
```typescript
// Preferred
export const Component: m.Component<Attrs> = {
  view(vnode) { return m('div', ...); }
};

// Avoid
export const Component = (attrs) => m('div', ...);
```

Benefits:
- Proper lifecycle hooks
- Type inference works better
- Consistent pattern across codebase
