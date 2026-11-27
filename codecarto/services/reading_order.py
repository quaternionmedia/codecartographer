"""Reading order: a graph placed left to right, the way its arrows read.

`place` returns where each node goes, in the canvas's units. It lays out
nothing else and draws nothing: `reading_order_layout` hands its places to the
serializer every graph goes through.

**A graph whose nodes say their `column`** is placed as a reading. Four
columns run left to right -- `who`, `instruction`, `question`, `answerer` --
and each chain of edges across them is a row, so a chain is a straight line:
the node that starts it, what it asked for, the question that raised, the node
that answered. A node in several rows stands at the middle of them. A
`beneath` node is tucked under the row of the node that points at it, and a
`beneath` node it points at stands beside it, so what belongs to one row
stays with that row. `over` and `head` stand above the rows and `under`
below, so an edge to one of them leaves the reading upward or downward and
never runs along it.

Rows are ordered by `rank` first, a node's own say in how far down it goes,
then rows that hold an instruction before rows that hold none, then by the
name of whatever starts the row, then of whatever ends it, so the rows of one
name are neighbours and its edges do not cross other names'.

The spacing is for names drawn at the size the canvas keeps them readable at:
a row leaves room for a name above its node, and a column for a name of
`interaction_graph.LABEL` characters beside or above it.

**Any other graph** is placed by how far each node is along its arrows: a
node nothing points at stands at the left, and each other node one column
right of the furthest node that points at it. Nodes on a cycle share the
column after the last.

What this cannot do: uncross every edge. Rows are ordered once, by name; a
name that answers rows far apart still has edges that cross the rows between,
and an edge to a node above or below the rows crosses the rows on its way.
"""

from __future__ import annotations

from typing import Any, Hashable

WHO, INSTRUCTION_COLUMN, QUESTION_COLUMN, ANSWERER = "who", "instruction", "question", "answerer"
HEAD, OVER, UNDER, BENEATH = "head", "over", "under", "beneath"
COLUMNS = (WHO, INSTRUCTION_COLUMN, QUESTION_COLUMN, ANSWERER, HEAD, OVER, UNDER, BENEATH)

# Where each column of the reading stands. The two outer gaps are narrower:
# the names at the ends are written outward, so only the middle columns' names
# need the room between them.
X = {WHO: 0.0, INSTRUCTION_COLUMN: 130.0, QUESTION_COLUMN: 345.0, ANSWERER: 475.0}

ROW = 44.0
"""From one row to the next: a node, the name above it, and air."""

NAME_GAP = 30.0
"""The least between two nodes at an end of the reading, whose names are beside them."""

CHAR, PAD, LEAST = 8.0, 40.0, 90.0
"""The width of one character of a name at the size the canvas keeps names
readable at when it frames a graph this tall, the air beside a name, and the
least a node above or below the rows takes."""

OVER_GAP, HEAD_GAP, UNDER_GAP = 70.0, 30.0, 56.0
"""From the first row up to the nodes above it, from those to the head, and
from the last row down to the nodes below."""

BENEATH_GAP, BENEATH_ROOM = 30.0, 52.0
"""From a row down to what is tucked under it, and how much further down the
next row then starts: room for the name written below a tucked node."""

OVER_START, UNDER_START = X[QUESTION_COLUMN], X[INSTRUCTION_COLUMN] + 160.0
"""Where the nodes above the rows start, and the nodes below them that the
start of the reading does not point at. Both are well right of the
instruction column, so an edge from that column leans away from it at once
and clears what is tucked under the rows it passes."""

STEP = 180.0
"""Between columns of a graph that names none."""

LAST = chr(0x10FFFF)
"""Sorts after every name: a row nothing ends comes after the rows of the
names that end the others."""

Place = dict[Hashable, tuple[float, float]]


