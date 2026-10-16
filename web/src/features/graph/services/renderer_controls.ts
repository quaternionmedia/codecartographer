/**
 * Which Graph Settings controls act on each renderer. A control the renderer
 * does not read is not offered.
 *
 * Physics, Repulsion and Link Distance drive a force simulation, and only
 * Gravis (vis-network) runs one. The D3 canvas draws nodes where the server's
 * layout placed them; Notebook and System Monitor draw without a simulation.
 * The layout algorithm is chosen for the D3 canvas, which asks the server for
 * it. Notebook and System Monitor take none of the visual controls.
 *
 * Compiled by `tsconfig.pure.json` and asserted under `node --test`.
 */

export interface RendererControls {
  layout: boolean;
  physics: boolean;
  visual: boolean;
}

export function rendererControls(renderer: string): RendererControls {
  return {
    layout: renderer === 'd3',
    physics: renderer === 'gravis',
    visual: renderer !== 'notebook' && renderer !== 'system',
  };
}
