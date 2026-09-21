"""Where a figure is calculated, where it is stored, and where it is displayed.

**THE BOUNDARY, IN ONE PLACE.** `docs/architecture.md` states it in prose; this
file is what makes it a check rather than a hope. The estate views calculate one
thing -- a layout, through `PositionService` -- and resolve one thing -- the
palette's vocabulary for a kind, through `palette_service.vocabulary`. They
store nothing. They display the producer's caveat verbatim. Every other figure
on the screen is the producer's, or a count of the document's own rows.

Three faces of the boundary, each pinned below because each was found crossed:

- **Calculation does not depend on how the caller spelled its name.** The same
  layout came out five times larger for `Kamada_Kawai` than for `Kamada Kawai`,
  and an already-suffixed name raised, because the serializer normalised once
  for the lookup and compared the raw string for the spread.
- **Data documents carry no display constants.** Three hex colours rode in the
  topology metadata from the gravis era; the front end overwrote them on
  arrival, so they were a boundary crossed for nothing.
- **A seam that cannot be drawn as asked is a sentence, not a 500.** An unknown
  layout raised through the route and reached the browser as a fault in this
  service.

Seen red before trusted: the spread test against the unnormalised comparison;
the metadata test with the colours present; the unknown-layout test against the
routers before they caught `ValueError`; the storage test with `open(` written
into a service; the panel test with `localStorage` written into a panel.

WHAT THIS CANNOT SEE. Whether a panel recomputes a figure the document already
carries -- that is a reading, and the rule for it is in the architecture page:
a panel may map a stated figure to a style and may count the rows it was handed;
it never derives a figure the producer also states.
"""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx
import pytest
from fastapi.testclient import TestClient

from codecarto.models.plot_data import PlotOptions
from codecarto.services import estate_service, qmcp_client, topology_service
from codecarto.services.graph_serializer import GraphSerializer
from codecarto.services.qmcp_client import Reach

ROOT = Path(__file__).resolve().parents[1]

# The modules that read a seam. They may calculate a layout and resolve a
# palette; they may not persist, cache or write.
ESTATE_SERVICES = (
    "codecarto/services/estate_service.py",
    "codecarto/services/topology_service.py",
    "codecarto/services/capability_service.py",
    "codecarto/services/overview_service.py",
    "codecarto/services/qmcp_client.py",
)
ESTATE_ROUTERS = (
    "codecarto/routers/estate_router.py",
    "codecarto/routers/topology_router.py",
    "codecarto/routers/capability_router.py",
    "codecarto/routers/overview_router.py",
)
# Controls, not canvases, and not stores.
ESTATE_PANELS = (
    "web/src/layout/panels/estate_panel.ts",
    "web/src/layout/panels/topology_panel.ts",
    "web/src/layout/panels/capabilities_panel.ts",
    "web/src/layout/panels/overview_panel.ts",
    "web/src/features/estate/seam_client.ts",
    "web/src/features/estate/estate_service.ts",
    "web/src/features/estate/problem_view.ts",
    "web/src/features/estate/provenance.ts",
)


def _triangle() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
    return g


def _xs(gjgf: dict) -> list[float]:
    return sorted(round(n["metadata"]["x"], 6) for n in gjgf["nodes"].values())


# --- calculation ----------------------------------------------------------------

@pytest.mark.parametrize("spelling", ["Kamada Kawai", "Kamada_Kawai", "kamada-kawai",
                                      "kamada_kawai_layout", "KAMADA KAWAI"])
def test_a_layout_is_one_calculation_however_it_is_spelled(spelling):
    """Same positions, same spread, for every spelling the menu or a caller uses."""
    reference = GraphSerializer.serialize_to_gjgf(_triangle(), PlotOptions(layout="Kamada_Kawai"))
    spelled = GraphSerializer.serialize_to_gjgf(_triangle(), PlotOptions(layout=spelling))
    assert _xs(spelled) == _xs(reference), spelling


def test_the_menus_own_registry_names_lay_out():
    """The front end's menu is keyed by `<name>_layout`; each must reach the registry."""
    for name in ("spring_layout", "circular_layout", "compound_layout", "shell_layout",
                 "sorted_square_layout", "spectral_layout"):
        gjgf = GraphSerializer.serialize_to_gjgf(_triangle(), PlotOptions(layout=name))
        assert len(gjgf["nodes"]) == 3, name


