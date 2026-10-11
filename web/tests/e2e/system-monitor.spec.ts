import { test, expect } from '@playwright/test';

/**
 * The system monitor, driven as the generic thing it now is.
 *
 * Like gravis-renderer.spec.ts, this imports the modules through Vite and
 * drives the renderer directly: the subject is the renderer/definition seam,
 * not the dock layout around it.
 *
 * The first test uses an inline definition, so it proves the seam with no
 * dependency on what happens to be cloned beside the checkout. The second
 * renders the real moat derivation end-to-end — backend compose, layout,
 * replayed history — and skips with the reason on a machine without a moat
 * clone, rather than faking one: the derivation from real contents IS its
 * subject.
 */

test('the renderer draws whatever definition styling selects', async ({ page }) => {
  await page.goto('/');
  const outcome = await page.evaluate(async () => {
    // @ts-expect-error -- an absolute Vite dev-server URL, resolved in the browser at run time
    const core = await import('/features/graph/services/system_core.ts');
    // @ts-expect-error -- an absolute Vite dev-server URL, resolved in the browser at run time
    const mod = await import('/features/graph/services/system_renderer.ts');

    const definition = {
      id: 'e2e-inline',
      name: 'Inline E2E System',
      description: 'two nodes, one packet',
      wsPath: '',
      httpStatusPath: '',
      getNodes: () => ({
        a: { label: 'A', px: 0.2, py: 0.5, type: 'chart' },
        b: { label: 'B', px: 0.8, py: 0.5, type: 'application' },
      }),
      getEdges: () => [{ from: 'a', to: 'b', style: 'solid' as const }],
      getDemoEvents: () => [{ event_type: 'ping', timestamp: 0.1 }],
      handleEvent: (
        ev: { event_type: string },
        cb: { setNodeState(id: string, s: string): void;
              log(t: string, l: string): void },
      ) => {
        if (ev.event_type === 'ping') {
          cb.setNodeState('b', 'active');
          cb.log('ping handled', 'ok');
        }
      },
    };
    core.SystemDefinitionRegistry.register(definition as never);

    const container = document.createElement('div');
    container.style.cssText = 'width:800px;height:500px';
    document.body.appendChild(container);

    const renderer = new mod.SystemRenderer();
    renderer.render(container, null, { systemId: 'e2e-inline' } as never);
    await new Promise(resolve => setTimeout(resolve, 600));

    return {
      title: container.querySelector('.sys-title')?.textContent ?? '',
      nodes: container.querySelectorAll('.sys-node').length,
      activated: container.querySelectorAll('.sys-node--active').length,
      log: container.querySelector('.sys-log')?.textContent ?? '',
    };
  });

  expect(outcome.title).toBe('Inline E2E System');
  expect(outcome.nodes).toBe(2);
  expect(outcome.activated).toBe(1);
  expect(outcome.log).toContain('ping handled');
});

test('moat is derived from its clone and replays real history', async ({ page }) => {
  await page.goto('/');

  const listed = await page.evaluate(async () => {
    const reply = await fetch('/system/repos');
    if (!reply.ok) return [];
    const doc = await reply.json() as { repos: { name: string }[] };
    return doc.repos.map(r => r.name);
  });
  test.skip(!listed.includes('moat'),
    'no moat clone beside this backend — the derivation from real contents is the subject, so nothing is faked');

  const outcome = await page.evaluate(async () => {
    // @ts-expect-error -- an absolute Vite dev-server URL, resolved in the browser at run time
    const derived = await import('/features/graph/services/derived_system.ts');
    // @ts-expect-error -- an absolute Vite dev-server URL, resolved in the browser at run time
    const core = await import('/features/graph/services/system_core.ts');
    // @ts-expect-error -- an absolute Vite dev-server URL, resolved in the browser at run time
    const mod = await import('/features/graph/services/system_renderer.ts');

    const moat = new derived.DerivedSystemDefinition('moat');
    core.SystemDefinitionRegistry.register(moat);

    const container = document.createElement('div');
    container.style.cssText = 'width:1100px;height:700px';
    document.body.appendChild(container);

    const renderer = new mod.SystemRenderer();
    renderer.render(container, null, {
      systemId: 'moat',
      systemHttpBase: '',   // same origin: the dev server proxies /system
      systemMode: 'demo',
    } as never);
    // load() fetches compose+events, then the demo replays paced history —
    // wait until the first change frame lands in the log, up to 30 s.
    for (let waited = 0; waited < 30000; waited += 100) {
      if ((container.querySelector('.sys-log')?.textContent ?? '').includes('REPLAY')) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const labels = [...container.querySelectorAll('.sys-node')]
      .map(el => el.textContent ?? '');
    return {
      title: container.querySelector('.sys-title')?.textContent ?? '',
      nodes: labels.length,
      hasGroot: labels.some(l => l.includes('groot')),
      log: container.querySelector('.sys-log')?.textContent ?? '',
    };
  });

  expect(outcome.title).toBe('moat (derived)');
  // The exact count is moat's to decide; the shape is ours: a real homelab
  // has more than a handful of components, and groot is its deployer.
  expect(outcome.nodes).toBeGreaterThan(5);
  expect(outcome.hasGroot).toBe(true);
  expect(outcome.log).toContain('REPLAY');
});
