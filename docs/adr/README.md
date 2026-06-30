# Architecture Decision Records — Process & Handoff

This directory is the project's decision memory. This file is the contract
for producing and maintaining it. The discipline exists because decision
documents drift in a specific, predictable way — drafts accumulate references
to their own revision history, numbers get assigned before ratification and
then need "renumbering," and supersession language leaks into documents that
were never published. The rules below make the discipline mechanical instead
of dependent on any one contributor's (or assistant's) memory.

## Adopted org records

This project adopts the [quaternionmedia/qm](../qm) constitution by
reference (vendored as a git submodule at `docs/qm`). Org records bind this
project; project records may tighten them, never relax them. A genuine
exception is an amendment ratified at org level.

| Corpus | Pin (tag/commit) | Records adopted |
|---|---|---|
| qm-constitution | `6b893e33176751c5b036a9380901397b2d77e7b` | all org records at pin (all currently `Proposed`, none yet `Accepted` upstream) |

Bumping the pin is a reviewed commit in this project.

## The one rule that prevents most drift

> **Before ratification, documents have no memory. After ratification, they
> have nothing but memory.**

- A **draft** is rewritten in place as understanding improves — squashed, as
  if the final position had been held from the beginning. Git is the
  archaeology; prose is not. A draft never says "previously," "supersedes the
  earlier stance," or "corrected in review."
- An **Accepted** ADR is append-only. Its body is never silently edited.
  Changes are dated entries under **Amendments**; reversals are a new ADR
  that **supersedes** it. Supersession is a relation between *ratified*
  documents only.

## Lifecycle

```
Draft ──▶ Proposed ──▶ Accepted ──▶ (Amended*) ──▶ Deprecated | Superseded by ADR-NNNN
  ▲           │
  └── squash ─┘   (any change before Accepted = rewrite in place)
```

| Status | Meaning |
|---|---|
| **Draft** | Being written. Numberless (`ADR-XXXX`). Rewritten freely. |
| **Proposed** | Complete; pending a named input (`Pends on`) or ratification. Numberless. |
| **Accepted** | Ratified. Number assigned. Append-only from here. |
| **Deprecated** | No longer applies; nothing replaced it. Body intact. |
| **Superseded** | Replaced by a named ADR. Body intact, header points forward. |

## Numbering

Numbers are assigned **at ratification, by the index below, in order of
acceptance** — never during drafting. Drafts reference each other by *title*.
Once assigned, a number is permanent; gaps are fine; numbers are never
reused. Project numbering is local (`ADR-NNNN`); org records are `QM-NNNN`.

## Authoring rules

1. **One decision per ADR.**
2. **Alternatives are written honestly** — each with the real reason it lost.
3. **Every ADR has revision triggers** — observable events, not vibes.
4. **Open questions are not decided by stealth** — undecided input → status
   Proposed with an explicit `Pends on`.
5. **External history is context; internal history is noise.**

## Drafting-session handoff (humans and AI assistants alike)

**Inputs to provide the session:** this file; the pinned org records; the
current index; the project design plan and any ADRs being touched.

**Session obligations:** plan first, with a contradiction check against the
org records and the index; squash continuously (the chat may discuss a
position change; the document may not); never assign numbers, never
renumber, never write supersession language into a draft; mark pending human
decisions as Proposed with `Pends on`; end by outputting drafts, the proposed
index diff, and the open-question list. Ratification — status flip, number
assignment, index update — is a **human commit** naming the record.

**Session prohibitions (verbatim-banned):** "takes the ADR-NNNN slot,"
"the set renumbers," "supersedes the stance from the earlier review/draft,"
"retroactive" framing for adoption-time rules, edits to an Accepted body
outside Amendments.

## Index

| # | Title | Status | Date |
|---|---|---|---|
| | | | |

Drafts in flight (numberless, by title):
- *Unify parser/cache architecture around `ParserRegistry` + `batch_whole_tree`* — `DRAFT-parser-cache-unification.md`
- *Golden Layout as the primary application shell* — `DRAFT-golden-layout-primary-shell.md`
- *Compound hierarchical layout (dirs → files → symbols)* — `DRAFT-compound-hierarchical-layout.md`
- *`CacheService` and `graphbase` stay separate stores* — `DRAFT-cache-service-vs-graphbase.md`
- *Generalize dock panels into a registry; add a window-add menu* — `DRAFT-panel-registry-and-add-window-menu.md`
- *Hierarchical drag propagation, per-depth labels, and compound layout spread improvements* — `DRAFT-d3-hierarchy-layout-improvements.md`
- *Wire graphbase as a named bookmark store via /db/bookmarks* — `DRAFT-graphbase-bookmark-integration.md`