def test_an_unknown_layout_is_a_value_error_naming_the_registered_ones():
    with pytest.raises(ValueError) as caught:
        GraphSerializer.serialize_to_gjgf(_triangle(), PlotOptions(layout="Nonsense"))
    assert "Registered:" in str(caught.value)
    assert "kamada_kawai_layout" in str(caught.value)


# --- display constants stay out of data -----------------------------------------

def test_topology_metadata_carries_no_colours():
    view = topology_service.render({"topology": "t", "boxes": [], "arrows": []})
    md = topology_service.metadata(view, {"source": "topology"})
    for key in md:
        assert not key.endswith("_color"), f"a display constant in the data layer: {key}"
    assert "caveat" in md and "kind" in md


# --- a seam that cannot be drawn as asked is a sentence -------------------------

def _corpus(tmp_path: Path) -> Path:
    registry = tmp_path / "ci" / "capability-registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text("schema: 1\ncapabilities:\n  - id: a/b\n    phase: design\n"
                        "    repo: o/r\n", encoding="utf-8")
    return tmp_path


def test_unknown_layout_on_every_estate_route_is_a_200_with_a_remedy(monkeypatch, tmp_path):
    monkeypatch.setattr(estate_service.capability_service, "CORPUS", _corpus(tmp_path))
    seam = tmp_path / "overview.json"
    seam.write_text('{"schema": 1, "scope": "s", "masthead": [], "sections": [{"title": "T", "rows": [["r"]]}]}',
                    encoding="utf-8")
    monkeypatch.setenv(estate_service.overview_service.SEAM_ENV, str(seam))

    def harness(path, base=None, remedy_404=None):
        return Reach(True, "http://h" + path, {
            "schema": 1, "source": "topology", "encoding": [],
            "payload": {"topology": "t", "level": 2, "caption": "", "status": "runs",
                        "marks": [], "boxes": [{"id": "a", "label": "a", "kind": "input"}],
                        "arrows": []}}, status=200)
    monkeypatch.setattr(qmcp_client, "fetch", harness)

    from codecarto.main import app

    client = TestClient(app)
    for route in ("/topology/gjgf", "/capabilities/gjgf", "/overview/gjgf"):
        answer = client.get(route, params={"layout": "Nonsense"})
        assert answer.status_code == 200, route
        results = answer.json()["results"]
        assert results.get("unreadable") is True, route
        assert "does not exist" in results["problem"], route
        assert "kamada_kawai_layout" in results["remedy"], route
        assert "graph" not in results, route
        # And a spelling the menu uses draws.
        drawn = client.get(route, params={"layout": "compound_layout"}).json()["results"]
        assert "graph" in drawn, route


# --- storage: the estate services and panels persist nothing --------------------

WRITES = re.compile(r"""open\([^)]*["'][wa]|write_text\(|write_bytes\(|\.write\(|pymongo|sqlite3|shelve|pickle\.dump|CacheService|GraphbaseService""")


@pytest.mark.parametrize("path", ESTATE_SERVICES + ESTATE_ROUTERS)
def test_estate_modules_store_nothing(path):
    source = (ROOT / path).read_text(encoding="utf-8")
    hits = [m.group(0) for m in WRITES.finditer(source)]
    assert not hits, f"{path} writes or persists: {hits}"


CLIENT_STORES = re.compile(r"localStorage|sessionStorage|indexedDB|document\.cookie")
CANVAS_IMPORTS = re.compile(r"from '[^']*(_renderer|/d3|streaming_renderer)[^']*'|from 'd3'")


@pytest.mark.parametrize("path", ESTATE_PANELS)
def test_estate_panels_are_controls_that_store_nothing(path):
    source = (ROOT / path).read_text(encoding="utf-8")
    assert not CLIENT_STORES.search(source), f"{path} stores in the browser"
    assert not CANVAS_IMPORTS.search(source), f"{path} imports a canvas; the drawing goes to the Graph panel"


@pytest.mark.parametrize("path", ESTATE_ROUTERS)
def test_estate_routers_never_raise_to_the_browser(path):
    """Absence is a sentence: no `HTTPException`, no bare `raise`, in an estate router."""
    source = (ROOT / path).read_text(encoding="utf-8")
    assert "HTTPException" not in source, path
    assert not re.search(r"^\s+raise\b", source, re.M), path
