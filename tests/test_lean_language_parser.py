"""The Lean reader: declarations, what each uses, and where it stops."""

from __future__ import annotations

import hashlib

import pytest

from codecarto.models.source_data import Directory, File, Folder, RepoInfo
from codecarto.services.parsers.language_parser import ParserRegistry
from codecarto.services.parsers.lean_language_parser import (
    KINDS,
    LeanLanguageParser,
    read_file,
    tokenize,
)
from codecarto.services.unified_parser_service import UnifiedParserService

DEFS = """\
namespace Demo

inductive Shape where
  | circle (r : Nat) : Shape
  | rect (w h : Nat) : Shape

def Shape.area : Shape → Nat
  | .circle r => 3 * r * r
  | .rect w h => w * h

end Demo
"""

BASIC = """\
/-! A module doc that says theorem and def at the start of a line:
theorem not_a_declaration : False := sorry
-/
import Mathlib.Data.Nat.Basic
import Demo.Defs

open Nat

namespace Demo

/-- Doubling. -/
def double (n : Nat) : Nat := n + n

@[simp, norm_cast]
theorem double_eq (n : Nat) : double n = 2 * n := by
  unfold double
  omega

lemma double_pos {n : Nat} (h : 0 < n) : 0 < double n := by
  rw [double_eq]
  open Classical in
  exact Nat.mul_pos (by decide) h

theorem unfinished : ∀ n, double n = Shape.area (.circle n) := by
  intro n
  sorry

axiom choice_like : ∀ α : Type, Nonempty α → α

private noncomputable def pick (α : Type) [h : Nonempty α] : α := choice_like α h

structure Point where
  x : Nat
  y : Nat
  deriving Repr

structure Point3 extends Point where
  mk3 ::
  /-- depth -/
  z : Nat := 0

class Measurable (α : Type) where
  size : α → Nat
  size_nonneg : ∀ a, 0 ≤ size a

instance : Measurable Point where
  size p := p.x + p.y
  size_nonneg := fun _ => Nat.zero_le _

instance pointInhabited : Inhabited Point := ⟨⟨0, 0⟩⟩

inductive Color
  | red | green | blue
  deriving DecidableEq

example : double 2 = 4 := rfl

end Demo

#check Demo.double

notation "𝔻" => Demo.double
"""


def parse(*files: tuple[str, str], depth: int = 3):
    return LeanLanguageParser().parse_files(
        [File(name=path.rsplit("/", 1)[-1], url=path, raw=raw) for path, raw in files], depth=depth)


@pytest.fixture(scope="module")
def graph():
    return parse(("proj/Demo/Basic.lean", BASIC), ("proj/Demo/Defs.lean", DEFS))


def named(graph, label: str) -> tuple[str, dict]:
    found = [(n, d) for n, d in graph.nodes(data=True) if d["label"] == label]
    assert len(found) == 1, (label, [n for n, _ in found])
    return found[0]


def edges(graph, kind: str) -> dict[tuple[str, str], dict]:
    return {(graph.nodes[u]["label"], graph.nodes[v]["label"]): d
            for u, v, d in graph.edges(data=True) if d["kind"] == kind}


# ── the tokenizer ─────────────────────────────────────────────────────────────


def test_registered_for_lean_files():
    assert isinstance(ParserRegistry.get(".lean"), LeanLanguageParser)


def test_comments_nest_and_a_doc_comment_is_kept_as_its_first_line():
    """Mutation: end a block comment at its first `-/` -- `inner -/ still` is
    read as source and `still` is a token."""
    toks = tokenize("/- outer /- inner -/ still -/ a\n/-- First.\nSecond. -/ b -- c")
    assert [(t.kind, t.text) for t in toks] == [("ident", "a"), ("doc", "First."), ("ident", "b")]


def test_a_prime_ends_a_name_and_a_quote_opens_a_character():
    toks = tokenize("x' ≠ 'a' ∧ h.symm.1 \"theorem\" «my name».get?")
    assert [t.text for t in toks] == [
        "x'", "≠", "'a'", "∧", "h.symm", ".", "1", '"theorem"', "«my name».get?"]


