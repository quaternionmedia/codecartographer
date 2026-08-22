# Consolidation notes

**What this is.** Things found while putting the harness topology onto this
project's rendering path — each one hit while building, not read off the code.
Six are fixed and named here so nobody re-finds them; the rest are open, with
what they would cost.

**What it is not.** A backlog anybody has committed to, or a criticism of the
design. Most of these are the ordinary residue of a renderer that changed canvas
(matplotlib to gravis) while its vocabulary stayed where it was.

**Stamped 2026-08-22**, against `0823aa6`. Re-derive before acting.

---

## Fixed while passing through

**The `Palette` decided nothing.** `bases`, `labels`, `alphas`, `sizes`,
`shapes` and `colors` were all declared and none was read on the rendering path:
sizes came from an edge-count heuristic, colours from two hard-coded names in
the dependency branch, and `palette_id` reached the output as a line of metadata.
A palette could be edited, saved and selected without changing a pixel.
`services/palette_service.py` now resolves them, including the dotted hierarchy
that makes a coarse palette possible — `control.cond.if` inherits from
`control.cond`, then `control`. Nothing had ever walked it.

**`serialize_to_gjgf` collapsed every multigraph.** `nx.DiGraph(graph)` keeps
one edge per ordered pair and drops the rest silently. Three measured readings of
one relation went in and one came out, with no error and a picture that looked
complete. Multigraphs are preserved now; simple graphs are untouched.

**An explicit node `size` was overwritten.** A caller setting `size=30` got 21
from the edge-count heuristic. The heuristic is what to do when nobody has
decided, not a correction to somebody who has.

**A layout could not be named the way a menu names it.** `serialize_to_gjgf`
builds the registry key as `layout.lower() + "_layout"`, so `Kamada Kawai`
became `kamada kawai_layout` and failed several frames deep with a message
naming a layout nobody typed. `position_service.layout_key` normalises spaces
and hyphens in one place, and both lookups accept either spelling.

**An unknown layout raised `UnboundLocalError`.** `get_positions` left
`layout_func` unbound when nothing matched, so the caller got an error about a
local variable. It raises a `ValueError` naming what is registered.

**A GitHub token prefix was written to a log.** `_github_token[:8]` is `gho_`
plus four characters of the secret, in a file that outlives the process. Not
usable at that length, and not a thing to write down; it logs the token *kind*
now.

**The API's address was written down four times, and three were wrong.**
`appsettings.json` said 8000 (which is what `playwright.config.ts` starts, so it
was not arbitrary — it was one true case), the container publishes 2020, and the
trio runs 2718. A build could only ever talk to one of them, and moving the API
meant rebuilding the front end. Now: `ConfigManager` resolves at runtime
(injected meta tag → same origin → settings), the dev server proxies API paths
so development shares an origin like production does, and `playwright.config.ts`
states the address it starts rather than relying on a constant agreeing with it.

**`StateController.update` changes state without repainting.** Every other
action gets away with it because it is reached from a DOM event handler, and
Mithril repaints after those by itself. An `oninit` that awaits is not, so the
Topology panel sat on "asking the harness…" after its answer had arrived.
`update` is used in dozens of places; **whether it should redraw is a real
decision and not obviously "yes"** — a redraw per update in a loop is waste. But
the current arrangement means correctness depends on the caller's context, which
nothing states and nothing checks. Either `update` redraws and a batching escape
hatch exists, or it keeps a name that says it does not.

## Open, with what it would cost

**The palette speaks matplotlib and the canvas speaks gravis.** `shapes` are
markers (`o`, `s`, `^`, `x`) because matplotlib drew these first. gravis knows
three shapes, so nine markers collapse onto them and `x` — chosen by an author
precisely to stand apart from `o` — had no mapping at all until a test asked for
one. **The cheap repair is done** (one translation table, tested against every
marker in the default palette). The real question is whether the palette should
carry canvas-neutral shape *names* with per-renderer tables beside it. That is a
data migration and a decision about which renderer is primary; worth taking
deliberately rather than drifting into.

**`DefaultPalette` is a literal in `models/plot_data.py`.** Several hundred
lines of styling data inside a module that also defines the models that describe
it. Moving it to `data/palettes/default.yaml` — beside `data/lexicons/` — would
match where lexicons already live and let a palette be edited without touching
Python. The blocker is that `Palette` is constructed at import time by several
callers.

**Nothing validates a custom palette.** `fetch_palette_by_id` returns whatever
the database holds. A palette missing `unknown` resolves every unmatched base to
the hard-coded fallbacks in `palette_service`, quietly. A `Palette.validate()`
naming missing keys would make a bad palette a message rather than a grey graph.

**The lexicon and the palette describe the same thing twice.**
`models/lexicon.py` puts tokens on abstraction layers with a `group`, explicitly
so graphs can be coloured by abstraction level. The palette maps AST node types
to dotted bases with colours. Both are ontologies of the same language aimed at
the same renderer, and neither knows about the other. Joining them — bases
derived from lexicon groups, or a lexicon layer resolving to a base — is the
largest item here and the one most likely to pay off.

**`plotter_router.render_graph_to_html` inlines its own gJGF handling.** About a
hundred lines pulling nodes, edges and eight colour overrides out of a dict by
hand, duplicating what `GraphSerializer` and the models already describe. The
topology router builds its figure in a dozen lines through the serializer; the
same treatment would shrink the plotter route and give both one path to fix.

**`gravis_settings.GravisOptions` is unused.** Twenty-odd rendering settings
with sensible defaults, and the figures are built with keyword arguments written
out at each call site — including this project's newest one, because passing
`GravisOptions` was not wired to anything. Either it becomes the way figures are
configured, or it goes.

**`Positions._layouts` is private and read from outside.** The topology page
lists available layouts by reaching into it. A public `names()` would be one
line and would let the picker stop touching an underscore.

**Two `topology_service` modules existed briefly.** One here, one in `dossier`,
with the same channel constants written out twice because the repositories may
not import each other. That duplication is deliberate and correct — but only
`MIN_WIDTH`, `UNMEASURED_WIDTH` and the style names are shared, and a drift
between them would show up as two windows disagreeing rather than as an error.
`qm demo --over-http` is what catches it, and it only runs when somebody runs it.
