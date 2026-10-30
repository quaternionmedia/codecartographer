# Scale

What a show export costs a reader, measured; how fast the corpus it draws is
growing; and the budgets and rules that keep every page manageable as it
grows. The numbers are a baseline to optimise against: `codecarto show
measure` takes them again, and sets a new export beside them.

The baseline is the export the corpus's showgraph pages were last drawn from:
codecartographer at `92c5a4c`, the corpus at `bb2ed17`, drawn on 2026-10-29,
with its built site. Every figure here is in
[docs/scale/baseline.json](scale/baseline.json) and
[docs/scale/growth.json](scale/growth.json), or says where it came from.

## What a picture costs

**Elements, not bytes.** GitHub Pages sends a picture gzipped, at about a
tenth of its size: core's family code map is 22.5 MB on disk and 2.0 MB on
the wire. The browser still parses and paints every element in it. Over the
93 pictures, the time Chromium takes to draw one follows its element count
closely: about 27 ms and 9.5 ms for every thousand elements, on the machine
below (r² 0.984). A megabyte here is 2²⁰ bytes.

| picture | elements | drawn here | at a 4× CPU slowdown |
|---|---|---|---|
| a project's estate | 36-122 | 33 ms | 34 ms |
| qm's code map | 14,976 | 127 ms | 681 ms |
| apothecary's code map | 34,276 | 287 ms | 1,464 ms |
| core's family code map | 101,338 | 1,046 ms | 6,026 ms |

Drawn is decoded, put on a page at the picture's own size, and two frames let
pass. The machine is an Intel Core i9-9900K, 16 threads, 64 GB, Windows 11,
Chromium 149. A 4× CPU slowdown is Chrome's DevTools' setting for a mid-tier
phone. Timed in a run of its own, it made each large picture 5.4 to 5.7 times
as slow as the same run unslowed, so a phone pays seconds where this machine
pays a second. A picture of a few dozen elements costs two frames either way.

## The baseline

93 pictures, 86.4 MB (8.1 MB gzipped), and 47 show documents, 30.7 MB: 117.2
MB in all.

| level | pictures | median elements | heaviest | its elements | gzipped | drawn in |
|---|---|---|---|---|---|---|
| index | 1 | 372 | `index/estate.svg` | 372 | 6.7 KB | 33 ms |
| family | 18 | 350 | `family/core/code.svg` | 101,338 | 2.0 MB | 1,046 ms |
| project | 74 | 86 | `project/apothecary/code.svg` | 34,276 | 815 KB | 287 ms |

A page's cost is the pictures it fetches as it opens. The median page opens in
218 ms here. The heaviest:

| page | elements on opening | opens in | with its lazy pictures |
|---|---|---|---|
| codecartographer's | 15,853 | 4,576 ms | 413,169 |
| core's | 101,400 | 1,769 ms | 101,400 |
| irl's | 64,640 | 1,170 ms | 64,640 |
| performing's | 48,805 | 904 ms | 48,805 |
| apothecary's | 34,332 | 516 ms | 34,332 |

codecartographer's page holds every showgraph, 94 pictures, and every one but
two is lazy, yet it is the slowest to open: a browser fetches a lazy picture
once it is within a screen or two of view, and a grid of small pictures puts
dozens within that.

**Where core's family code map goes.** Of its 101,338 elements:
- 15,770 are marks, each a group and a shape;
- 19,117 are links;
- 34,887 are `<title>`s, which a browser shows only on hovering the picture
  opened on its own, never on a page that shows it as an image;
- 15,770 are labels, of which 15,762 the window had hidden, so they are
  parsed and never shown.

Without the titles and the hidden labels it is 50,689 elements, about 3.2 a
mark. Of its 22.5 MB, 12.6 MB shows nothing either:
- the window's interaction data (`data-*`), 6.2 MB;
- a style restating the colours beside it, 4.5 MB;
- decimals past the first, 1.9 MB.

**Two exports of the same sources differ.** The export was run again from the
same commits. Of 93 pictures:
- 35 were the same bytes;
- 26 differed only in coordinates past the first decimal, by at most 0.005;
- 32 differed further, in the transform that fits the drawing to the window
  and in label offsets measured from the drawn text.

So every redraw writes almost every picture again. The corpus's pull request
that publishes this export adds 10.5 MB to its repository's history, against a
25 MB pack; the redraw before it added 5.0 MB.

**An export's time.** The rerun drew the 47 subjects in 447 s, one at a time.
After the first, which starts the servers, each subject took about 5.7 s and
2.1 s per thousand marks; core's family code map took 49 s.

## How fast the corpus grows

`codecarto show growth` read each project's history up to the commit its code
map was drawn from:

| month | projects | commits | bytes the parser reads | code-map nodes (est.) |
|---|---|---|---|---|
| 2026-05 | 29 | 7 | 5.7 MB | 8,393 |
| 2026-06 | 31 | 47 | 6.8 MB | 9,550 |
| 2026-07 | 32 | 147 | 8.1 MB | 10,493 |
| 2026-08 | 34 | 893 | 15.4 MB | 17,968 |
| 2026-09 | 37 | 570 | 17.6 MB | 20,128 |
| 2026-10 | 37 | 2,157 | 29.3 MB | 33,388 |

Months to double, fitted through the last 6, 12 and 24 months:

