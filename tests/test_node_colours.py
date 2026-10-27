"""The canvas's node colours keep red and pink for what is to be noticed.

A node's colour says what it is. Red and pink stand out from everything else on
the canvas, so they are kept for a node a reader should notice -- a deprecated
one -- and for the canvas's own highlights (an error, a refusal, the ring's
danger), not spent on an ordinary kind: an import, a module, a loop, an async
function, an entry point. The abstraction-layer ramp keeps pink for its last,
seventh layer, used only when a lexicon has that many.

Every place a node is given a colour by its kind is read here: the default
palette, the layer ramp, the construct vocabulary, the Cargo graph's looks, the
Python parser's and the canvas's fallback for an import, and the dependency
plot's external dependency.
"""

import colorsys
import re
from pathlib import Path

import yaml

from codecarto.models.plot_data import DefaultPalette
from codecarto.services import cargo_service, construct_service
from codecarto.services.parsers import python_language_parser

ROOT = Path(__file__).resolve().parent.parent

# The CSS names the default palette uses, as the canvas draws them.
NAMED = {
    "gray": "#808080", "orange": "#ffa500", "green": "#008000", "violet": "#ee82ee",
    "purple": "#800080", "red": "#ff0000", "khaki": "#f0e68c", "gold": "#ffd700",
    "blue": "#0000ff", "lightblue": "#add8e6", "darkblue": "#00008b", "skyblue": "#87ceeb",
    "pink": "#ffc0cb", "maroon": "#800000", "salmon": "#fa8072", "darkcyan": "#008b8b",
    "olivedrab": "#6b8e23", "slateblue": "#6a5acd", "peru": "#cd853f",
}
# What may be red: a node a reader should notice.
NOTICED = {"deprecated"}


def _red_or_pink(colour: str) -> bool:
    hex_ = NAMED.get(colour.lower(), colour)
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", hex_), f"{colour!r} is a colour this test cannot read; name it in NAMED"
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    hue *= 360
    return sat > 0.3 and 0.15 < light < 0.92 and (hue >= 290 or hue <= 12)


def test_no_ordinary_kind_in_the_default_palette_is_red_or_pink():
    # Mutation: give `module` its red back -- and this fails.
    red = {base: c for base, c in DefaultPalette.colors.items() if base not in NOTICED and _red_or_pink(c)}
    assert red == {}, f"ordinary kinds drawn red or pink: {red}"


def test_the_layer_ramp_keeps_pink_for_its_last_layer_and_has_no_red():
    # Mutation: start the ramp at red again -- layer 0 is red, and this fails.
    ramp = construct_service.LAYER_RAMP
    assert not any(_red_or_pink(c) for c in ramp[:-1]), ramp


def test_no_construct_s_look_is_red_or_pink():
    vocabulary = yaml.safe_load((ROOT / "codecarto" / "data" / "constructs.yaml").read_text(encoding="utf-8"))
    entries = vocabulary.get("constructs") if isinstance(vocabulary, dict) else vocabulary
    looks = {entry["id"]: entry["look"]["color"] for entry in entries
             if isinstance(entry, dict) and isinstance(entry.get("look"), dict) and entry["look"].get("color")}
    assert looks, "no construct looks were read"
    red = {name: c for name, c in looks.items() if _red_or_pink(c)}
    assert red == {}, f"constructs drawn red or pink: {red}"


def test_no_cargo_look_is_red_or_pink():
    looks = {**{k: c for k, (_, c) in cargo_service.LOOKS.items()},
             **{f"target {k}": c for k, (_, c) in cargo_service.TARGET_LOOKS.items()}}
    red = {name: c for name, c in looks.items() if _red_or_pink(c)}
    assert red == {}, f"Cargo nodes drawn red or pink: {red}"


def test_an_import_and_an_external_dependency_are_not_red():
    assert not _red_or_pink(python_language_parser._PY_COLOR["import"])
    renderer = (ROOT / "web" / "src" / "features" / "graph" / "services" / "streaming_renderer.ts").read_text(encoding="utf-8")
    fallback = re.search(r"kind === 'import'\) node\.color = '(#[0-9a-fA-F]{6})'", renderer)
    assert fallback and not _red_or_pink(fallback.group(1)), "the canvas's fallback draws an import red"
    serializer = (ROOT / "codecarto" / "services" / "graph_serializer.py").read_text(encoding="utf-8")
    external = re.search(r'data\["color"\] = "([^"]+)"\s*# External dependencies', serializer)
    assert external and not _red_or_pink(external.group(1)), "an external dependency is drawn red"
