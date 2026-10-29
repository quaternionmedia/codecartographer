"""A showgraph's code view held to a floor of nodes: drawn deeper where a project is small.

Drawn to its directories and files, a code map is three nodes for one
repository and six hundred for another, so a small project's showgraph showed
almost nothing of what codecarto reads. `floored` reads a parse's stream drawn
to its deepest and lets through the shallowest depth that holds at least
`floor` nodes: the directories and files alone when they reach it, their
symbols too when they do not, and their members too when even that falls
short -- all a repository has, when it has fewer.

The stream is the one `/parse/stream-url` sends (`unified_parser_service`):
the directories and files first, a `phase` event, then each file's symbols and
members as the file is parsed, and `done`. The directories and files are
counted at the `phase` event, or at the first node deeper than a file in a
stream that sends none:

- **A project they reach the floor for is drawn to them**, streamed as they
  came, and ended there, before any file is fetched.
- **A project they do not is drawn deeper, and laid out whole.** The stream
  places each file's symbols in a ring round the file as it arrives, where
  they pile on their neighbours'; here the whole parse is kept to the end,
  its members let through only if the directories, files and symbols fall
  short, and laid out once in the layout asked for -- for a showgraph, the
  Showcase, a disc round each file of what it holds -- and sent. It holds
  what the repository holds: a module a file imports from elsewhere is left
  out, as the files-deep map never had one.
- **A Showcase is drawn to its symbols at the least**, wherever its files
  reach the floor: it colours each file by the code in it, and drawn to its
  files alone it is a field of grey dots with nothing to colour. The window
  opens a showgraph's code view as one.

`done` says which depth was drawn (`depth`: 1 files, 2 symbols, 3 members),
the floor it was held to and how many nodes it holds.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

# The fewest nodes a showgraph's code map is drawn with, where the repository
# has that many: `show_router`'s views name it, the window streams with it.
CODE_FLOOR = 100

FILES, SYMBOLS, MEMBERS = 1, 2, 3


def _read(chunk: str) -> tuple[str | None, Any]:
    """An SSE chunk's event name and its data, or None for what it does not say."""
    event, data = None, None
    for line in chunk.splitlines():
        if line.startswith("event: "):
            event = line[len("event: "):].strip()
        elif line.startswith("data: "):
            data = line[len("data: "):]
    try:
        return event, json.loads(data) if data is not None else None
    except ValueError:
        return event, None


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _depth(node: dict) -> int:
    depth = node.get("depth")
    return depth if isinstance(depth, int) else FILES


def _least(layout: str) -> int:
    """The shallowest depth `layout` is drawn to: a Showcase's symbols, any other's files."""
    from codecarto.services.position_service import layout_key, layout_spec

    return SYMBOLS if layout_key(layout_spec(layout)[0]) == "showcase_layout" else FILES


def _done(payload: Any, depth: int, floor: int, nodes: int) -> str:
    said = dict(payload) if isinstance(payload, dict) else {}
    said.update(depth=depth, floor=floor, nodes=nodes)
    return _sse("done", said)


def _attrs(item: dict, drop: tuple[str, ...]) -> dict:
    """An item's attributes, those a gJGF edge keeps under `metadata` among them."""
    nested = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    return {**nested, **{k: v for k, v in item.items() if k not in drop and k != "metadata"}}


_HOLDS = frozenset({"contains", "field_of"})


def _held_within(nodes: dict[str, dict], edges: list[dict]) -> set[str]:
    """The ids of what the repository holds: each root directory, and what a
    contains or field_of edge from it reaches. A module a file imports from
    elsewhere is held by nothing in it, and is left out: the Map packs it in
    rows outside the repository, and the canvas drew the nearest directory's
    outline out round them."""
    held: dict[str, list[str]] = {}
    targets: set[str] = set()
    for edge in edges:
        if _attrs(edge, ("source", "target")).get("kind") in _HOLDS:
            source, target = str(edge.get("source")), str(edge.get("target"))
            if source in nodes and target in nodes:
                held.setdefault(source, []).append(target)
                targets.add(target)
    reached = [key for key, node in nodes.items() if _depth(node) == 0 and key not in targets]
    within = set(reached)
    while reached:
        for target in held.get(reached.pop(), []):
            if target not in within:
                within.add(target)
                reached.append(target)
    return within


