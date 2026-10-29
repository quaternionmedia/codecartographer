"""Circles packed tight in the order given, and the smallest circle round them.

A port of d3-hierarchy 3.1.2's `packSiblings` and `packEnclose`, which the
canvas's own outlines are drawn by (`compound_layout.ts`), under d3's licence
(REUSE.toml, LICENSES/ISC.txt):

    Copyright 2010-2021 Mike Bostock

    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
    SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION
    OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
    CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

Each circle is placed tangent to two on the front chain, nearest the middle, so
the pack is as dense as circles allow, and a circle's place depends only on the
circles before it: the same circles in the same order are always packed the
same way. The enclosing circle's shuffle is d3's, from a fixed seed, so it is
the same every time too.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Circle:
    x: float
    y: float
    r: float


def pack(radii: list[float], gap: float = 0.0) -> tuple[list[tuple[float, float]], float]:
    """Circles of `radii`, in that order, packed `gap` apart round the middle
    of the smallest circle enclosing them. Returns each centre, relative to
    that middle, and its radius."""
    circles = [Circle(0.0, 0.0, r + gap / 2) for r in radii]
    if not circles:
        return [], 0.0
    radius = _pack_siblings(circles)
    return [(c.x, c.y) for c in circles], max(radius - gap / 2, max(radii))


def enclose(circles: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    """The smallest circle enclosing `(x, y, r)` circles: its centre and radius."""
    found = _enclose([Circle(x, y, r) for x, y, r in circles])
    return (found.x, found.y, found.r) if found else (0.0, 0.0, 0.0)


# ── d3-hierarchy's siblings.js ──────────────────────────────────────────────


def _place(b: Circle, a: Circle, c: Circle) -> None:
    dx, dy = b.x - a.x, b.y - a.y
    d2 = dx * dx + dy * dy
    if d2:
        a2 = (a.r + c.r) ** 2
        b2 = (b.r + c.r) ** 2
        if a2 > b2:
            x = (d2 + b2 - a2) / (2 * d2)
            y = math.sqrt(max(0.0, b2 / d2 - x * x))
            c.x, c.y = b.x - x * dx - y * dy, b.y - x * dy + y * dx
        else:
            x = (d2 + a2 - b2) / (2 * d2)
            y = math.sqrt(max(0.0, a2 / d2 - x * x))
            c.x, c.y = a.x + x * dx - y * dy, a.y + x * dy + y * dx
    else:
        c.x, c.y = a.x + c.r, a.y


def _intersects(a: Circle, b: Circle) -> bool:
    dr = a.r + b.r - 1e-6
    dx, dy = b.x - a.x, b.y - a.y
    return dr > 0 and dr * dr > dx * dx + dy * dy


class _Node:
    __slots__ = ("c", "next", "previous")

    def __init__(self, circle: Circle):
        self.c = circle
        self.next: _Node | None = None
        self.previous: _Node | None = None


def _score(node: _Node) -> float:
    a, b = node.c, node.next.c
    ab = a.r + b.r
    dx = (a.x * b.r + b.x * a.r) / ab
    dy = (a.y * b.r + b.y * a.r) / ab
    return dx * dx + dy * dy


def _pack_siblings(circles: list[Circle]) -> float:
    n = len(circles)
    a = circles[0]
    a.x = a.y = 0.0
    if n == 1:
        return a.r
    b = circles[1]
    a.x, b.x, b.y = -b.r, a.r, 0.0
    if n == 2:
        return a.r + b.r
    c = circles[2]
    _place(b, a, c)
    na, nb, nc = _Node(a), _Node(b), _Node(c)
    na.next = nc.previous = nb
    nb.next = na.previous = nc
    nc.next = nb.previous = na
    i = 3
    while i < n:
        c = circles[i]
        _place(na.c, nb.c, c)
        node = _Node(c)
        # The nearest circle on the front chain this one overlaps, if any,
        # nearness being distance along the chain.
        j, k, sj, sk = nb.next, na.previous, nb.c.r, na.c.r
        retried = False
        while True:
            if sj <= sk:
                if _intersects(j.c, node.c):
                    nb = j
                    na.next, nb.previous = nb, na
                    retried = True
                    break
                sj += j.c.r
                j = j.next
            else:
                if _intersects(k.c, node.c):
                    na = k
                    na.next, nb.previous = nb, na
                    retried = True
                    break
                sk += k.c.r
                k = k.previous
            if j is k.next:
                break
        if retried:
            continue
        # Insert it between a and b, then find the pair nearest the middle.
        node.previous, node.next = na, nb
        na.next = nb.previous = nb = node
        best = _score(na)
        at = node.next
        while at is not nb:
            score = _score(at)
            if score < best:
                na, best = at, score
            at = at.next
        nb = na.next
        i += 1
    chain = [nb.c]
    at = nb.next
    while at is not nb:
        chain.append(at.c)
        at = at.next
    e = _enclose(chain)
    for circle in circles:
        circle.x -= e.x
        circle.y -= e.y
    return e.r


# ── d3-hierarchy's enclose.js ───────────────────────────────────────────────


def _lcg():
    state = 1

    def random() -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) % 4294967296
        return state / 4294967296

    return random


def _shuffle(items: list, random) -> list:
    m = len(items)
    while m:
        i = int(random() * m)
        m -= 1
        items[m], items[i] = items[i], items[m]
    return items


def _enclose(circles: list[Circle]) -> Circle | None:
    circles = _shuffle(list(circles), _lcg())
    basis: list[Circle] = []
    e: Circle | None = None
    i = 0
    while i < len(circles):
        p = circles[i]
        if e is not None and _encloses_weak(e, p):
            i += 1
        else:
            basis = _extend_basis(basis, p)
            e = _enclose_basis(basis)
            i = 0
    return e


def _extend_basis(basis: list[Circle], p: Circle) -> list[Circle]:
    if _encloses_weak_all(p, basis):
        return [p]
    for b in basis:
        if _encloses_not(p, b) and _encloses_weak_all(_enclose2(b, p), basis):
            return [b, p]
    for i in range(len(basis) - 1):
        for j in range(i + 1, len(basis)):
            bi, bj = basis[i], basis[j]
            if (_encloses_not(_enclose2(bi, bj), p) and _encloses_not(_enclose2(bi, p), bj)
                    and _encloses_not(_enclose2(bj, p), bi)
                    and _encloses_weak_all(_enclose3(bi, bj, p), basis)):
                return [bi, bj, p]
    raise ValueError("no circle encloses these")


def _encloses_not(a: Circle, b: Circle) -> bool:
    dr = a.r - b.r
    dx, dy = b.x - a.x, b.y - a.y
    return dr < 0 or dr * dr < dx * dx + dy * dy


def _encloses_weak(a: Circle, b: Circle) -> bool:
    dr = a.r - b.r + max(a.r, b.r, 1.0) * 1e-9
    dx, dy = b.x - a.x, b.y - a.y
    return dr > 0 and dr * dr > dx * dx + dy * dy


def _encloses_weak_all(a: Circle, basis: list[Circle]) -> bool:
    return all(_encloses_weak(a, b) for b in basis)


def _enclose_basis(basis: list[Circle]) -> Circle:
    if len(basis) == 1:
        return Circle(basis[0].x, basis[0].y, basis[0].r)
    if len(basis) == 2:
        return _enclose2(*basis)
    return _enclose3(*basis)


def _enclose2(a: Circle, b: Circle) -> Circle:
    x21, y21, r21 = b.x - a.x, b.y - a.y, b.r - a.r
    length = math.sqrt(x21 * x21 + y21 * y21)
    return Circle((a.x + b.x + x21 / length * r21) / 2, (a.y + b.y + y21 / length * r21) / 2,
                  (length + a.r + b.r) / 2)


def _enclose3(a: Circle, b: Circle, c: Circle) -> Circle:
    x1, y1, r1 = a.x, a.y, a.r
    x2, y2, r2 = b.x, b.y, b.r
    x3, y3, r3 = c.x, c.y, c.r
    a2, a3, b2, b3 = x1 - x2, x1 - x3, y1 - y2, y1 - y3
    c2, c3 = r2 - r1, r3 - r1
    d1 = x1 * x1 + y1 * y1 - r1 * r1
    d2 = d1 - x2 * x2 - y2 * y2 + r2 * r2
    d3 = d1 - x3 * x3 - y3 * y3 + r3 * r3
    ab = a3 * b2 - a2 * b3
    xa = (b2 * d3 - b3 * d2) / (ab * 2) - x1
    xb = (b3 * c2 - b2 * c3) / ab
    ya = (a3 * d2 - a2 * d3) / (ab * 2) - y1
    yb = (a2 * c3 - a3 * c2) / ab
    qa = xb * xb + yb * yb - 1
    qb = 2 * (r1 + xa * xb + ya * yb)
    qc = xa * xa + ya * ya - r1 * r1
    r = -((qb + math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa) if abs(qa) > 1e-6 else qc / qb)
    return Circle(x1 + xa + xb * r, y1 + ya + yb * r, r)
