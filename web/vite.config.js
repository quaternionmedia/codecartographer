// Where the API is while developing. The dev server proxies to it so the app
// and its API share an origin in development exactly as they do in production,
// which removes the whole class of "works built, broken in dev".
//
// **THIS EXISTS BECAUSE `appsettings.json` NAMED A PORT NOTHING RUNS ON.** It
// said 8000; the container publishes 2020 and the trio runs 2718. A developer
// running `npm run dev` got a panel stuck on "asking the harness..." with no
// clue that the request had gone to a fourth address.
const API = process.env.CODECARTO_API || 'http://127.0.0.1:2718';

// Every path the API owns. A prefix missing from this list is a request the
// dev server tries to answer itself and cannot, so the list is the contract.
const API_PATHS = [
  '/topology', '/plotter', '/palette', '/repo', '/parse', '/lexicon',
  '/c-parser', '/pam', '/db', '/auth', '/docs', '/openapi.json',
];

export default {
  root: 'src',
  server: {
    port: 1234,
    host: '0.0.0.0',
    proxy: Object.fromEntries(
      API_PATHS.map((path) => [path, { target: API, changeOrigin: true }]),
    ),
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