@pytest.mark.parametrize("src", ['theorem t : "never closed', "/- never closed", 'r#"raw',
                                 "def f := (((", "⟩ ] } end end", "'", "@[", ""])
def test_any_text_is_read(src):
    read_file(src)
    assert "".join(t.text for t in tokenize("a b")) == "ab"


def test_a_token_knows_its_line_and_whether_it_begins_one():
    toks = tokenize("a b\n  c\n/- x\ny -/ d")
    assert [(t.text, t.line, t.col, t.first) for t in toks] == [
        ("a", 1, 0, True), ("b", 1, 2, False), ("c", 2, 2, True), ("d", 4, 5, True)]


# ── declarations ──────────────────────────────────────────────────────────────


def test_every_declaration_is_found_once_with_its_full_name(graph):
    """A keyword in a module doc, a string or a comment declares nothing, and
    `open Classical in` inside a proof does not end it. Mutation: read `open`
    as a command wherever it begins a line -- `double_pos` ends on the line
    above its `open`."""
    top = {d["meta"].get("qualified") or d["label"]: d["kind"]
           for _, d in graph.nodes(data=True) if d["depth"] == 2}
    assert top == {
        "Demo.double": "def", "Demo.double_eq": "theorem", "Demo.double_pos": "theorem",
        "Demo.unfinished": "theorem", "Demo.choice_like": "axiom", "Demo.pick": "def",
        "Demo.Point": "structure", "Demo.Point3": "structure", "Demo.Measurable": "class",
        "Measurable Point": "instance", "Demo.pointInhabited": "instance",
        "Demo.Color": "inductive", "example": "example", "𝔻": "macro",
        "Demo.Shape": "inductive", "Demo.Shape.area": "def",
    }
    _, double_pos = named(graph, "double_pos")
    assert (double_pos["line"], double_pos["meta"]["line_end"]) == (19, 22)


def test_every_kind_emitted_is_declared(graph):
    assert {d["kind"] for _, d in graph.nodes(data=True) if d["language"] == "lean"} <= set(KINDS)


def test_a_theorem_carries_its_statement_and_how_it_is_proved(graph):
    _, eq = named(graph, "double_eq")
    assert eq["meta"]["statement"] == "double n = 2 * n"
    assert (eq["meta"]["proof"], eq["meta"]["keyword"]) == ("tactic", "theorem")
    assert eq["meta"]["attributes"] == ["simp", "norm_cast"]
    assert named(graph, "double_pos")[1]["meta"]["keyword"] == "lemma"
    assert named(graph, "example")[1]["meta"]["proof"] == "term"
    assert named(graph, "double")[1]["meta"]["doc"] == "Doubling."
    assert "proof" not in named(graph, "choice_like")[1]["meta"]


def test_a_sorry_marks_the_declaration_unproved(graph):
    """Mutation: misspell the `sorry` key under Lean's `meta:` in
    constructs.yaml -- the count is still carried and the facet is gone."""
    _, unfinished = named(graph, "unfinished")
    assert unfinished["meta"]["sorry"] == 1
    assert unfinished["meta"]["facets"] == ["proof.incomplete"]
    assert unfinished["construct"] == "proof.theorem"
    _, proved = named(graph, "double_eq")
    assert "sorry" not in proved["meta"] and "facets" not in proved["meta"]


def test_modifiers_are_qualifiers(graph):
    _, pick = named(graph, "pick")
    assert pick["meta"]["qualifiers"] == ["private", "noncomputable"]
    assert pick["meta"]["facets"] == ["linkage.internal"]


def test_a_structure_holds_its_fields_and_an_inductive_its_constructors(graph):
    """`mk3 ::` names a constructor, and a doc comment above a field is that
    field's."""
    contains = edges(graph, "contains")
    assert {child for (parent, child) in contains if parent == "Point"} == {"x", "y"}
    assert {child for (parent, child) in contains if parent == "Point3"} == {"z"}
    assert {child for (parent, child) in contains if parent == "Measurable"} == {"size", "size_nonneg"}
    assert {child for (parent, child) in contains if parent == "Color"} == {"red", "green", "blue"}
    assert {child for (parent, child) in contains if parent == "Shape"} == {"circle", "rect"}
    assert named(graph, "y")[1]["meta"]["type_str"] == "Nat"
    _, z = named(graph, "z")
    assert (z["meta"]["type_str"], z["meta"]["doc"], z["depth"]) == ("Nat", "depth", 3)
    assert named(graph, "size_nonneg")[1]["meta"]["type_str"] == "∀ a, 0 ≤ size a"
    assert named(graph, "rect")[1]["meta"]["type_str"] == "(w h : Nat) : Shape"


