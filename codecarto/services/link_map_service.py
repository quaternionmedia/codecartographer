"""What a link actually put where, read from the map file the linker wrote.

**MEASURED, WHERE THE LINKER SCRIPT ONLY DECLARES.** A linker script says a
region is 512 KiB and that `.text` goes in it; how much of it `.text` then
fills is known only after the link, and the linker says so in the map it writes
when asked (`-Map=<file>`). This module reads that map -- in the two shapes the
linkers firmware is built with print it: GNU ld's (`arm-none-eabi-gcc
-Wl,-Map=...`) and LLD's (`rust-lld`, the default for Rust's embedded targets)
-- into sections, the input sections each holds, and the symbols in those, and
measures each region's use against its length.

**A DOCUMENT A PERSON'S BUILD WROTE, READ WITH ITS AGE.** The window never
links anything. `codecarto cargo record --map <bin>` writes
`target/codecarto/<bin>.map` for a Rust binary; a C build that passes
`-Wl,-Map=target/codecarto/<name>.map` writes the same. The reading carries the
file's time, and a source changed after it is stale.

How each figure is found
------------------------
region use   the sum of the sizes of the output sections whose address falls in
             the region, at run time; plus, for a section whose load address
             differs (`.data`), its size against the region it is loaded from.
             A zero-initialised section (`.bss`, `.uninit`, `.noinit`, a stack
             or heap) has no load image -- named by convention, because LLD's
             map does not print a section's type.
symbol size  a symbol's input section's size when the section holds that symbol
             alone, which is how `-ffunction-sections` and Rust lay code out;
             otherwise the distance to the next symbol in the section.
names        Rust's legacy mangling (`_ZN...17h<hash>E`) is demangled and the
             hash dropped, so a symbol reads as the path it was compiled from.

WHAT THIS CANNOT SEE. Whether the map belongs to the source beside it -- only
when each was written -- or what an inlined function cost: inlined code has no
symbol of its own and is counted in its caller.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

_NO_LOAD = re.compile(r"^\.(?:t?s?bss|uninit|noinit|stack|heap)(?:\.|$)")


@dataclass
class Symbol:
    name: str
    address: int
    size: int | None = None


@dataclass
class InputSection:
    name: str
    file: str
    address: int
    size: int
    symbols: list[Symbol] = field(default_factory=list)


@dataclass
class OutputSection:
    name: str
    vma: int
    lma: int
    size: int
    inputs: list[InputSection] = field(default_factory=list)

    @property
    def loads(self) -> bool:
        """Whether the section has an image to load from somewhere else."""
        return not _NO_LOAD.match(self.name) and self.lma != self.vma


@dataclass
class Region:
    name: str
    origin: int
    length: int
    attributes: str = ""

    def holds(self, address: int) -> bool:
        return self.origin <= address < self.origin + self.length


@dataclass
class LinkMap:
    path: str
    format: str = ""
    sections: list[OutputSection] = field(default_factory=list)
    regions: list[Region] = field(default_factory=list)
    reason: str = ""

    @property
    def ok(self) -> bool:
        return not self.reason

    def symbols(self) -> Iterable[Symbol]:
        for section in self.sections:
            for inp in section.inputs:
                yield from inp.symbols


@dataclass
class RegionUse:
    name: str
    origin: int
    length: int
    runtime_bytes: int = 0
    load_bytes: int = 0
    sections: list[str] = field(default_factory=list)

    @property
    def used_bytes(self) -> int:
        return self.runtime_bytes + self.load_bytes

    @property
    def fill(self) -> float:
        return self.used_bytes / self.length if self.length else 0.0

    def as_dict(self) -> dict:
        return {"name": self.name, "origin": self.origin, "length_bytes": self.length,
                "runtime_bytes": self.runtime_bytes, "load_bytes": self.load_bytes,
                "used_bytes": self.used_bytes, "fill": round(self.fill, 4),
                "sections": self.sections}


# ── Reading ───────────────────────────────────────────────────────────────────


def read(path: Path | str) -> LinkMap:
    """A map file, or a reason it could not be read."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return LinkMap(path=str(p), reason=f"{p.name} could not be read: {error}")
    return parse(text, str(p))