def laid_out(nodes: list[dict], edges: list[dict], layout: str) -> list[dict]:
    """`nodes` placed by `layout` over the whole graph, as `GraphSerializer`
    places a parse, each with the side its name goes on where the layout says."""
    import networkx as nx

    from codecarto.models.plot_data import PlotOptions
    from codecarto.services.graph_serializer import GraphSerializer

    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node["id"], **_attrs(node, ("id", "x", "y", "label_at")))
    for edge in edges:
        graph.add_edge(edge["source"], edge["target"], **_attrs(edge, ("source", "target")))
    drawn = GraphSerializer.serialize_to_gjgf(graph, PlotOptions(layout=layout, type="d3")).get("nodes", {})
    for node in nodes:
        placed = drawn.get(node["id"]) or {}
        meta = placed.get("metadata") if isinstance(placed.get("metadata"), dict) else {}
        for key in ("x", "y", "label_at"):
            if key in placed:
                node[key] = placed[key]
            elif key in meta:
                node[key] = meta[key]
    return nodes


async def floored(stream: AsyncIterator[str], floor: int, layout: str = "Map") -> AsyncIterator[str]:
    """`stream`, a parse drawn to its deepest, cut to the shallowest depth holding `floor` nodes,
    and no shallower than `layout` is drawn to (`_least`)."""
    start = time.monotonic()
    least = _least(layout)
    waiting: list[str] = []          # the directories and files, until they are counted
    nodes: list[dict] = []           # a deepened project's, to its symbols
    members: list[dict] = []
    edges: list[dict] = []
    counted = deepened = False
    try:
        async for chunk in stream:
            event, payload = _read(chunk)
            node = payload if event == "node" and isinstance(payload, dict) else None
            if not counted and (event == "phase" or (node is not None and _depth(node) > FILES)):
                counted = True
                shown = [n for kind, n in map(_read, waiting) if kind == "node" and isinstance(n, dict)]
                if len(shown) >= floor and least <= FILES:
                    # Enough with the directories and files: no file is fetched.
                    for kept in waiting:
                        yield kept
                    elapsed = int((time.monotonic() - start) * 1000)
                    yield _done({"elapsed_ms": elapsed}, FILES, floor, len(shown))
                    return
                deepened = True
                for held in waiting:
                    kind, item = _read(held)
                    if kind == "node" and isinstance(item, dict):
                        nodes.append(item)
                    elif kind == "edge" and isinstance(item, dict):
                        edges.append(item)
                    elif kind != "meta":
                        # A note or a fetch's progress goes on; the count is said again at the end.
                        yield held
                waiting = []
            if not counted:
                if event == "done":
                    # Nothing past the files: all there is, as it came.
                    shown = sum(1 for kind, _ in map(_read, waiting) if kind == "node")
                    for kept in waiting:
                        yield kept
                    yield _done(payload, FILES, floor, shown)
                    return
                waiting.append(chunk)
                continue
            if node is not None:
                (members if _depth(node) >= MEMBERS else nodes).append(node)
            elif event == "edge" and isinstance(payload, dict):
                edges.append(payload)
            elif event == "done":
                # Each id once, the shallowest copy: a parser that names two
                # things alike sent both, and the canvas drew both.
                unique: dict[str, dict] = {}
                for item in nodes:
                    unique.setdefault(str(item.get("id")), item)
                ids = _held_within(unique, edges)
                if len(ids) < floor:
                    for item in members:
                        unique.setdefault(str(item.get("id")), item)
                    ids = _held_within(unique, edges)
                kept = [item for key, item in unique.items() if key in ids]
                joined = [e for e in edges if str(e.get("source")) in ids and str(e.get("target")) in ids]
                kept.sort(key=lambda n: (_depth(n), str(n.get("id"))))
                laid_out(kept, joined, layout)
                yield _sse("meta", {"nodeCount": len(kept), "edgeCount": len(joined), "layout": layout,
                                    "phase": "floor"})
                for item in kept:
                    yield _sse("node", item)
                for item in joined:
                    yield _sse("edge", item)
                deepest = max((_depth(n) for n in kept), default=FILES)
                yield _done(payload, max(deepest, FILES), floor, len(kept))
                return
            elif event != "meta" or not deepened:
                yield chunk
    finally:
        closing = getattr(stream, "aclose", None)
        if closing is not None:
            await closing()