def test_an_inductive_with_bare_constructors_is_an_enumeration(graph):
    """Mutation: misspell `enumeration` in the `refine` rule for `inductive`
    in constructs.yaml -- `Color` is a sum type."""
    assert named(graph, "Color")[1]["construct"] == "type.enumeration"
    assert named(graph, "Shape")[1]["construct"] == "type.sum"
    assert named(graph, "Point")[1]["meta"]["sides"] == 3  # two fields, the fewest sides


# ── relations ─────────────────────────────────────────────────────────────────


def test_a_statement_and_a_proof_use_what_they_name(graph):
    """`part` tells what a theorem is about from what its proof cites.
    Mutation: file every reference under the body -- `double_pos` uses
    `double` in its body, and this fails."""
    uses = edges(graph, "uses")
    assert uses[("double_eq", "double")]["part"] == "both"
    assert uses[("double_pos", "double")]["part"] == "statement"
    assert uses[("double_pos", "double_eq")]["part"] == "body"
    assert uses[("pick", "choice_like")]["part"] == "body"
    assert uses[("𝔻", "double")] == {"kind": "uses", "weight": 1.0, "part": "body", "resolution": "exact"}
    assert uses[("unfinished", "Shape.area")]["resolution"] == "namespace"
    assert ("double", "double") not in uses


def test_extends_and_instances(graph):
    assert set(edges(graph, "inherits")) == {("Point3", "Point")}
    assert set(edges(graph, "implements")) == {("Measurable Point", "Measurable")}
    # `Inhabited` is declared nowhere in the batch, so nothing is drawn to it.
    assert named(graph, "pointInhabited")[1]["meta"]["class"] == "Inhabited"


def test_a_name_is_found_as_lean_scopes_it():
    """As written, then through each enclosing namespace, then through each
    `open`; a dotted name by its prefixes. Mutation: look a name up only as
    written -- `inner`, `opened` and `closed` find nothing."""
    g = parse(("A.lean", """\
namespace Geo
theorem base : True := trivial
namespace Deep
theorem inner : True := base
end Deep
end Geo

namespace Other
open Geo
theorem opened : True := base
theorem dotted : True := Geo.base.elim
theorem rooted : True := _root_.Geo.base
theorem closed : True := Deep.inner
end Other

theorem full : True := Geo.Deep.inner
"""))
    uses = {pair: d["resolution"] for pair, d in edges(g, "uses").items()}
    assert uses == {
        ("inner", "base"): "namespace", ("opened", "base"): "open", ("dotted", "base"): "exact",
        ("rooted", "base"): "exact", ("closed", "inner"): "open", ("full", "inner"): "exact",
    }


def test_a_declarations_own_name_opens_its_namespace():
    g = parse(("A.lean", "def Nat.twice (n : Nat) := n + n\n"
                         "theorem Nat.twice_eq (n : Nat) : twice n = 2 * n := by omega\n"))
    assert set(edges(g, "uses")) == {("Nat.twice_eq", "Nat.twice")}


def test_a_local_is_not_a_declaration():
    """A binder, a `variable`, and a name `fun`, `intro` or `obtain` brings in
    are local, and a dotted name that begins with one is a projection.
    Mutation: skip the locals -- each theorem here uses `h`, `x` or `f`."""
    g = parse(("A.lean", """\
def h : Nat := 0
def x : Nat := 1
def f : Nat := 2
variable (f : Nat → Nat)
theorem binder (h : 1 = 1) : 1 = 1 := h.symm
theorem introduced : ∀ n : Nat, n = n := by
  intro x
  rfl
theorem lambda : (fun x => x) 1 = 1 := rfl
theorem destructured (p : ∃ n, n = 1) : True := by
  obtain ⟨x, hx⟩ := p
  trivial
theorem applied : f 1 = f 1 := rfl
theorem global_use : x = 1 := rfl
"""))
    assert set(edges(g, "uses")) == {("global_use", "x")}