def parse(text: str, path: str = "") -> LinkMap:
    """Detect the map's shape and read it. An unknown shape is a reason."""
    lines = text.splitlines()
    header = next((i for i, line in enumerate(lines[:20])
                   if all(word in line.split() for word in ("VMA", "LMA", "Size", "Out", "Symbol"))), None)
    if header is not None:
        found = _parse_lld(lines, header, path)
    elif "Linker script and memory map" in text:
        found = _parse_gnu(lines, path)
    else:
        return LinkMap(path=path, reason=(f"{Path(path).name or 'this file'} is not a map GNU ld "
                                          "or LLD wrote: it has neither LLD's column header nor "
                                          "GNU ld's 'Linker script and memory map'"))
    for section in found.sections:
        for inp in section.inputs:
            _size_symbols(inp)
    return found


_LLD_ROW = re.compile(r"^\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+(\d+) (.*)$")


def _parse_lld(lines: list[str], header: int, path: str) -> LinkMap:
    found = LinkMap(path=path, format="lld")
    section: OutputSection | None = None
    inp: InputSection | None = None
    for line in lines[header + 1:]:
        m = _LLD_ROW.match(line)
        if m is None:
            continue
        vma, lma, size = (int(m.group(i), 16) for i in (1, 2, 3))
        text = m.group(5)
        # Out, In and Symbol are columns eight apart: the depth is the indent.
        depth = round((len(text) - len(text.lstrip(" "))) / 8)
        if " = " in text or text.rstrip().endswith("="):
            continue  # a script assignment, not a section or a symbol
        if depth <= 0:
            section = OutputSection(text.strip(), vma, lma, size)
            found.sections.append(section)
            inp = None
        elif depth == 1 and section is not None:
            file, _, name = text.strip().rpartition(":(")
            inp = InputSection(name.rstrip(")") or text.strip(), file, vma, size)
            section.inputs.append(inp)
        elif inp is not None:
            inp.symbols.append(Symbol(text.strip(), vma))
    return found


_HEX = r"0x[0-9a-fA-F]+"
_GNU_REGION = re.compile(rf"^(\S+)\s+({_HEX})\s+({_HEX})(?:\s+(\S+))?\s*$")
_GNU_SECTION = re.compile(rf"^(\S+)?\s+({_HEX})\s+({_HEX})(?:\s+load address\s+({_HEX}))?\s*$")
_GNU_INPUT = re.compile(rf"^ (\S+)?\s+({_HEX})\s+({_HEX})\s+(\S.*)$")
_GNU_SYMBOL = re.compile(rf"^\s+({_HEX})\s+([^=\s][^=]*?)\s*$")