def place(graph: Any) -> Place:
    """Where each node of `graph` goes, in the canvas's units."""
    nodes = list(graph.nodes(data=True))
    if nodes and all(data.get("column") in COLUMNS for _, data in nodes):
        return _reading(graph)
    return _along_the_arrows(graph)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _spread(wanted: list[tuple[float, Hashable]], gap: float) -> dict[Hashable, float]:
    """Each node at the height it wants, moved down just far enough to clear the one above."""
    placed: dict[Hashable, float] = {}
    last: float | None = None
    for y, node in sorted(wanted, key=lambda pair: pair[0]):
        y = y if last is None else max(y, last + gap)
        placed[node] = last = y
    return placed


def _reading(graph: Any) -> Place:
    column = {node: data["column"] for node, data in graph.nodes(data=True)}
    label = {node: str(data.get("label") or node).lower() for node, data in graph.nodes(data=True)}
    rank = {node: int(data.get("rank") or 0) for node, data in graph.nodes(data=True)}
    seen = {node: index for index, node in enumerate(graph.nodes)}
    of = {name: [node for node in graph.nodes if column[node] == name] for name in COLUMNS}

    def joined(source_column: str, target_column: str) -> dict[Hashable, Hashable]:
        """For each node of one column, the first node of another that points at it."""
        found: dict[Hashable, Hashable] = {}
        for source, target in graph.edges():
            if column[source] == source_column and column[target] == target_column:
                found.setdefault(target, source)
        return found

    starts = joined(WHO, INSTRUCTION_COLUMN)
    raised = joined(INSTRUCTION_COLUMN, QUESTION_COLUMN)
    asked = joined(WHO, QUESTION_COLUMN)
    ends: dict[Hashable, Hashable] = {}
    for source, target in graph.edges():
        if column[source] == QUESTION_COLUMN and column[target] == ANSWERER:
            ends.setdefault(source, target)

    # A row is one chain: who, instruction, question, answerer; any may be absent.
    rows: list[tuple[Any, Any, Any, Any]] = []
    for instruction in of[INSTRUCTION_COLUMN]:
        questions = [q for q in of[QUESTION_COLUMN] if raised.get(q) == instruction]
        for question in questions or [None]:
            rows.append((starts.get(instruction), instruction, question,
                         ends.get(question) if question is not None else None))
    for question in of[QUESTION_COLUMN]:
        if question not in raised:
            rows.append((asked.get(question), None, question, ends.get(question)))

    def order(row: tuple[Any, Any, Any, Any]) -> tuple[Any, ...]:
        who, instruction, question, answerer = row
        present = [node for node in row if node is not None]
        return (max(rank[node] for node in present),
                instruction is None,
                label[who] if who is not None else "",
                label[answerer] if answerer is not None else LAST,
                min(seen[node] for node in present))

    rows.sort(key=order)

    # What is tucked under a row: a `beneath` node goes with the first node of
    # the reading that points at it, and the row under that one starts lower.
    carries: dict[Hashable, list[Hashable]] = {}
    carried: set[Hashable] = set()
    for source, target in graph.edges():
        if column[target] == BENEATH and column[source] in X and target not in carried:
            carries.setdefault(source, []).append(target)
            carried.add(target)
    height: dict[int, float] = {}
    down = 0.0
    for index, row in enumerate(rows):
        height[index] = down
        ends_here = any(node in carries and not any(node in later for later in rows[index + 1:])
                        for node in row)
        down += ROW + (BENEATH_ROOM if ends_here else 0.0)

    found: Place = {}
    wanted: dict[str, dict[Hashable, list[float]]] = {name: {} for name in X}
    for index, row in enumerate(rows):
        for name, node in zip(X, row):
            if node is not None:
                wanted[name].setdefault(node, []).append(height[index])
    below = down
    for name in X:
        asks: list[tuple[float, Hashable]] = []
        for node in of[name]:
            if node in wanted[name]:
                asks.append((_mean(wanted[name][node]), node))
            else:
                # In no row: an end of the reading that only an edge to above
                # or below reaches. It goes under the rows.
                asks.append((below, node))
                below += NAME_GAP
        gap = NAME_GAP if name in (WHO, ANSWERER) else ROW
        for node, y in _spread(asks, gap).items():
            found[node] = (X[name], y)

    def room(node: Hashable) -> float:
        """The width a node above or below the rows takes with its name."""
        return max(LEAST, len(label[node]) * CHAR + PAD)

    # Above: from the question column on, so an edge up from the instruction
    # column leans away from it at once and clears what is tucked under the
    # rows it passes. What points at the head comes first, under it; then the
    # rest; each by name and as far right as the name before it needs.
    top = -OVER_GAP
    to_head = {source for source, target in graph.edges()
               if column[source] == OVER and column[target] == HEAD}
    x = OVER_START
    under_head: list[float] = []
    for node in sorted(of[OVER], key=lambda node: (node not in to_head, label[node])):
        found[node] = (x, top)
        if node in to_head:
            under_head.append(x)
        x += room(node)
    for index, node in enumerate(of[HEAD]):
        found[node] = ((_mean(under_head) if under_head else OVER_START) + index * STEP,
                       top - HEAD_GAP)

    # Tucked under its row: each `beneath` node under the node that points
    # at it, and a `beneath` node that one points at a column to its right.
    across = sorted(X.values())
    for holder, tucked in carries.items():
        hx, hy = found[holder]
        for node in tucked:
            x = hx
            chain = [node]
            while chain:
                current = chain.pop()
                found[current] = (x, hy + BENEATH_GAP)
                x = next((step for step in across if step > x), x + STEP)
                chain.extend(target for _, target in graph.out_edges(current)
                             if column[target] == BENEATH and target not in found)
    for node in of[BENEATH]:
        if node not in found:
            # Pointed at by nothing in the reading: it goes under the rows.
            found[node] = (X[WHO], below)
            below += NAME_GAP

    # Below: what the start of the reading points at stands under that start,
    # and the rest from `UNDER_START` on, each by name and as far right as
    # the name before it needs.
    lowest = max([0.0] + [y for node, (_, y) in found.items() if column[node] in X]
                 + [y + BENEATH_ROOM - BENEATH_GAP for node, (_, y) in found.items()
                    if column[node] == BENEATH])
    bottom = lowest + UNDER_GAP
    from_start = {target for source, target in graph.edges()
                  if column[source] == WHO and column[target] == UNDER}
    x = X[WHO]
    for node in sorted((node for node in of[UNDER] if node in from_start), key=label.get):
        found[node] = (x, bottom)
        x += room(node)
    x = max(x, UNDER_START)
    for node in sorted((node for node in of[UNDER] if node not in from_start), key=label.get):
        # Its name is written under it, centred: half its room is to its left.
        found[node] = (x + room(node) / 2 - LEAST / 2, bottom)
        x += room(node)
    return found


def _along_the_arrows(graph: Any) -> Place:
    """Each node one column right of the furthest node that points at it."""
    waiting = {node: sum(1 for source in graph.predecessors(node) if source != node)
               for node in graph.nodes}
    depth = {node: 0 for node in graph.nodes}
    ready = [node for node in graph.nodes if waiting[node] == 0]
    done: set[Hashable] = set()
    while ready:
        node = ready.pop()
        done.add(node)
        for target in graph.successors(node):
            if target == node or target in done:
                continue
            depth[target] = max(depth[target], depth[node] + 1)
            waiting[target] -= 1
            if waiting[target] == 0:
                ready.append(target)
    # What is left is on a cycle, or behind one: it shares the next column.
    after = max((depth[node] for node in done), default=-1) + 1
    for node in graph.nodes:
        if node not in done:
            depth[node] = after

    rows: dict[int, int] = {}
    found: Place = {}
    for node in graph.nodes:
        row = rows.get(depth[node], 0)
        rows[depth[node]] = row + 1
        found[node] = (depth[node] * STEP, row * ROW)
    return found
