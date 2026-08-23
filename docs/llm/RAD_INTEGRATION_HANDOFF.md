# Integrating rad into a web host — a handoff from the first one

**Status: field notes, not a standard.** The standard is
[`DRAFT-rad-host-integration-standard.md`](https://github.com/quaternionmedia/rad)
in `quaternionmedia/rad`. This page is what integrating against it actually
cost in one host, written for the next one — apothecary and benchmark, per the
*rad release milestones* draft's `v0.0.2`.

Where this page and the standard disagree, the standard wins and this page is
a bug. Where this page says something the standard does not, that is a
candidate for the standard, and it is marked **→ upstream**.

Reference implementation of everything below: [`web/src/features/graph/rad/`](../../web/src/features/graph/rad/).

---

## 1. The shape that worked

```
rad/
  core/        geometry.ts  machine.ts  time.ts  chord.ts  types.ts
               platform-free. No DOM, no app imports. Vector-tested.
  session.ts   createSession() — the standard's §2 seam, verbatim
  dom/         ring_view.ts  attach.ts  theme.ts
               SVG + Pointer Events. No app imports.
  host/        vocabulary.ts  resolve.ts  view_state.ts
               graph_intents.ts  rad_extension.ts
               the ONLY half that knows about the application
  conformance/ run.ts — replays the governed vectors
```

The line that matters is between `host/` and everything above it. Everything
above has no import that escapes `rad/`, which means the directory can be
lifted into a shared package the day a second web host wants one. `host/` is
the part you write yourself, and it is smaller than you expect: **five files,
~600 lines**, of which the interesting ones are `resolve.ts` and
`graph_intents.ts`.

**Port the core; do not try to import it.** rad's core is a comment banner
inside a 3,333-line `index.html` (its own C13), so there is nothing to import.
That sounds like a blocker and is not — the contract asks for a native
implementation per platform and shares only the contract and the vectors. The
port is about 250 lines and took under a day, matching the platform plan's
own estimate.

---

## 2. Do the conformance suite first, before any UI

This is the single strongest recommendation on the page. Port `core/`, replay
the vectors, and only then write a renderer. The vectors caught real errors in
the port while they were still cheap, and a green vector run makes every
later bug a wiring bug rather than a semantics bug.

**It costs no new dependency.** The core is pure, so it does not need a
browser or a test framework:

```jsonc
// tsconfig.rad.json — builds only the platform-free half
{
  "compilerOptions": {
    "lib": ["ES2020"],        // no DOM: a stray `document` is a COMPILE error
    "outDir": "dist-rad",
    "module": "ESNext", "moduleResolution": "bundler", "strict": true
  },
  "include": ["src/features/graph/rad/core/**/*.ts", /* … */]
}
```

```json
"test:rad": "npm run lint:rad && npm run build:rad && node --test tests/rad/"
```

`node --test` has shipped since Node 18. The whole suite runs in ~100 ms.

Three practical notes:

- **Use explicit `.js` extensions in relative imports** (`'./geometry.js'`).
  TypeScript's `bundler` resolution lets you omit them and Vite does not care,
  but Node's ESM loader does — and being resolvable outside a bundler is what
  makes the package liftable. Fixing this after the fact is a sweep.
- **Write `dist-rad/package.json` as `{"type":"module"}`** in the build step,
  or Node reparses every file and warns.
- **`lib: ["ES2020"]` will reject `queueMicrotask`.** It is a host global, not
  an ES one. `Promise.resolve().then(…)` is the portable form. This is the
  no-DOM rule doing its job rather than an inconvenience.

### Negative-control the runner, and the port

A conformance runner that reports success on a broken implementation is worse
than no runner, and you cannot tell the difference from a green run. Two
checks, both cheap:

```js
// the runner must go red on a corrupted expectation
const sabotaged = { ...vectors, cases: [{ ...aTrace, expectHighlights: [...hl, 999] }] };
assert.equal(runConformanceWith(sabotaged)[0].pass, false);
```

Then change a constant in your own core and watch the suite fail before you
believe it. Ours did — and told us something (§6).

### Check the constants, not just the behaviour

The vector file carries `geometry` and `time` blocks. Assert your port's
constants against them. This is not redundant with the behavioural cases:
**it caught a changed `cancelScale` that all 40 behavioural vectors missed.**

---

## 3. Where a host actually plugs in

Two callbacks, and both are required for a reason.

```ts
createSession({
  resolve: (context) => resolveGraphMenu(context, factsFor(context)),
  onIntent: (intent) => route(intent),
  onEffect: (fx) => { /* haptics, instrumentation */ },
});
```

**Make `resolve` pure by passing it facts, not state.** Ours takes a plain
`MenuFacts` record — `{ depth, hasRenderedChildren, pinned, hasSource, … }` —
computed by the caller. The payoff is immediate: menu content becomes
testable with no graph, no DOM and no network, and the "which items are
enabled in which state" logic gets real coverage.

```ts
// the whole of resolve's dependency on the application
export interface MenuFacts {
  depth?: number;
  hasRenderedChildren?: boolean;
  pinned?: boolean;
  selectionCount?: number;
  /* … */
}
```

**→ upstream:** the standard says `resolve(context) → MenuSpec` and is silent
on how the host gets what it needs. "Take facts as a parameter, do not close
over state" is the difference between a testable resolver and the legacy
menu's closures, and is worth a sentence in §2.

### Coordinate conversion is genuinely ~20 lines

The standard predicts this and it is accurate:

```ts
function polar(clientX: number, clientY: number) {
  const r = svg.getBoundingClientRect();
  const c = ring.getCentre();
  return toPolar(clientX - r.left - c.x, clientY - r.top - c.y);
}
```

Two traps, both of which we hit:

- **Mount the ring OUTSIDE your pan/zoom transform.** Inside it, the ring
  scales with the scene and its drawn band stops matching the geometry the
  machine judges against — the same class of defect rad fixed by making
  geometry travel with the machine.
- **Fit first, then clamp against the fitted radius.** Clamping against the
  natural `r1` places a shrunken ring using a radius it does not have.

**→ upstream:** both belong in §3. The second is a two-line ordering
constraint that is invisible until a small viewport makes it large.

---

## 4. Routing intents without lying about it

§5.1 says route through the authoritative state layer. In practice that
splits verbs into two kinds, and being explicit about the split is what keeps
it honest:

| | Verbs | Why |
|---|---|---|
| **State** | `hide` `pin` `color:*` `expand` `collapse` `delete` | own graph facts; must survive a re-render |
| **Camera / selection** | `fit` `relayout` `spread`\* `cluster`\* `toggle-physics`\* `select-neighbors` `clear-selection` | own nothing; routing them through the store adds a write nothing reads |

\* Disabled in our rings — this renderer takes positions from a backend layout
and has no simulation. They keep their wedges (a menu whose items move
between states is one nobody builds muscle memory for) and are wired to an
explicit refusal, not to `{}` and not to a fallback.

For the first group we added a sparse `NodeViewState` — `{ [id]: { hidden?,
pinned?, colorToken? } }` — that intents fold into and the renderer projects.
It is serializable, so it survives a cache replay. The legacy menu's
`d3.selectAll(...).attr('opacity', 0)` was invisible to the rest of the
application and vanished on the next redraw; this is what §5.1 is warning you
about, concretely.

### The routing test proves less than it looks like it proves

Read this before trusting your own version of it. Ours asserts *every verb the
menu can commit reaches a named operation* — and it stayed green while
`spread`, `cluster` and `focus-group` all pointed at the same `fitView()`
call. Three verbs claiming three things, doing one, and the suite could not
see it: the spy sits at the `GraphOps` boundary, so it observes *which op
fired*, never what the op body does. Op bodies are application code and never
enter the conformance build.

The gap is structural and you will have it too. Two things close most of it:

- **A capability the host lacks is offered disabled, never substituted.** That
  *is* purely testable — resolve with the capability flag false and assert the
  item comes back `enabled: false` while keeping its wedge. Aliasing a missing
  verb onto a working one is the failure mode; refusing to alias is the rule.
- **Review the op bodies by hand for duplicates.** Nothing automated caught
  this. Reading `ops` top to bottom did.

**Throw on an unrouted verb.** Do not let it fall through:

```ts
default:
  throw new Error(`rad: no handler for verb '${action}'`);
```

The legacy menu shipped stubbed actions that opened, animated, committed and
did nothing — indistinguishable from working ones. One test closes it
permanently:

```js
test('every verb the menu can commit reaches a named operation', () => {
  for (const action of allMenuVerbs()) { /* route into a spy, assert it fired */ }
});
```

**→ upstream:** §5's revision triggers already say that a host found violating
§5.2 or §5.3 means "§5 needs a check rather than a clause". Those checks
exist here — [`tests/rad/vocabulary.test.mjs`](../../web/tests/rad/vocabulary.test.mjs)
and [`intents.test.mjs`](../../web/tests/rad/intents.test.mjs) — and are
offered as the seed of them. They are ~120 lines and mostly host-agnostic.

---

## 5. Vocabulary: what we omitted, and why that is allowed

§5.2 says extend, never repurpose. It does not say implement everything, and
for a domain-specific host that distinction matters. A code map's nodes are
derived from parsing source, so:

- `add-node` — there is no meaningful "add" that is not an edit to a repo.
- `reverse`, `edit-label` — an edge's direction and label are facts about the
  code, not authored properties.

We omitted all three and declared three host verbs instead (`view-source`,
`node-info`, `focus-group`). **Name your omissions somewhere a reader can find
them**; a silently absent standard verb looks like an oversight.

Keep the chord vocabulary in a file that compiles into your conformance
build. One governed vector asserts the chord map is prefix-free — that vector
only means something if it reads the words you actually bind, not a copy.

**The 8-item ceiling binds harder than it looks.** Our node ring is at exactly
8, so the next verb forces a regrouping. That is the contract working; budget
for it rather than discovering it.

---

## 6. What we found, offered as vectors rather than fixed locally

Per §5.5 — a divergence is a proposed vector, not a local patch.

**`cancelScale` is unpinned by the behavioural suite.** Changing it from 1.35
to 1.60 fails no vector. The cases probe `r_cancel` at r=130/200 against
r1=108, and r=120/130 against r1=92, so the multiplier can sit anywhere in
**[1.3043, 1.413)** undetected. The contract's own revision triggers note that
1.35 "has not been validated against a human" — which makes it the constant
most likely to be tuned and currently the least guarded.

*Proposed vector:* a boundary pair at r1=108 — r=145.7 commits, r=145.9
cancels — pinning the multiplier to ±0.001.

Until such a vector exists, assert the `geometry` block (§2 above). That is
what caught this.

---

## 7. Order of work, in hindsight

1. `core/` + vectors + the two negative controls. **Nothing else.**
2. The DOM-freedom lint. It is 60 lines and it is the check the reference
   implementation cannot run on itself, so it is real evidence, not ceremony.
3. `resolve()` + vocabulary, with the §5.2/§5.3 tests. Still no UI.
4. The ring renderer and the input adapters.
5. Mount, and route intents.

Steps 1–3 are all testable without a browser, and they are where the
semantics live. We wrote them in that order and did not have to revisit any
of them once the UI existed.

---

## 8. What this host has not done

Stated so the next reader does not inherit an assumption:

- **No haptics.** `onEffect` is wired and empty.
- **No chord adapter mounted.** The vocabulary and the pure classifier are
  in place and tested; nothing listens to a keyboard for bursts yet.
- **No clock.** `time.ts` is ported in full because the vectors cover it, but
  nothing quantizes — this host has no MIDI and no live-performance context.
  Porting the pure functions anyway is what keeps "conformant" from meaning
  "conformant to the parts we felt like".
- **Not driven on a touch device.** Release-select, drag-through and the
  dead-zone cancel are vector-green and have not met a finger.
- **`view` has not been stress-tested as a renderer contract.** §6 of the
  standard flags that its shape is a guess informed by one renderer. Ours is
  the second, and it fit — but our ring is also SVG, so that is weak evidence
  for the Compose case.