def _parse_gnu(lines: list[str], path: str) -> LinkMap:
    found = LinkMap(path=path, format="gnu-ld")
    i = 0
    if "Memory Configuration" in "\n".join(lines):
        i = next(n for n, line in enumerate(lines) if line.startswith("Memory Configuration"))
        for line in lines[i + 1:]:
            if line.startswith("Linker script and memory map"):
                break
            m = _GNU_REGION.match(line)
            if m and m.group(1) not in ("Name", "*default*"):
                found.regions.append(Region(m.group(1), int(m.group(2), 16), int(m.group(3), 16),
                                            m.group(4) or ""))
    start = next(n for n, line in enumerate(lines) if line.startswith("Linker script and memory map"))
    section: OutputSection | None = None
    inp: InputSection | None = None
    pending_section = pending_input = ""
    for line in lines[start + 1:]:
        if not line.strip() or line.startswith(("LOAD ", "OUTPUT(", "START GROUP", "END GROUP")):
            continue
        if line[0] not in " \t":
            # An output section starts at column 0, alone on its line when its
            # name is too long for the column.
            m = _GNU_SECTION.match(line)
            if m and m.group(1):
                section = OutputSection(m.group(1), int(m.group(2), 16),
                                        int(m.group(4) or m.group(2), 16), int(m.group(3), 16))
                found.sections.append(section)
                inp = None
            else:
                pending_section = line.split()[0]
            continue
        if pending_section:
            m = _GNU_SECTION.match(line)
            pending, pending_section = pending_section, ""
            if m:
                section = OutputSection(pending, int(m.group(2), 16), int(m.group(4) or m.group(2), 16),
                                        int(m.group(3), 16))
                found.sections.append(section)
                inp = None
                continue
        if section is None or line.startswith(" *"):
            continue  # an input pattern, or `*fill*`
        if line.startswith(" ") and not line.startswith("  ") and line[1] != "*":
            m = _GNU_INPUT.match(line)
            if m:
                inp = InputSection(m.group(1), m.group(4).strip(), int(m.group(2), 16), int(m.group(3), 16))
                section.inputs.append(inp)
            else:
                pending_input = line.split()[0]
            continue
        if pending_input:
            m = re.match(rf"^\s+({_HEX})\s+({_HEX})\s+(\S.*)$", line)
            name, pending_input = pending_input, ""
            if m:
                inp = InputSection(name, m.group(3).strip(), int(m.group(1), 16), int(m.group(2), 16))
                section.inputs.append(inp)
                continue
        m = _GNU_SYMBOL.match(line)
        if m and inp is not None and not m.group(2).startswith((".", "*")):
            inp.symbols.append(Symbol(m.group(2), int(m.group(1), 16)))
    return found


def _size_symbols(inp: InputSection) -> None:
    ordered = sorted(inp.symbols, key=lambda s: s.address)
    if len(ordered) == 1 and ordered[0].address == inp.address:
        ordered[0].size = inp.size
        return
    end = inp.address + inp.size
    for here, after in zip(ordered, ordered[1:] + [None]):
        here.size = (after.address if after else end) - here.address


# ── Measuring ─────────────────────────────────────────────────────────────────


def usage(link_map: LinkMap, regions: list[Region]) -> list[RegionUse]:
    """Each region's use, from the sections the link placed in it."""
    uses = [RegionUse(r.name, r.origin, r.length) for r in regions]
    for section in link_map.sections:
        if section.size == 0:
            continue
        for use, region in zip(uses, regions):
            if region.holds(section.vma):
                use.runtime_bytes += section.size
                use.sections.append(section.name)
            if section.loads and region.holds(section.lma):
                use.load_bytes += section.size
                use.sections.append(f"{section.name} (load image)")
    return uses


# ── Names ─────────────────────────────────────────────────────────────────────

_ESCAPES = {"$LT$": "<", "$GT$": ">", "$u20$": " ", "$C$": ",", "$RF$": "&", "$BP$": "*",
            "$SP$": "@", "$LP$": "(", "$RP$": ")", "$u27$": "'", "$u5b$": "[", "$u5d$": "]",
            "$u7b$": "{", "$u7d$": "}", "$u3b$": ";", "$u2b$": "+", "$u22$": '"', "$u7e$": "~"}
_HASH = re.compile(r"::h[0-9a-f]{16}$")


def _unescape(part: str) -> str:
    if part.startswith("_$"):
        part = part[1:]
    part = part.replace("..", "::")
    for code, char in _ESCAPES.items():
        part = part.replace(code, char)
    return part


def demangle(name: str) -> str:
    """Rust's legacy mangling to the path it came from, hash dropped.

    Takes the mangled form (`_ZN...17h<hash>E`) and the half-demangled form an
    Itanium demangler prints for it, which joins the segments with `::` and
    leaves Rust's own escapes (`_$LT$`, `..`, `$u20$`) in place -- what LLD
    writes in a map. Anything else is returned with only its hash dropped."""
    m = re.fullmatch(r"_?_ZN(.+)E", name)
    if m is None:
        if "$" in name or ".." in name:
            name = "::".join(_unescape(p) for p in name.split("::"))
        return _HASH.sub("", name)
    rest, parts, i = m.group(1), [], 0
    while i < len(rest):
        j = i
        while j < len(rest) and rest[j].isdigit():
            j += 1
        if j == i:
            return name
        n = int(rest[i:j])
        parts.append(rest[j:j + n])
        i = j + n
    return _HASH.sub("", "::".join(_unescape(p) for p in parts))


