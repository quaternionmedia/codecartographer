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
 * **A TITLE SAYS HOW MUCH IS DRAWN, OF THE SIZE MEASURED BESIDE IT.** The
 * server reads the size GitHub reports for a repository, in KB and with its
 * history, against its own thresholds (`github_service`): under 5,000 KB it is
 * drawn with its content, under 50,000 KB as structure only, and above that as
 * a shallow root. So a small library with a long history is past the first.
 * Each example's `sizeKb` is that size as `gh api repos/<owner>/<repo> --jq
 * .size` gave it on `SIZES_MEASURED`, and its title ends with the word the
 * thresholds give for it; `tests/test_examples.py` holds the two together. A
 * repository grows after it is measured, and nothing here notices.
 *
 * Compiled by `tsconfig.pure.json` and asserted under `node --test`.
 */

/** The day each GitHub example's `sizeKb` was measured. */
export const SIZES_MEASURED = '2026-10-25';

export interface Example {
  label: string;
  /** A GitHub repository, or for a bundled example the absolute path it is read from. */
  url: string;
  title: string;
  /** A GitHub repository's size in KB, as GitHub gave it on `SIZES_MEASURED`. */
  sizeKb?: number;
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
      { label: 'app-template', url: 'https://github.com/knurling-rs/app-template', sizeKb: 80,
        title: 'knurling-rs app-template — a probe-rs + defmt firmware starting point (~80 KB), with content' },
      { label: 'mini-redis', url: 'https://github.com/tokio-rs/mini-redis', sizeKb: 240,
        title: 'mini-redis — an async Redis server on Tokio, written to teach (~240 KB), with content' },
      { label: 'embedded-hal', url: 'https://github.com/rust-embedded/embedded-hal', sizeKb: 1613,
        title: 'embedded-hal — the traits a firmware driver implements (~1.6 MB), with content' },
      { label: 'rustlings', url: 'https://github.com/rust-lang/rustlings', sizeKb: 4461,
        title: 'rustlings — small exercises in reading and writing Rust (~4.5 MB), with content' },
      { label: 'embassy', url: 'https://github.com/embassy-rs/embassy', sizeKb: 46847,
        title: 'embassy — an async embedded framework across many chips (~47 MB), structure only' },
    ],
  },
  {
    language: 'C',
    examples: [
      { label: 'git', url: 'https://github.com/git/git', sizeKb: 323561,
        title: 'git — the VCS itself, written in C (~324 MB), shallow root' },
      { label: 'curl', url: 'https://github.com/curl/curl', sizeKb: 150584,
        title: 'curl — ubiquitous networking library in C (~151 MB), shallow root' },
      { label: 'Lua', url: 'https://github.com/lua/lua', sizeKb: 12456,
        title: 'Lua 5.x — reference VM in C (~12 MB), structure only' },
      { label: 'SQLite', url: 'https://github.com/sqlite/sqlite', sizeKb: 579841,
        title: 'SQLite — most deployed DB in C (~580 MB), shallow root' },
      { label: 'Redis', url: 'https://github.com/redis/redis', sizeKb: 219085,
        title: 'Redis — systems C data structures (~219 MB), shallow root' },
    ],
  },
  {
    language: 'Python',
    examples: [
      { label: 'requests', url: 'https://github.com/psf/requests', sizeKb: 13631,
        title: 'requests — HTTP for Python, a small library with a long history (~14 MB), structure only' },
      { label: 'Flask', url: 'https://github.com/pallets/flask', sizeKb: 12216,
        title: 'Flask — a web microframework (~12 MB), structure only' },
      { label: 'React', url: 'https://github.com/facebook/react', sizeKb: 1127731,
        title: 'React — a large JavaScript repository (~1.1 GB), shallow root' },
      { label: 'CPython', url: 'https://github.com/python/cpython', sizeKb: 899710,
        title: 'CPython — the reference interpreter (~900 MB), shallow root' },
      { label: 'Linux', url: 'https://github.com/torvalds/linux', sizeKb: 6447116,
        title: 'Linux — the kernel (~6.4 GB), shallow root' },
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
