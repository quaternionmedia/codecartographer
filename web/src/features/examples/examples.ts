/**
 * What the project selector offers to open, by language.
 *
 * **RUST FIRST, AND ONE EXAMPLE THAT NEEDS NOTHING.** The Rust group leads,
 * because Rust and its firmware are where this window reads the most -- the
 * code map, the Cargo panel, rustc's diagnostics, the memory a link measured.
 * GitHub examples show the code map only: the window never runs cargo, and a
 * fetched repository brings no records of a build. So the group opens with the
 * examples bundled with this checkout (`GET /repo/examples`), which bring their
 * recorded documents with them and need no network and no toolchain.
 *
 * A title says how much of a GitHub repository is drawn, by the server's own
 * thresholds (`github_service`): under ~5 MB with its content, under ~50 MB
 * as structure only, above that as a shallow root.
 *
 * Compiled by `tsconfig.pure.json` and asserted under `node --test`.
 */

export interface Example {
  label: string;
  /** A GitHub repository, or for a bundled example the absolute path it is read from. */
  url: string;
  title: string;
  /** Bundled with this checkout, read from disk. */
  bundled?: boolean;
  /** A Cargo workspace whose recorded documents the Cargo panel can read. */
  cargo?: boolean;
}

export interface ExampleGroup {
  language: string;
  examples: Example[];
}

/** One bundled example, as `GET /repo/examples` answers. */
export interface BundledExample {
  id: string;
  label: string;
  language: string;
  title: string;
  path: string;
  cargo: boolean;
}

export const GITHUB_EXAMPLES: readonly ExampleGroup[] = [
  {
    language: 'Rust',
    examples: [
      { label: 'app-template', url: 'https://github.com/knurling-rs/app-template',
        title: 'knurling-rs app-template — a probe-rs + defmt firmware starting point (~80 KB), with content' },
      { label: 'mini-redis', url: 'https://github.com/tokio-rs/mini-redis',
        title: 'mini-redis — an async Redis server on Tokio, written to teach (~240 KB), with content' },
      { label: 'embedded-hal', url: 'https://github.com/rust-embedded/embedded-hal',
        title: 'embedded-hal — the traits a firmware driver implements (~1.6 MB), with content' },
      { label: 'rustlings', url: 'https://github.com/rust-lang/rustlings',
        title: 'rustlings — small exercises in reading and writing Rust (~4.5 MB), with content' },
      { label: 'embassy', url: 'https://github.com/embassy-rs/embassy',
        title: 'embassy — an async embedded framework across many chips (~45 MB), structure only' },
    ],
  },
  {
    language: 'C',
    examples: [
      { label: 'git', url: 'https://github.com/git/git', title: 'git — the VCS itself, written in C (~30 MB), structure only' },
      { label: 'curl', url: 'https://github.com/curl/curl', title: 'curl — ubiquitous networking library in C (~10 MB), full content' },
      { label: 'Lua', url: 'https://github.com/lua/lua', title: 'Lua 5.x — reference VM in C (~1 MB), full content' },
      { label: 'SQLite', url: 'https://github.com/sqlite/sqlite', title: 'SQLite — most deployed DB in C (~15 MB), structure only' },
      { label: 'Redis', url: 'https://github.com/redis/redis', title: 'Redis — systems C data structures (~5 MB), full content' },
      { label: 'Linux', url: 'https://github.com/torvalds/linux', title: 'Linux — xxlarge repo (~1 GB+), shallow root' },
    ],
  },
  {
    language: 'Python',
    examples: [
      { label: 'requests', url: 'https://github.com/psf/requests', title: 'requests — small repo (~2 MB), full content' },
      { label: 'Flask', url: 'https://github.com/pallets/flask', title: 'Flask — medium repo (~8 MB), structure only' },
      { label: 'CPython', url: 'https://github.com/python/cpython', title: 'CPython — xlarge repo (~200 MB), shallow root' },
    ],
  },
  {
    language: 'JavaScript',
    examples: [
      { label: 'React', url: 'https://github.com/facebook/react', title: 'React — large repo (~25 MB), structure only' },
    ],
  },
];

/**
 * The selector's groups: each language's bundled examples first, then its
 * GitHub ones. A bundled example in a language with no group gets one.
 */
export function exampleGroups(bundled: readonly BundledExample[]): ExampleGroup[] {
  const groups = GITHUB_EXAMPLES.map((g) => ({ language: g.language, examples: [...g.examples] }));
  for (const b of [...bundled].reverse()) {
    const example: Example = { label: b.label, url: b.path, title: b.title, bundled: true, cargo: b.cargo };
    const group = groups.find((g) => g.language.toLowerCase() === b.language.toLowerCase());
    if (group) group.examples.unshift(example);
    else groups.push({ language: b.language, examples: [example] });
  }
  return groups;
}
