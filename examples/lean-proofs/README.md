# lean-proofs — a small Lean 4 library

Three files of core Lean 4, with no dependency beyond the toolchain:

- `Proofs/Basic.lean` defines `double` and proves three facts about it.
- `Proofs/Parity.lean` states evenness and oddness through `double` and proves
  them closed under the obvious operations. `even_or_odd` is left with a
  `sorry` in its inductive step.
- `Proofs/Shapes.lean` holds data: a structure and one that extends it, an
  inductive with arguments and one without, a class with two instances, and
  two axioms with a theorem that rests on them.

It is the [Open panel's](../../docs/ui.md#open) Lean example, **parity
proofs**, and shows what codecarto reads of a Lean project with no Lean
toolchain on the machine:

- each declaration as its construct: theorems, definitions, the axioms, a
  product type, a sum type, an enumeration, an interface and its
  implementations;
- `uses` edges from each theorem to what its statement names and to the lemmas
  its proof cites, with `part` on the edge saying which;
- `inherits` from `ColouredPoint` to `Point`, and `implements` from each
  instance to `Sized`;
- `depends_on` between the files, from their `import` lines;
- `even_or_odd` carrying `meta.sorry` and the facet `proof.incomplete`.

`tests/test_examples.py` holds each of those to the sources here.

## What is not claimed

codecarto reads the text and runs no Lean, so the map says what the sources
spell and not what Lean accepts. With a toolchain, `lake build` in this
directory is the check that they compile.