def test_a_name_two_declarations_could_be_draws_nothing_unless_one_is_here():
    """Mutation: take the first declaration of a name -- `far` uses a `helper`
    and this fails."""
    helper = "theorem helper : True := trivial\n"
    g = parse(("a/A.lean", helper + "theorem near : True := helper\n"),
              ("b/B.lean", helper),
              ("c/C.lean", "theorem far : True := helper\n"))
    uses = edges(g, "uses")
    assert set(uses) == {("near", "helper")}
    (near_id, _), = [(n, d) for n, d in g.nodes(data=True) if d["label"] == "near"]
    (target,) = [v for u, v, d in g.edges(data=True) if u == near_id]
    assert g.nodes[target]["file"] == "a/A.lean"


def test_at_depth_two_a_constructor_is_its_inductive():
    g = parse(("A.lean", "inductive T\n  | a\n  | b (n : Nat)\ndef pickA : T := T.a\n"), depth=2)
    assert {d["kind"] for _, d in g.nodes(data=True)} == {"inductive", "def"}
    assert set(edges(g, "uses")) == {("pickA", "T")}


def test_below_depth_two_nothing_is_drawn():
    assert len(parse(("A.lean", "def a := 1\n"), depth=1)) == 0


def test_a_command_ends_the_declaration_above_it():
    """`attribute [simp] b` is its own command, not part of `a`'s proof.
    Mutation: drop `attribute` from the commands the reader knows -- `a` uses
    `b`."""
    g = parse(("A.lean", "theorem b : True := trivial\ntheorem a : True := trivial\n"
                         "attribute [simp] b\n#print b\n"))
    assert edges(g, "uses") == {}


def test_a_deriving_clause_ends_the_fields():
    """Mutation: read the fields to the end of the declaration -- `x` is of
    type `Nat deriving Repr`."""
    g = parse(("A.lean", "structure P where\n  x : Nat\nderiving Repr\n"))
    assert named(g, "x")[1]["meta"]["type_str"] == "Nat"
    assert named(g, "P")[1]["meta"]["field_count"] == 1


def test_an_absolute_value_bar_is_not_a_constructor():
    """Mutation: take every bar outside brackets as a constructor's -- `n` is
    a constructor of `T`."""
    g = parse(("A.lean", "inductive T : Type\n  | mk : (n : Int) → |n| = n → T\n  | other\n"))
    assert {d["label"] for _, d in g.nodes(data=True) if d["kind"] == "constructor"} == {"mk", "other"}


# ── imports ───────────────────────────────────────────────────────────────────


def test_an_import_names_the_file_at_its_module_path(graph):
    relations = graph.graph["file_relations"]
    assert ("proj/Demo/Basic.lean", "proj/Demo/Defs.lean",
            {"kind": "depends_on", "resolution": "module-path"}) in relations
    assert ("proj/Demo/Basic.lean", "external::lean::Mathlib",
            {"kind": "depends_on", "resolution": "external"}) in relations
    assert len(relations) == 2
    mathlib = graph.nodes["external::lean::Mathlib"]
    assert (mathlib["kind"], mathlib["depth"], mathlib["meta"]) == ("external_module", 1, {"core": False})
    assert graph.graph["file_meta"]["proj/Demo/Basic.lean"] == {
        "imports": ["Mathlib.Data.Nat.Basic", "Demo.Defs"], "sorry_count": 1}


