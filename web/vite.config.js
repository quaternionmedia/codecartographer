export default {
  root: 'src',
  server: {
    port: 1234,
    host: '0.0.0.0',
  },
  build: {
    base: '/codecartographer',
    outDir: '../dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // vis-network/vis-data (~530 KB minified) are only ever loaded
          // via the dynamic import() inside GravisGraphRenderer.render(),
          // so isolating them here doesn't add to the eager bundle -- it
          // gives that lazy chunk one stable, named file instead of an
          // auto-hashed one, and it's never in index.html's
          // modulepreload list (verified: only d3/golden-layout are).
          'vis-network': ['vis-network', 'vis-data'],
          // d3/golden-layout are both needed at startup either way; split
          // out mainly so unrelated app-code deploys don't invalidate
          // browser caches for these rarely-changing vendor chunks.
          'golden-layout': ['golden-layout'],
          'd3': ['d3'],
        },
      },
    },
    // The vis-network chunk above is intentionally >500 KB but lazy --
    // the default warning threshold doesn't distinguish eager from lazy
    // chunks, so it would otherwise flag a non-problem on every build.
    chunkSizeWarningLimit: 600,
  },
};
