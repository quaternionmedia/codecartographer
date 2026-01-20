# Adding a New Graph Renderer

This guide shows how to add a new visualization library to the renderer system.

## Example: Adding Cytoscape.js Renderer

Let's walk through adding [Cytoscape.js](https://js.cytoscape.org/) as a new renderer option.

### Step 1: Install Dependencies

```bash
cd web
npm install cytoscape
npm install --save-dev @types/cytoscape
```

### Step 2: Create Renderer Class

Create `web/src/features/graph/services/cytoscape_renderer.ts`:

```typescript
import cytoscape from 'cytoscape';
import { IGraphRenderer } from './base_renderer';
import { GraphData } from './graph_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

/**
 * Cytoscape.js graph renderer
 * Renders interactive graphs using Cytoscape.js library
 */
export class CytoscapeGraphRenderer implements IGraphRenderer {
  readonly type = 'cytoscape';
  readonly name = 'Cytoscape.js Graph Renderer';

  private cytoscapeInstance: cytoscape.Core | null = null;

  /**
   * Render graph using Cytoscape.js
   */
  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void {
    if (!this.canHandle(data)) {
      throw new Error('CytoscapeGraphRenderer: Invalid data format');
    }

    const graphData = data as GraphData;
    logger.debug('CytoscapeGraphRenderer.render - rendering graph');

    // Clear container
    container.innerHTML = '';

    // Convert gJGF to Cytoscape format
    const cytoscapeData = this.convertToCytoscape(graphData);

    // Create Cytoscape instance
    this.cytoscapeInstance = cytoscape({
      container: container,
      elements: cytoscapeData,
      style: this.getStyles(styling),
      layout: {
        name: this.getLayoutName(graphData.metadata.layout),
        animate: true,
        animationDuration: 500
      },
      // Enable interactions
      wheelSensitivity: 0.2,
      minZoom: 0.1,
      maxZoom: 10
    });

    // Add event listeners
    this.addEventListeners();

    logger.debug('CytoscapeGraphRenderer: Rendering complete');
  }

  /**
   * Check if data is in gJGF format
   */
  canHandle(data: unknown): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }

    const obj = data as Record<string, unknown>;

    // Check for gJGF format with cytoscape type
    if ('graph' in obj && 'metadata' in obj) {
      const metadata = obj.metadata as Record<string, unknown>;

      // Only handle if explicitly marked for cytoscape
      // (Otherwise D3 will handle it)
      return metadata.type === 'cytoscape';
    }

    return false;
  }

  /**
   * Convert gJGF to Cytoscape elements format
   */
  private convertToCytoscape(graphData: GraphData): cytoscape.ElementDefinition[] {
    const elements: cytoscape.ElementDefinition[] = [];

    // Convert nodes
    const nodes = Array.isArray(graphData.graph.nodes)
      ? graphData.graph.nodes
      : Object.values(graphData.graph.nodes);

    nodes.forEach(node => {
      elements.push({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label || node.id,
          ...node
        },
        position: node.x && node.y ? { x: node.x, y: node.y } : undefined
      });
    });

    // Convert edges
    graphData.graph.edges.forEach((edge, index) => {
      elements.push({
        group: 'edges',
        data: {
          id: `edge-${index}`,
          source: typeof edge.source === 'string' ? edge.source : edge.source.id,
          target: typeof edge.target === 'string' ? edge.target : edge.target.id,
          label: edge.label,
          ...edge
        }
      });
    });

    return elements;
  }

  /**
   * Get Cytoscape styles from GraphStylingOptions
   */
  private getStyles(styling?: GraphStylingOptions): cytoscape.Stylesheet[] {
    const nodeSize = styling?.nodeSize || 20;
    const edgeWidth = styling?.edgeWidth || 2;
    const labelColor = styling?.labelColor || '#00ff41';

    return [
      {
        selector: 'node',
        style: {
          'background-color': '#00ff41',
          'label': 'data(label)',
          'width': nodeSize,
          'height': nodeSize,
          'font-size': '10px',
          'color': labelColor,
          'text-valign': 'center',
          'text-halign': 'center'
        }
      },
      {
        selector: 'edge',
        style: {
          'width': edgeWidth,
          'line-color': '#666',
          'target-arrow-color': '#666',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': '8px',
          'color': labelColor
        }
      },
      {
        selector: ':selected',
        style: {
          'background-color': '#ffff00',
          'line-color': '#ffff00',
          'target-arrow-color': '#ffff00'
        }
      }
    ];
  }

  /**
   * Map layout names from backend to Cytoscape
   */
  private getLayoutName(backendLayout: string): string {
    const mapping: Record<string, string> = {
      'Spring': 'cose',
      'Spectral': 'circle',
      'Kamada_Kawai': 'cose',
      'Circular': 'circle',
      'Random': 'random',
      'Grid': 'grid'
    };
    return mapping[backendLayout] || 'cose';
  }

  /**
   * Add interaction event listeners
   */
  private addEventListeners(): void {
    if (!this.cytoscapeInstance) return;

    // Node click
    this.cytoscapeInstance.on('tap', 'node', (event) => {
      const node = event.target;
      logger.debug('Node clicked:', node.data());
    });

    // Edge click
    this.cytoscapeInstance.on('tap', 'edge', (event) => {
      const edge = event.target;
      logger.debug('Edge clicked:', edge.data());
    });

    // Background click (deselect)
    this.cytoscapeInstance.on('tap', (event) => {
      if (event.target === this.cytoscapeInstance) {
        this.cytoscapeInstance!.elements().unselect();
      }
    });
  }

  /**
   * Cleanup Cytoscape instance
   */
  cleanup(): void {
    if (this.cytoscapeInstance) {
      this.cytoscapeInstance.destroy();
      this.cytoscapeInstance = null;
    }
  }
}
```