def test_an_import_two_files_could_be_or_that_names_a_missing_local_file_draws_nothing():
    """Two packages each with `Util/Basic.lean`, and `Demo.Gone` under a
    directory the batch holds. Mutation: draw an external module for every
    import that names no file -- `Demo` is drawn as one."""
    g = parse(("one/Util/Basic.lean", "def a := 1\n"), ("two/Util/Basic.lean", "def a := 1\n"),
              ("app/Demo/Main.lean", "import Util.Basic\nimport Demo.Gone\nimport Lean\n"))
    assert g.graph["file_relations"] == [
        ("app/Demo/Main.lean", "external::lean::Lean", {"kind": "depends_on", "resolution": "external"})]
    assert g.nodes["external::lean::Lean"]["meta"] == {"core": True}


# ── through the pipeline ──────────────────────────────────────────────────────


def _directory() -> Directory:
    def file(name: str, raw: str) -> File:
        return File(name=name, size=len(raw), raw=raw)

    demo = Folder(name="Demo", size=2, folders=[],
                  files=[file("Basic.lean", BASIC), file("Defs.lean", DEFS)])
    root = Folder(name="proj", size=1, files=[], folders=[demo])
    return Directory(info=RepoInfo(owner="test", name="proj", url=""), size=0, root=root)


def test_the_pipeline_hangs_declarations_from_their_files_and_joins_the_imports():
    g = UnifiedParserService.build_graph(_directory(), depth=3, extensions=None, annotate_lexicon=True)
    files = {d["label"]: n for n, d in g.nodes(data=True) if d.get("kind") == "file"}
    basic, defs = files["Basic.lean"], files["Defs.lean"]
    assert g.edges[basic, defs]["kind"] == "depends_on"
    assert g.edges[basic, "external::lean::Mathlib"]["resolution"] == "external"
    assert g.nodes[basic]["meta"]["sorry_count"] == 1
    assert "facets" not in g.nodes[basic]["meta"]  # the facet is a declaration's, not its file's
    held = {g.nodes[v]["label"] for _, v, d in g.out_edges(basic, data=True) if d["kind"] == "contains"}
    assert {"double", "double_eq", "Point", "Color"} <= held and "x" not in held
    # The lexicon join: a theorem is on the proof layer, a structure on data's.
    _, theorem = named(g, "double_eq")
    assert theorem["meta"]["lexicon_layers"][0]["layer_name"] == "Propositions & proof"
    _, pick = named(g, "pick")
    assert {ctx["group"] for ctx in pick["meta"]["lexicon_layers"]} == {"definition", "visibility", "evaluation"}


def test_a_tree_cached_before_lean_was_read_is_parsed_again(monkeypatch, tmp_path):
    """At 10 a `.lean` file's declarations are nodes; a graph of the same tree
    cached at 9 has the file and nothing in it. Mutation: leave
    GRAPH_SCHEMA_VERSION at 9 -- the graph cached at 9 is served."""
    import codecarto.services.cache_service as cache_svc
    from fastapi.testclient import TestClient

    from codecarto.main import app

    repos_dir = tmp_path / "cache" / "repos"
    monkeypatch.setattr(cache_svc, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(cache_svc, "_REPOS_DIR", repos_dir)
    monkeypatch.setattr(cache_svc, "_INDEX_FILE", repos_dir / "index.json")

    url = "https://github.com/test/before-lean"
    at_9 = hashlib.sha256(f"v9::{url}::2::Spring::{sorted([])}".encode()).hexdigest()[:16]
    old = {"graph": {"nodes": {"CACHED_AT_9": {"metadata": {"depth": 1, "kind": "file"}}},
                     "edges": []}, "metadata": {}}
    cache_svc.CacheService.set(f"test-before-lean::{at_9}", old, label="test/before-lean",
                               url=url, mode="2", layout="Spring")
    body = {
        "directory": {
            "info": {"url": url, "owner": "test", "name": "before-lean"},
            "size": 0,
            "root": {"name": "r", "size": 0, "folders": [],
                     "files": [{"name": "A.lean", "size": 30, "raw": "theorem t : True := trivial\n"}]},
            "is_partial": False,
        },
        "depth": 2,
        "layout": "Spring",
    }
    results = TestClient(app).post("/parse/unified", json=body).json()["results"]
    assert not results.get("from_cache") and "CACHED_AT_9" not in results["graph"]["nodes"]
    assert any(n.get("metadata", n).get("kind") == "theorem" for n in results["graph"]["nodes"].values())