| series | 6 | 12 | 24 |
|---|---|---|---|
| code-map nodes (est.) | 2.5 | 4.2 | 8.0 |
| bytes read | 2.1 | 3.5 | 6.6 |
| commits a month | 0.6 | 1.6 | 4.6 |
| projects | 13.4 | 16.8 | 28.3 |

A month's nodes are its bytes at each project's nodes per byte today. The
projects double in over a year; what they hold doubles in a few months. So the
cost grows inside each project and family, and a page that draws a project
whole outgrows any fixed budget.

If nothing about the drawing changes, each picture grows with the nodes, and
this many go over the element budgets below:

| after | at 2.5 months to double | at 4.2 months to double |
|---|---|---|
| now | 7 of 93 pictures, 8 of 47 pages on opening | the same |
| 3 months | 10 pictures, 11 pages | 10, 10 |
| 6 months | 14 pictures, 15 pages; core's page 533,000 elements | 11, 11 |
| 12 months | 32 pictures, 34 pages; core's page 2.8 million | 18, 18 |

## Budgets

`show_measure.BUDGETS`, and what each is for:

| budget | value | why |
|---|---|---|
| a picture's elements | 15,000 | draws in about 170 ms here, and about a second at a 4× slowdown |
| a page's elements on opening | 15,000 | the same second, for everything a page fetches as it opens |
| a page's elements with its lazy pictures | 75,000 | five pictures' worth; lazy loading spares a long grid little |
| a picture's unseen labels | 0 | a hidden or unreadable label is all cost |

A label is unseen when the window hid it, or when it is under 8 px at the
picture's own size. Nothing fails on a budget yet: `--check` exits 1 when one
is exceeded, which is how a redraw's CI would hold it, once a decision record
adopts these.

## Rules for growth

1. **A page is held to its own subject.** No page's cost may grow with the
   corpus as a whole. The index draws the families, not what is in them. The
   one page that holds the corpus today, the drawer's "Every showgraph"
   gallery on codecartographer's page, splits along the hierarchy: each
   family's pictures go on that family's page.
2. **Each level draws one level deeper than the level above it, and no
   deeper:**
   - the index, each family with its members;
   - a family, its projects to their files;
   - a project, its own symbols.

   Its projects to their files are at most 1,507 marks for a family, core's,
   where to their symbols they are 15,762. At about three elements a mark, that
   is a picture of about 5,000 elements before its links. A deeper view of a
   subject, a family to every symbol or the whole corpus, is the live window's.
   The page links it by its address (`?show=family:core&view=code`) and draws
   none of it.
3. **A subject that outgrows its budget steps back a level, whole.** Its
   picture is drawn one level shallower and links the deeper view; a subject
   is never cut into pieces by a count. Symbols are about 9.9 times files and
   folders across the code maps, so each step back buys about 3.3 doublings:
   8 months at the last half-year's rate, 14 at the last year's. When a family's
   projects to their files outgrow it too, the hierarchy needs another level,
   a subfamily as performing has three, and that is the corpus's decision:
   `codecarto show measure` names the family; it does not split it.
4. **A picture carries nothing its page does not show:**
   - no hidden label;
   - no `<title>` in a picture a page shows as an image;
   - no interaction data;
   - a colour once;
   - one decimal.

   In core's family code map that is half its elements and over half its
   bytes. Draw time follows elements, so it is about half the time: 508 ms by
   the fit, against 1,046.
5. **The same inputs draw the same bytes.** Coordinates rounded and the fit's
   transform settled to fixed steps, so that a redraw of an unchanged subject
   writes nothing, and the corpus's history grows by what changed, not by the
   whole folder.
6. **A redraw draws what changed.** A full export's time grows with the marks
   drawn, which double every few months. Once rule 5 holds, an export skips a
   subject whose source commit, claims and drawer are all unchanged.
7. **Every redraw is measured against the baseline.** The redraw's pull
   request carries `codecarto show measure` against
   `docs/scale/baseline.json`. The baseline is replaced when a change to the
   drawing is accepted, and growth is measured again each quarter, to check
   the rate these rules are sized for.

## Measuring again

```bash
uv run codecarto show measure ../qm/docs/show --site ../qm/site --draw --out report.json --against docs/scale/baseline.json
uv run codecarto show growth ../clones ../qm/docs/show --out growth.json
```

- **`show measure`** reads an export folder and, with `--site`, a site built
  from it (`zensical build` in the corpus). It prints:
  - each level's heaviest picture;
  - the heaviest pages;
  - everything over a budget;
  - with `--against`, each headline number that changed, and by how much.

  `--draw` adds Chromium's times from `web/scripts/measure-draw.mjs`, which
  serves every file from disk and fetches nothing, and names the machine.
  Without it nothing depends on the machine.
- **`show growth`** needs a clone of each project, bare or not, named
  `<project>.git` or `<project>`. `gh repo clone quaternionmedia/<project>
  <project>.git -- --bare` makes one. A project whose clone lacks the commit
  its map was drawn from is named and left out.

Not measured here:
- the live window drawing the views rule 2 sends to it;
- a real phone, rather than Chromium slowed;
- memory;
- the network beyond gzipped sizes.

The timings were taken on a workstation running other work, and a run's
figures move by a few percent from one run to the next.
