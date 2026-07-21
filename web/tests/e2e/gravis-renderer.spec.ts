import { test, expect } from '@playwright/test';

/**
 * GravisGraphRenderer (vis-network) has no UI path reachable from the
 * default panel layout in this test environment — the Renderer dropdown
 * lives in control_panel.ts's "Graph" tab, gated behind panel-navigation
 * state that wasn't reproducible via automated clicking. Rather than
 * skip coverage entirely, this calls the renderer directly via Vite's
 * dev module graph (`import()` of its real source file, transpiled
 * on-the-fly like any other module) against synthetic gJGF data —
 * exercising the actual rendering logic without depending on which
 * panel happens to be open.
 */
test('GravisGraphRenderer renders real gJGF data to a non-blank canvas', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));

  await page.goto('/');
  await page.waitForTimeout(500);
  errors.length = 0;

  const result = await page.evaluate(async () => {
    // Absolute Vite-dev-server URL, resolved in the browser at runtime --
    // not a real module specifier tsc can resolve against this file.
    // @ts-expect-error -- see comment above
    const mod = await import('/features/graph/services/gravis_renderer.ts');
    const { GravisGraphRenderer } = mod as any;

    const container = document.createElement('div');
    container.style.width = '800px';
    container.style.height = '600px';
    document.body.appendChild(container);

    const gjgfData = {
      graph: {
        nodes: {
          a: { label: 'A', metadata: { color: '#ff0000', shape: 'circle', x: 0, y: 0, size: 40 } },
          b: { label: 'B', metadata: { color: '#00ff00', shape: 'square', x: 100, y: 100, size: 20 } },
          c: { label: 'C', metadata: { color: '#0000ff', shape: 'diamond', x: 200, y: 0, size: 10 } },
        },
        edges: [
          { source: 'a', target: 'b', label: 'contains' },
          { source: 'b', target: 'c', label: 'calls' },
        ],
        directed: true,
      },
      metadata: { layout: 'spring_layout', type: 'gravis', nodeCount: 3, edgeCount: 2, palette_id: 'default' },
    };

    const renderer = new GravisGraphRenderer();
    const canHandle = renderer.canHandle(gjgfData);

    let renderError: string | null = null;
    try {
      renderer.render(container, gjgfData, {
        layout: 'spring_layout', enablePhysics: true, chargeStrength: -50, linkDistance: 100,
        nodeSize: 6, nodeOpacity: 0.9, nodeBorderWidth: 2, edgeWidth: 1.5, edgeOpacity: 0.7,
        showNodeLabels: true, showEdgeLabels: false, labelSize: 11, labelColor: '#00ff41',
        interactionProfile: 'default',
      });
    } catch (e: any) {
      renderError = e.message;
    }

    await new Promise((r) => setTimeout(r, 1500));

    const canvas = container.querySelector('canvas');
    let hasNonBlankPixels = false;
    if (canvas) {
      const ctx = (canvas as HTMLCanvasElement).getContext('2d')!;
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      for (let i = 3; i < imgData.length; i += 4) {
        if (imgData[i] !== 0) { hasNonBlankPixels = true; break; }
      }
    }

    renderer.cleanup();
    container.remove();

    return { canHandle, renderError, canvasCount: container.querySelectorAll('canvas').length, hasNonBlankPixels };
  });

  expect(result.canHandle).toBe(true);
  expect(result.renderError).toBeNull();
  expect(result.hasNonBlankPixels).toBe(true);
  expect(errors).toEqual([]);
});