def _split_path(path: str) -> list[str]:
    """`a::<b as c>::d` -> [`a`, `<b as c>`, `d`]: `::` outside angle brackets."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(path):
        ch = path[i]
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif depth == 0 and path.startswith("::", i):
            parts.append(path[start:i])
            start = i + 2
            i += 2
            continue
        i += 1
    parts.append(path[start:])
    return [p for p in parts if p]


def symbol_key(symbol: str) -> tuple[str | None, str]:
    """A demangled symbol's (self type, function name).

    `<hal::gpio::pin::Pin as hal::gpio::OutputPin>::set_high` -> (`Pin`, `set_high`)
    `hal::gpio::pin::<impl hal::gpio::OutputPin for hal::gpio::pin::Pin>::set_high` -> (`Pin`, `set_high`)
    `hal::gpio::pin::Pin::new` -> (`Pin`, `new`); `blinky::delay` -> (None, `delay`)"""
    parts = _split_path(demangle(symbol))
    if not parts:
        return None, symbol
    name = parts[-1]
    owner = parts[-2] if len(parts) >= 2 else ""
    if owner.startswith("<") and owner.endswith(">"):
        inner = owner[1:-1]
        m = re.match(r"impl\s+(?:.+?\s+for\s+)?(.+)$", inner) if inner.startswith("impl") else None
        target = m.group(1) if m else inner.split(" as ")[0]
        return _last(target), name
    if owner[:1].isupper():
        return _last(owner), name
    return None, name


def _last(path: str) -> str:
    head = re.split(r"<", path, maxsplit=1)[0]
    return _split_path(head.strip("&* "))[-1] if head.strip("&* ") else path


# ── Joining a map to a code map ───────────────────────────────────────────────

_CODE_KINDS = {"rust": {"function", "method", "static"}, "c": {"function", "variable"}}


def _crate_of(path: str) -> str:
    """`.../crates/hal-core/src/gpio.rs` -> `hal_core`: the directory above `src`."""
    parts = path.replace("\\", "/").split("/")
    if "src" in parts:
        at = len(parts) - 1 - parts[::-1].index("src")
        if at >= 1:
            return parts[at - 1].replace("-", "_")
    return ""


def _symbol_crate(symbol: str, owner: str) -> str:
    """The crate a symbol was compiled in: its path's first segment, the path
    inside `<..>` for an impl, or the map's own binary for an unmangled name."""
    parts = _split_path(demangle(symbol))
    if len(parts) < 2:
        return owner
    first = parts[0]
    if first.startswith("<"):
        inner = first[1:].removeprefix("impl ")
        return _split_path(inner.split(" as ")[0].split(" for ")[-1].strip("&* "))[0]
    return first


def _kib(n: int) -> str:
    return f"{n} B" if n < 1024 else f"{n / 1024:.1f} KiB"