### Step 3: Register Renderer

Update `web/src/features/graph/services/renderers.ts`:

```typescript
// Add import
import { CytoscapeGraphRenderer } from './cytoscape_renderer';

// Add export
export { CytoscapeGraphRenderer } from './cytoscape_renderer';

// Register in initializeRenderers()
function initializeRenderers(): void {
  GraphRendererRegistry.register('notebook', () => new NotebookGraphRenderer());
  GraphRendererRegistry.register('d3', () => new D3GraphRenderer());
  GraphRendererRegistry.register('gravis', () => new GravisGraphRenderer());

  // Add this line
  GraphRendererRegistry.register('cytoscape', () => new CytoscapeGraphRenderer());

  GraphRendererRegistry.setDefault('d3');
}
```

### Step 4: Use the New Renderer

#### Option A: Via Backend Metadata

Update backend to return `type: 'cytoscape'`:

```python
# codecarto/services/graph_serializer.py
metadata = {
    "type": "cytoscape",  # Use cytoscape renderer
    "layout": "Spring",
    ...
}
```

#### Option B: Via Frontend Code

```typescript
// Explicit selection
const renderer = GraphRendererRegistry.get('cytoscape');
renderer.render(container, graphData, stylingOptions);

// Or set as default
GraphRendererRegistry.setDefault('cytoscape');
```

### Step 5: Test

```bash
cd web
npm run build
npm run dev
```

Then:
1. Upload a file or import a repo
2. Backend returns `metadata.type === 'cytoscape'`
3. Cytoscape renderer is automatically selected
4. Graph renders with Cytoscape.js

## Template for Any Renderer

