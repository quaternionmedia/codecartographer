"""What a Showcase draws of a parse: its code, not its imports, and a folder of prose as one dot.

A Showcase colours each file by the code in it (`show_layout.showcase`). Two
things a parse holds say little there and weigh a great deal:

- **An import is a link, not a dot.** A parse holds each name a file imports
  as a node of the file's -- `Sequence`, `alembic.op` -- two in every five of
  the corpus's code maps' nodes, and nearly half of them name nothing the
  repository holds. Where a file imports another of the repository's, the
  parse joins the two (`depends_on`), and a Showcase draws that as its
  imports link. So a Showcase leaves every import node out, and every link to
  or from one.
- **A folder of prose is one dot.** A directory holding nothing but markdown,
  however deep, is drawn as one dot as large as the lines its pages hold
  (`meta.lines`, `show_layout.lines_scale`), in place of a dot for each page
  and each folder of pages. Its pages are files a Showcase has nothing to
  colour in.

`thinned` takes a parse as the stream sends it -- its nodes and edges, each a
dict -- and the lines of each markdown file read, by file id, and returns what
a Showcase draws. `thin_graph` does the same to a graph built whole.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, AsyncIterator

import networkx as nx

MARKDOWN = (".md", ".mdx", ".markdown")
_HOLDS = frozenset({"contains", "field_of"})


def is_showcase(layout: str) -> bool:
    """Whether `layout`, as the window names it (`Showcase(dot=2,...)`), is a Showcase."""
    from codecarto.services.position_service import layout_key, layout_spec

    return layout_key(layout_spec(layout)[0]) == "showcase_layout"


def is_markdown(name: Any) -> bool:
    return str(name or "").lower().endswith(MARKDOWN)


def markdown_lines(text: str) -> int:
    """The lines of a markdown page, as a Showcase measures a folder of them."""
    return len(text.splitlines())


def _kind(attrs: dict) -> Any:
    nested = attrs.get("metadata") if isinstance(attrs.get("metadata"), dict) else {}
    return attrs.get("kind") or nested.get("kind")


def _plan(nodes: dict[str, dict], edges: list[tuple[str, str, dict]],
          lines: dict[str, int]) -> tuple[set[str], dict[str, dict]]:
    """The ids a Showcase leaves out, and the meta each folded directory takes."""
    held: dict[str, list[str]] = defaultdict(list)
    parent: dict[str, str] = {}
    for source, target, attrs in edges:
        if _kind(attrs) in _HOLDS and source in nodes and target in nodes:
            held[source].append(target)
            parent.setdefault(target, source)

    gone: set[str] = set()

    def leave_out(key: str) -> None:
        # With all it holds: an import holds the names it brings in, which,
        # left with nothing holding them, the canvas gave the nearest outline.
        below = [key]
        while below:
            node = below.pop()
            if node not in gone:
                gone.add(node)
                below.extend(held[node])

    for key, node in nodes.items():
        if _kind(node) == "import":
            leave_out(key)

    prose: dict[str, tuple[bool, int, int]] = {}   # a directory: only markdown, its pages, their lines

    def walk(key: str) -> tuple[bool, int, int]:
        if key in prose:
            return prose[key]
        prose[key] = (False, 0, 0)                 # a cycle holds no prose
        only, pages, count = True, 0, 0
        for child in held[key]:
            kind = _kind(nodes[child])
            if kind == "directory":
                sub = walk(child)
                only, pages, count = only and sub[0], pages + sub[1], count + sub[2]
            elif kind == "file":
                if is_markdown(nodes[child].get("label") or child):
                    pages, count = pages + 1, count + lines.get(child, 0)
                else:
                    only = False
        prose[key] = (only and pages > 0, pages, count)
        return prose[key]

    folded: dict[str, dict] = {}
    for key, node in nodes.items():
        if _kind(node) != "directory" or not walk(key)[0]:
            continue
        above = parent.get(key)
        if above is not None and _kind(nodes[above]) == "directory" and walk(above)[0]:
            continue                               # folded into the directory above
        _, pages, count = prose[key]
        folded[key] = {"lines": count, "pages": pages}
        for child in held[key]:
            leave_out(child)
    return gone, folded


def thinned(nodes: list[dict], edges: list[dict], lines: dict[str, int]) -> tuple[list[dict], list[dict]]:
    """`nodes` and `edges`, as the stream sends them, as a Showcase draws them."""
    by_id = {str(node.get("id")): node for node in nodes}
    pairs = [(str(edge.get("source")), str(edge.get("target")), edge) for edge in edges]
    gone, folded = _plan(by_id, pairs, lines)
    kept = []
    for key, node in by_id.items():
        if key in gone:
            continue
        if key in folded:
            node = {**node, "meta": {**(node.get("meta") or {}), **folded[key]}}
        kept.append(node)
    return kept, [edge for source, target, edge in pairs if source not in gone and target not in gone]


def thin_graph(graph: nx.DiGraph, lines: dict[str, int]) -> None:
    """`graph`, built whole, made what a Showcase draws, in place."""
    nodes = {str(key): dict(data) for key, data in graph.nodes(data=True)}
    pairs = [(str(source), str(target), dict(data)) for source, target, data in graph.edges(data=True)]
    gone, folded = _plan(nodes, pairs, lines)
    graph.remove_nodes_from([key for key in graph.nodes if str(key) in gone])
    for key, meta in folded.items():
        graph.nodes[key]["meta"] = {**(graph.nodes[key].get("meta") or {}), **meta}


async def without_imports(stream: AsyncIterator[str]) -> AsyncIterator[str]:
    """A stream laid out as it arrives, with no import nodes and no link to or
    from one. Its folders of prose are not folded: that takes the whole tree's
    pages read, which only a stream laid out whole (`stream_floor`) waits for."""
    import json

    imports: set[str] = set()
    async for chunk in stream:
        event = data = None
        for line in chunk.splitlines():
            if line.startswith("event: "):
                event = line[len("event: "):].strip()
            elif line.startswith("data: "):
                data = line[len("data: "):]
        if event in ("node", "edge") and data is not None:
            try:
                item = json.loads(data)
            except ValueError:
                item = None
            if isinstance(item, dict):
                if event == "node" and _kind(item) == "import":
                    imports.add(str(item.get("id")))
                    continue
                if event == "edge" and (str(item.get("source")) in imports or str(item.get("target")) in imports):
                    continue
        yield chunk