def annotate(graph, link_map: LinkMap, *, owner: str, recorded_at: str, stale: bool) -> dict:
    """Put what the link measured on a parsed code map. Returns what was joined.

    - **Regions** drawn from a linker script get `meta.measured` (bytes used at
      run time and as load images, the fill against their length) and a
      `hover` that says it. Against the map's own memory table when it has one
      (GNU ld prints it), else the regions the script declares. When several
      scripts declare regions, only the one under a directory named after the
      map's binary (`owner`) is joined.
    - **Sections** drawn from a script get their measured size and address.
    - **Code items** get `meta.bytes` from the symbols that name them, matched
      within the crate the symbol was compiled in, by function name and, for a
      method, its impl's type -- and only when exactly one item answers. A
      symbol from a crate outside the parse (`core`, a runtime) is counted, not
      drawn."""
    owner = owner.replace("-", "_")
    provenance = {"map": Path(link_map.path).name, "recorded_at": recorded_at, "stale": stale}
    linker = [(n, d) for n, d in graph.nodes(data=True) if d.get("language") == "linker"]
    files = {d.get("file", "") for _, d in linker if d.get("kind") == "region"}
    if len(files) > 1:
        dirs = {f"/{owner}/", f"/{owner.replace('_', '-')}/"}
        files = {f for f in files if any(d in f.replace("\\", "/") for d in dirs)}
    regions = list(link_map.regions)
    if not regions:
        for _, d in linker:
            meta = d.get("meta") or {}
            if (d.get("kind") == "region" and d.get("file") in files
                    and meta.get("origin_value") is not None and meta.get("length_bytes")):
                regions.append(Region(d["label"], meta["origin_value"], meta["length_bytes"]))
    uses = {u.name: u for u in usage(link_map, regions)}
    joined = {"regions": 0, "sections": 0, "symbols": 0, "outside": 0, "ambiguous": 0}
    sections = {s.name: s for s in link_map.sections}
    for _, d in linker:
        if d.get("file") not in files:
            continue
        if d.get("kind") == "region" and d.get("label") in uses:
            use = uses[d["label"]]
            d.setdefault("meta", {})["measured"] = {**use.as_dict(), **provenance}
            d["hover"] = (f"{use.name} — {_kib(use.used_bytes)} of {_kib(use.length)} used "
                          f"({use.fill:.1%}), from {provenance['map']}"
                          + (" (older than the source)" if stale else ""))
            joined["regions"] += 1
        elif d.get("kind") == "section" and d.get("label") in sections:
            s = sections[d["label"]]
            d.setdefault("meta", {})["measured"] = {"size_bytes": s.size, "vma": s.vma, "lma": s.lma,
                                                     **provenance}
            d["hover"] = f"{s.name} — {_kib(s.size)} at {s.vma:#010x}"
            joined["sections"] += 1

    # Code items, by crate, then name, then (for a method) the impl's type.
    items: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for node_id, d in graph.nodes(data=True):
        if d.get("kind") not in _CODE_KINDS.get(d.get("language", ""), ()):
            continue
        crate = _crate_of(str(d.get("file", ""))) if d.get("language") == "rust" else owner
        items.setdefault((crate, d.get("label", "")), []).append((node_id, d))

    def impl_type(node_id: str) -> str:
        for parent in graph.predecessors(node_id):
            pd = graph.nodes[parent]
            if pd.get("kind") == "impl":
                return (pd.get("meta") or {}).get("self_type", "")
        return ""

    totals: dict[str, list] = {}
    for section in link_map.sections:
        for inp in section.inputs:
            for sym in inp.symbols:
                type_name, name = symbol_key(sym.name)
                crate = _symbol_crate(sym.name, owner)
                found = items.get((crate, name), [])
                if not found and crate == owner:
                    found = [c for (cr, n), cs in items.items() if n == name and cr == "" for c in cs]
                if type_name:
                    found = [(n, d) for n, d in found if impl_type(n) == type_name]
                else:
                    found = [(n, d) for n, d in found if d.get("kind") != "method"]
                if not found:
                    joined["outside"] += 1
                    continue
                if len(found) > 1:
                    joined["ambiguous"] += 1
                    continue
                entry = totals.setdefault(found[0][0], [0, [], section.name])
                entry[0] += sym.size or 0
                entry[1].append(demangle(sym.name))
    for node_id, (size, names, section_name) in totals.items():
        d = graph.nodes[node_id]
        meta = d.setdefault("meta", {})
        meta["bytes"] = size
        meta["measured"] = {"symbols": names, "section": section_name, **provenance}
        d["hover"] = f"{d.get('label')} — {_kib(size)} in {section_name}, from {provenance['map']}"
        joined["symbols"] += 1
    return joined


def age(path: Path) -> tuple[str, float]:
    """When a map was written (ISO), and how long ago in seconds."""
    from datetime import datetime, timezone

    mtime = path.stat().st_mtime
    return (datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(timespec="seconds"),
            round(time.time() - mtime, 1))