```typescript
import { IGraphRenderer } from './base_renderer';
import { GraphStylingOptions } from '../../../state/types';
import { logger } from '../../../core/logger';

export class MyCustomRenderer implements IGraphRenderer {
  readonly type = 'my-renderer';
  readonly name = 'My Custom Renderer';

  render(
    container: HTMLElement,
    data: unknown,
    styling?: GraphStylingOptions
  ): void {
    // 1. Validate data
    if (!this.canHandle(data)) {
      throw new Error('Invalid data format');
    }

    // 2. Clear container
    container.innerHTML = '';

    // 3. Convert data to your library's format
    const convertedData = this.convertData(data);

    // 4. Initialize your library
    this.initializeLibrary(container, convertedData, styling);

    // 5. Add interactions
    this.addEventListeners();

    logger.debug('MyCustomRenderer: Complete');
  }

  canHandle(data: unknown): boolean {
    // Detection logic - what data formats can this renderer handle?

    // Option 1: Check for specific property
    return typeof data === 'object' && data !== null && 'myFormat' in data;

    // Option 2: Check metadata type
    // const obj = data as Record<string, unknown>;
    // return obj.metadata?.type === 'my-renderer';
  }

  private convertData(data: unknown): any {
    // Convert input data to your library's format
    return data;
  }

  private initializeLibrary(
    container: HTMLElement,
    data: any,
    styling?: GraphStylingOptions
  ): void {
    // Initialize your visualization library
  }

  private addEventListeners(): void {
    // Add interaction handlers
  }

  cleanup?(): void {
    // Clean up resources (optional)
  }
}
```

## Checklist

When adding a new renderer:

- [ ] Install library dependencies
- [ ] Create renderer class implementing `IGraphRenderer`
- [ ] Implement `render()` method
- [ ] Implement `canHandle()` detection logic
- [ ] Implement data conversion if needed
- [ ] Add event listeners for interactions
- [ ] Implement `cleanup()` if needed
- [ ] Export renderer from `renderers.ts`
- [ ] Register renderer in `initializeRenderers()`
- [ ] Test with sample data
- [ ] Update documentation
- [ ] Add to README.md

## Common Patterns

### Pattern 1: Explicit Type Detection

```typescript
canHandle(data: unknown): boolean {
  const obj = data as Record<string, unknown>;
  return obj.metadata?.type === 'my-renderer';
}
```

**Use When**: You want explicit control over when renderer is used

### Pattern 2: Format Detection

```typescript
canHandle(data: unknown): boolean {
  return typeof data === 'object' &&
         data !== null &&
         'specificProperty' in data;
}
```

**Use When**: Your library has a unique data format

### Pattern 3: Fallback Detection

```typescript
canHandle(data: unknown): boolean {
  // Accept gJGF format but only if type matches
  const obj = data as Record<string, unknown>;
  return 'graph' in obj &&
         'metadata' in obj &&
         obj.metadata?.type === 'my-renderer';
}
```

**Use When**: You share a data format with other renderers

## Best Practices

### 1. Keep Detection Specific

❌ **Bad** - Too broad, conflicts with D3:
```typescript
canHandle(data: unknown): boolean {
  return typeof data === 'object' && 'graph' in data;
}
```

✅ **Good** - Specific to your renderer:
```typescript
canHandle(data: unknown): boolean {
  return data.metadata?.type === 'my-renderer';
}
```

### 2. Handle Styling Options

```typescript
render(container, data, styling) {
  const nodeSize = styling?.nodeSize || DEFAULT_SIZE;
  const edgeWidth = styling?.edgeWidth || DEFAULT_WIDTH;
  // Use these values in your renderer
}
```

### 3. Clean Up Resources

```typescript
cleanup(): void {
  // Stop animations
  // Remove event listeners
  // Destroy library instances
  // Free memory
}
```

### 4. Log Appropriately

```typescript
logger.debug('Detailed info for debugging');
logger.info('Important user-facing info');
logger.warn('Something unexpected');
logger.error('Critical errors');
```

### 5. Error Handling

```typescript
render(container, data, styling) {
  try {
    // Rendering logic
  } catch (error) {
    logger.error('Render failed:', error);
    container.innerHTML = `
      <div style="padding: 20px; color: red;">
        Failed to render: ${error.message}
      </div>
    `;
  }
}
```

## Examples of Libraries to Add

Potential candidates for new renderers:

- **Three.js** - 3D force-directed graphs
- **vis.js** - Alternative 2D network visualization
- **Sigma.js** - High-performance graph rendering
- **G6** - AntV graph visualization
- **ECharts** - Apache ECharts graph module
- **Graphviz** - DOT language rendering
- **Mermaid** - Diagram and flowchart rendering

Each would follow the same pattern shown above.
