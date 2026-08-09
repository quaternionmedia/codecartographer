# Handoff — the rad integration on `feat/rad-integration`

**Working against `17a41a0`, 2026-08-09.** Every figure on this page was true
at that commit and may not be now. Re-derive before acting; do not quote a
number from here as current.

**Read the first two sections, then whichever queue item you are picking up.**

---

## Read this first: three branches, none of them pushed

| Repo | Branch | Head | Remote |
|---|---|---|---|
| `codecartographer` | `feat/rad-integration` | `17a41a0` | **does not exist** |
| `codecartographer/docs/qm` (submodule) | `adr/rad-integration` | `fd9d756` | **does not exist** |
| `qm/rad` | `evolve/rad-v1` | `a44f081` | 6 commits behind |

Everything below lives on one disk. That is the same failure the org rollout
page records as a stranded governance branch, and rad's own `HANDOFF.md` flags
it for rad at three hours old. This is now the third instance in one day, which
makes it a pattern rather than an accident.

```sh
git -C .          push -u origin feat/rad-integration
git -C docs/qm    push -u origin adr/rad-integration
git -C ../qm/rad  push origin evolve/rad-v1
```

**The submodule pointer was deliberately not bumped.** `git status` shows
`M docs/qm` and it should stay that way until `adr/rad-integration` is merged
into `project/codecartographer` — pinning the superproject to an unmerged ADR
side branch would point this repo at a ref that is about to move.

### The branch is stacked, not based on main

`feat/rad-integration` sits on `cleanup/2026-07-21-full-review`, which is
itself **53 commits ahead of `origin/main` and unmerged**. Five of those
commits are this work:

```
17a41a0  Fix what reviewing the rad integration found
ca82994  Write the host-integration handoff for the other v0.0.2 consumers
0f02357  Mount rad on the streaming renderer, and wire expand/collapse (M1, M2)
eb5fbb1  Add the rad DOM layer and this host's vocabulary, with §5 as tests
71effe5  Port the rad core to TypeScript and replay its vectors here
```

Do not open a PR against `main` without deciding what happens to the cleanup
branch first. The memory note *Lexicon Option B shipped* says that branch is
"awaiting one combined PR" — this work joins that queue rather than jumping it.

---

## What is verified, and what is not

| Claim | How established |
|---|---|
| 40/40 governed vectors replay green | `npm run test:rad`, 25 assertions total |
| The conformance runner actually fails | corrupted-expectation negative control in `conformance.test.mjs` |
| A changed core constant is caught | sabotage run — flipped a constant, suite went red |
| The disabled-capability rule is enforced | sabotage run — ungated `spread`, test 24 went red, restored |
| `core/` is DOM-free and app-free | `scripts/rad-core-lint.mjs`, 16 files; plus `lib:["ES2020"]` |
| Whole app compiles | `npx tsc --noEmit` clean |
| Whole app builds | `npx vite build` clean |
| **rad works in a browser** | **not established — nothing has been driven** |
| **Expand hits a live backend** | **not established — no server was run this session** |
| **The gesture grammar is usable** | **not established, and it is the actual deliverable** |

The gap between rows 1–7 and rows 8–10 is the whole risk on this branch. The
vectors prove the port agrees with the contract. Nothing yet proves the menu
is mounted where a user can reach it, which is the finding this work exists to
fix.

---

## The queue

