# Extending CodeCartographer

Guide for adding new renderers, parsers, and styling options.

---

## Adding a New Renderer

### Step 1: Create Renderer Class

Create a new file in `web/src/features/graph/services/`:

```typescript
// my_renderer.ts
import { IGraphRenderer } from './base_renderer';
import { GraphStylingOptions } from '../../../state/types';

export class MyRenderer implements IGraphRenderer {
  readonly type = 'myrenderer';
  readonly name = 'My Custom Renderer';

  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void {
    // Clear container
    container.innerHTML = '';

    // Your rendering logic here
    // Use data.graph.nodes and data.graph.edges
  }

  canHandle(data: unknown): boolean {
    // Return true if this renderer can handle the data format
    if (!data || typeof data !== 'object') return false;
    return 'graph' in data && 'nodes' in (data as any).graph;
  }

  cleanup(): void {
    // Clean up any resources (event listeners, etc.)
  }
}
```

### Step 2: Register Renderer

In `web/src/features/graph/services/renderers.ts`:

```typescript
import { MyRenderer } from './my_renderer';

// Add to registrations
GraphRendererRegistry.register('myrenderer', () => new MyRenderer());
```

### Step 3: Update Types

In `web/src/state/types.ts`:

```typescript
export type GraphRendererType = 'd3' | 'gravis' | 'notebook' | 'myrenderer';
```

### Step 4: Add UI Option

In `web/src/components/codecarto/control_panel/control_panel.ts`, find the renderer select and add:

```typescript
m('option', { value: 'myrenderer' }, 'My Custom Renderer'),
```

---

## Adding a New Parser

### Step 1: Create Parser Class

Create in `codecarto/services/parsers/`:

```python
# my_parser.py
import networkx as nx

class MyParser:
    def __init__(self):
        pass

    def parse(self, source) -> nx.DiGraph:
        """
        Parse source and return NetworkX directed graph.

        Args:
            source: Input data (Directory, File, etc.)

        Returns:
            NetworkX DiGraph with nodes and edges
        """
        G = nx.DiGraph()

        # Add nodes
        G.add_node('node1', label='Node 1', type='my_type')

        # Add edges
        G.add_edge('node1', 'node2', label='relationship')

        return G
```

### Step 2: Register in ParserService

In `codecarto/services/parser_service.py`:

```python
from codecarto.services.parsers.my_parser import MyParser

class ParserService:
    @staticmethod
    async def parse_my_format(source) -> nx.DiGraph:
        parser = MyParser()
        return parser.parse(source)
```

### Step 3: Add Route Option

In `codecarto/routers/plotter_router.py`:

```python
if options.parse_by == "my_format":
    graph = await ParserService.parse_my_format(source)
```

### Step 4: Update Frontend Types

In `web/src/state/types.ts`:

```typescript
export type ParserMode = 'ast' | 'directory' | 'dependencies' | 'my_format';
```

### Step 5: Add UI Option

In control panel parse mode section, add button for new parser mode.

---

## Adding a New Styling Option

### Step 1: Add to Schema

In `web/src/features/graph/config/styling_schema.ts`:

```typescript
{
  key: 'myOption',
  label: 'My Option',
  type: 'range',  // or 'color', 'boolean', 'select'
  category: 'node',  // or 'edge', 'label', 'physics', 'canvas'
  default: 10,
  min: 0,
  max: 100,
  step: 5,
  description: 'Description of what this option does',
},
```

### Step 2: Update Interface

In `web/src/state/types.ts`:

```typescript
export interface GraphStylingOptions {
  // ... existing options
  myOption?: number;
}
```

### Step 3: Add Default Value

In `web/src/state/cell_state.ts`:

```typescript
public graphStyling: GraphStylingOptions = {
  // ... existing defaults
  myOption: 10,
};
```

### Step 4: Apply in Renderer

In `web/src/features/graph/services/graph_renderer.ts`:

```typescript
// Use the option when rendering
.attr('some-attribute', styling.myOption || 10)
```

### Step 5: Add UI Control (if not using schema-driven UI)

In control panel, add input control that calls:

```typescript
callbacks.onGraphStylingChange({ myOption: newValue });
```

---

## Adding a New Graph Extension

Extensions add interactivity to the D3 renderer.

### Step 1: Create Extension

In `web/src/features/graph/extensions/`:

```typescript
// my_extension.ts
import { ExtensionContext } from './index';

export class MyExtension {
  private context: ExtensionContext;

  constructor(context: ExtensionContext) {
    this.context = context;
  }

  init(): void {
    // Set up event listeners, etc.
  }

  myMethod(): void {
    // Extension functionality
  }

  cleanup(): void {
    // Remove listeners, etc.
  }
}
```

### Step 2: Register Extension

In `web/src/features/graph/extensions/index.ts`:

```typescript
export { MyExtension } from './my_extension';
```

### Step 3: Use in Renderer

In `graph_renderer.ts`:

```typescript
import { MyExtension } from '../extensions';

// In render function
const myExtension = new MyExtension(context);
myExtension.init();
```

---

## Adding a Backend Endpoint

### Step 1: Create Router Function

In appropriate router file (e.g., `plotter_router.py`):

```python
@PlotterRouter.post("/my-endpoint")
async def my_endpoint(data: MyModel, options: PlotOptions) -> dict:
    try:
        result = await MyService.process(data, options)
        return generate_return(results=result)
    except Exception as e:
        return proc_exception("my_endpoint", "Error message", {}, e)
```

### Step 2: Create Service (if needed)

In `codecarto/services/`:

```python
# my_service.py
class MyService:
    @staticmethod
    async def process(data, options):
        # Business logic
        return {"key": "value"}
```

### Step 3: Add Frontend Service Method

In `web/src/services/`:

```typescript
public static async myMethod(url: string, data: any): Promise<unknown> {
  const response = await fetch(`${url}/my-endpoint`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return response.json();
}
```

---

## Testing Changes

1. **Build frontend**: `cd web && npm run build`
2. **Run backend**: `uv run codecarto`
3. **Run frontend dev**: `cd web && npm run dev`
4. **Test in browser**: Navigate to localhost:1234