| Task | Blocks on | Where |
|---|---|---|
| [Push all three branches](#read-this-first-three-branches-none-of-them-pushed) | nothing | all |
| [Q1 — drive it in a browser](#q1--drive-it-in-a-browser) | nothing | `codecartographer` |
| [Q2 — expand against a live backend](#q2--expand-against-a-live-backend) | a running server | `codecartographer` |
| [Q3 — decide the legacy menu's fate](#q3--the-legacy-menu) | Q1 | `codecartographer` |
| [Q4 — the cancelScale vector](#q4--the-cancelscale-vector) | a human amending the contract | `qm/rad` |
| [Q5 — merge the ADR into `project/codecartographer`](#q5--the-adr) | a push | `docs/qm` |

### Q1 — drive it in a browser

**Nothing on this branch has been seen working.** This is the top of the queue
and the reason nothing below it is urgent.

```sh
cd web && npm run dev      # then Load Demo — that is the fastest path to a graph
```

What to check, in the order a defect is most likely:

1. **Does the ring appear at all** on right-click / press-and-hold over the
   streamed graph? If not, the mount in `layout_context.ts::_mountRad` is not
   firing — it is called from `onDone` in `_mountAndStream`, so a stream that
   errors never mounts.
2. **Is the ring drawn outside the pan/zoom transform?** Zoom in, then open the
   menu. If the ring scales with the scene, the drawn band no longer matches
   the geometry the machine judges against and every commit lands on the wrong
   wedge. This is called out in the integration handoff as a known trap; it was
   written to be avoided but has not been observed.
3. **Keyboard route.** Focus the canvas, press the menu key. `_mountRad` sets
   `tabindex="0"` on the container if absent, and if some other component owns
   focus this silently does nothing.
4. **The dead-zone cancel and the outward cancel at `r_cancel`.** These are
   vector-green and have never met a finger.

Expect to find something. A first browser run that finds nothing would be more
surprising than one that finds three things.

### Q2 — expand against a live backend

`POST /parse/expand` answers in gJGF — `nodes` as an id-keyed map of
`{metadata}` records — while the streaming path deals in flat node objects.
`_normaliseGraph` in `layout_context.ts` accepts **either**, because both
conventions already exist in this codebase and guessing wrong fails silently as
an empty expansion.

That tolerance has never been exercised against a real response. Expand a
depth-0 directory node and confirm nodes actually arrive. The status line now
reports the count (`Expanded — N new node(s)`), so `Nothing further to expand`
on a directory that obviously has children means `_normaliseGraph` picked the
wrong shape.

### Q3 — the legacy menu

There are now two radial menus. `radial_menu.ts` still serves the Lexicon /
abstraction-layer path; rad serves every code-map path. `UI_REFERENCE.md`
documents both and which is which.

Retiring the legacy one is a follow-up the ADR explicitly does not make. Do not
delete it as tidying — it is the only menu on the Lexicon path, and the user's
standing preference is additive change over purge-and-replace. Migrating the
Lexicon path to rad is the real task, and it is not scoped here.

### Q4 — the cancelScale vector

The one divergence found, recorded in `qm/rad`'s milestone draft and in this
project's ADR §6. `cancelScale` can move anywhere in `[1.3043, 1.413)` without
failing a behavioural vector. Proposed fix is a boundary pair at r1=108 —
r=145.7 commits, r=145.9 cancels.

**Deliberately not applied.** Integration standard §5.5: a divergence is a
proposed vector, not a local patch, and adding a vector amends the contract.
That is a human's call.

### Q5 — the ADR

`docs/qm@adr/rad-integration` holds `DRAFT-rad-integration.md`. It needs
pushing and a PR into `project/codecartographer`, which is where this project's
ADRs live since the 2026-07-21 migration.

Status is **Draft** and must stay Draft — the standing rule is never
self-ratify. It carries two corrections written after review found the record
asserting things the code did not do; see below.

---

## What the review found, and why it matters more than the fixes

The first pass of this work shipped six defects. All six were mine, and two of
them were things the ADR asserted as done in the same commit that broke them:

- `spread`, `cluster` and `focus-group` were one `fitView()` call wearing three
  labels — the exact "stubbed actions indistinguishable from working ones"
  defect the commit message said it had closed.
- View state was wiped on relayout, while the record said it survives one.

**The test could not catch the first, and that is the transferable lesson.**
`intents.test.mjs` asserts every verb reaches a named operation. The spy sits
at the `GraphOps` boundary, so it sees *which* op fired and never what the op
body does — and op bodies are application code that never enters the
conformance build. A green suite proved routing and said nothing about meaning.

What closed it is a rule that *is* purely testable: **a capability the host
lacks is offered disabled, never substituted.** Reading the op bodies top to
bottom is what found it; no test would have.

This is written into `docs/llm/RAD_INTEGRATION_HANDOFF.md` as a warning to
apothecary and benchmark, who will have the same structural gap.

---

## Rules that apply to anything picked up here

- **Branch first**, even solo, even for local-only commits. Structural changes
  do not go on `main`.
- **Additive over destructive.** Build on what is there; do not purge and
  replace, even where a backlog says "purge".
- **Never self-ratify a record.** ADRs land as Draft/Proposed. A human accepts.
- **No `Co-Authored-By` naming a model** in `docs/qm` commits.
- **The user tests live and reports back.** Do not substitute an automated run
  for that loop, and do not claim a browser behaviour you have not seen.
- **A divergence from rad is a proposed vector, not a local patch** (§5.5).

---

## State at `17a41a0`

| | |
|---|---|
| rad gate | `npm run test:rad` — 25 assertions, 0 failures |
| Vectors | `web/tests/rad/vectors.v0.4.0.json`, pinned in the filename |
| Core lint | clean, 16 files |
| Typecheck / build | `tsc --noEmit` clean; `vite build` clean |
| New code | ~2,400 lines under `web/src/features/graph/rad/` |
| Host half | 5 files, ~600 lines, the only part importing app code |
| Node ring | at the contract's 8-item ceiling — no spare wedge |
| Records | `docs/qm@adr/rad-integration` (Draft), unpushed |

---

## Things deliberately not done

- **The submodule pointer was not bumped** — see the first section.
- **`cancelScale` was not changed**, and no vector was added to rad.
- **The legacy `radial_menu.ts` was not deleted.**
- **No chord adapter is mounted.** The vocabulary and the pure classifier are
  built and tested; nothing listens to a keyboard for bursts.
- **`time.ts` is ported but nothing quantizes.** This host has no MIDI. It was
  ported anyway because the vectors cover it, and skipping it would make
  "conformant" mean "conformant to the parts we felt like".
- **`onEffect` is wired and empty.** No haptics, no instrumentation.
- **Nothing was run in a browser.** Repeated here because it is the single
  thing most likely to be assumed from a green gate.
