"""
Regex Language Parsers
======================
Provides broad language coverage using lightweight regex patterns — zero new
dependencies beyond the standard library.

Each ``RegexLanguageParser`` instance is configured for a single language and
registered with ``ParserRegistry`` at import time.  Patterns match stripped
lines anchored at ``^`` to minimise false positives.  Only depth-2 nodes
(top-level symbol definitions) are emitted; depth-3 sub-symbol extraction is
deferred to the tree-sitter phase (Phase 2).

Supported languages
-------------------
JavaScript (.js .jsx .mjs), TypeScript (.ts .tsx), Rust (.rs), Go (.go),
Java (.java), C# (.cs), Kotlin (.kt .kts), Swift (.swift), Ruby (.rb),
PHP (.php), Scala (.scala), Shell (.sh .bash)

Node ID format
--------------
``{language}::{basename}::{kind}::{label}::{lineno}``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

import networkx as nx

from codecarto.models.source_data import File
from codecarto.services.parsers.language_parser import (
    ParserRegistry,
    make_node,
    make_edge,
)

# ── Type alias ────────────────────────────────────────────────────────────────

_Pattern = tuple[int, str, re.Pattern]   # (depth, kind, compiled_regex)


# ── Per-language pattern definitions ─────────────────────────────────────────
# Regex must capture the symbol name in group 1.

_JS: list[_Pattern] = [
    (2, "function",  re.compile(
        r"^(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s+(\w+)\s*[\(<]"
    )),
    (2, "class",     re.compile(
        r"^(?:export\s+(?:default\s+)?)?class\s+(\w+)"
    )),
    # Arrow / plain const function: const foo = (...) => or const foo = async (
    (2, "function",  re.compile(
        r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("
    )),
]

_TS: list[_Pattern] = _JS + [
    (2, "interface", re.compile(r"^(?:export\s+)?(?:default\s+)?interface\s+(\w+)")),
    (2, "type",      re.compile(r"^(?:export\s+)?type\s+(\w+)\s*(?:<[^=]+>)?\s*=")),
    (2, "enum",      re.compile(r"^(?:export\s+)?(?:const\s+)?enum\s+(\w+)")),
    (2, "decorator", re.compile(r"^@(\w+)\s*(?:\(|$)")),
]

_RUST: list[_Pattern] = [
    (2, "function",    re.compile(
        r"^(?:pub\s+(?:\(\w+\)\s+)?)?(?:async\s+)?fn\s+(\w+)\s*[\(<]"
    )),
    (2, "struct",      re.compile(r"^(?:pub\s+)?struct\s+(\w+)")),
    (2, "enum",        re.compile(r"^(?:pub\s+)?enum\s+(\w+)")),
    (2, "trait",       re.compile(r"^(?:pub\s+)?trait\s+(\w+)")),
    (2, "impl",        re.compile(r"^impl(?:\s*<[^>]*>)?\s+(?:\w+\s+for\s+)?(\w+)")),
    (2, "module",      re.compile(r"^(?:pub\s+)?mod\s+(\w+)\s*\{")),
    (2, "type",        re.compile(r"^(?:pub\s+)?type\s+(\w+)\s*=")),
    (2, "macro",       re.compile(r"^(?:pub\s+)?macro_rules!\s*(\w+)")),
]

_GO: list[_Pattern] = [
    # func (receiver) Name( and func Name(
    (2, "function",  re.compile(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*[\(<]")),
    (2, "struct",    re.compile(r"^type\s+(\w+)\s+struct")),
    (2, "interface", re.compile(r"^type\s+(\w+)\s+interface")),
    (2, "type",      re.compile(r"^type\s+(\w+)\s+\w")),
    (2, "variable",  re.compile(r"^(?:var|const)\s+(\w+)\s")),
]

_JAVA: list[_Pattern] = [
    (2, "class",      re.compile(
        r"^(?:public\s+|private\s+|protected\s+|static\s+)*"
        r"(?:abstract\s+|final\s+)?class\s+(\w+)"
    )),
    (2, "interface",  re.compile(
        r"^(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)"
    )),
    (2, "enum",       re.compile(
        r"^(?:public\s+|private\s+|protected\s+)?enum\s+(\w+)"
    )),
    (2, "annotation", re.compile(
        r"^(?:public\s+)?@interface\s+(\w+)"
    )),
]

_CSHARP: list[_Pattern] = [
    (2, "namespace", re.compile(r"^namespace\s+([\w.]+)")),
    (2, "class",     re.compile(
        r"^(?:(?:public|private|protected|internal|abstract|sealed|partial|static)\s+)*"
        r"class\s+(\w+)"
    )),
    (2, "interface", re.compile(
        r"^(?:(?:public|private|protected|internal)\s+)*interface\s+(\w+)"
    )),
    (2, "enum",      re.compile(
        r"^(?:(?:public|private|protected|internal)\s+)*enum\s+(\w+)"
    )),
    (2, "struct",    re.compile(
        r"^(?:(?:public|private|protected|internal|readonly)\s+)*struct\s+(\w+)"
    )),
    (2, "record",    re.compile(
        r"^(?:(?:public|private|protected|internal)\s+)*record\s+(\w+)"
    )),
]

_KOTLIN: list[_Pattern] = [
    (2, "class",     re.compile(
        r"^(?:(?:data|sealed|abstract|open|inner|enum)\s+)*"
        r"(?:class|object)\s+(\w+)"
    )),
    (2, "interface", re.compile(r"^(?:fun\s+)?interface\s+(\w+)")),
    (2, "function",  re.compile(
        r"^(?:(?:public|private|protected|internal|suspend|inline|"
        r"override|abstract|open)\s+)*fun\s+(?:<[^>]+>\s+)?(\w+)\s*[\(<]"
    )),
    (2, "type",      re.compile(r"^typealias\s+(\w+)\s*=")),
]

_SWIFT: list[_Pattern] = [
    (2, "class",    re.compile(
        r"^(?:(?:public|private|internal|open|final)\s+)?class\s+(\w+)"
    )),
    (2, "struct",   re.compile(
        r"^(?:(?:public|private|internal)\s+)?struct\s+(\w+)"
    )),
    (2, "protocol", re.compile(
        r"^(?:(?:public|private|internal)\s+)?protocol\s+(\w+)"
    )),
    (2, "enum",     re.compile(
        r"^(?:(?:public|private|internal|indirect)\s+)?enum\s+(\w+)"
    )),
    (2, "function", re.compile(
        r"^(?:(?:public|private|internal|static|class|override|"
        r"mutating|open)\s+)*func\s+(\w+)\s*[\(<]"
    )),
    (2, "extension", re.compile(r"^extension\s+(\w+)")),
]

_RUBY: list[_Pattern] = [
    (2, "module",   re.compile(r"^module\s+(\w+)")),
    (2, "class",    re.compile(r"^class\s+(\w+)")),
    (2, "function", re.compile(r"^def\s+(\w+)")),
]

_PHP: list[_Pattern] = [
    (2, "class",    re.compile(r"^(?:abstract\s+|final\s+)?class\s+(\w+)")),
    (2, "interface", re.compile(r"^interface\s+(\w+)")),
    (2, "trait",    re.compile(r"^trait\s+(\w+)")),
    (2, "enum",     re.compile(r"^enum\s+(\w+)")),
    (2, "function", re.compile(
        r"^(?:(?:public|private|protected|static|abstract|final)\s+)*"
        r"function\s+(\w+)\s*\("
    )),
]

_SCALA: list[_Pattern] = [
    (2, "class",    re.compile(r"^(?:case\s+)?class\s+(\w+)")),
    (2, "object",   re.compile(r"^(?:case\s+)?object\s+(\w+)")),
    (2, "trait",    re.compile(r"^trait\s+(\w+)")),
    (2, "function", re.compile(
        r"^(?:(?:private|protected|override|implicit|inline|def)\s+)*"
        r"def\s+(\w+)\s*[\[(]"
    )),
    (2, "type",     re.compile(r"^type\s+(\w+)\s*=")),
]

_SHELL: list[_Pattern] = [
    # POSIX style: name() { or name () {
    (2, "function", re.compile(r"^(\w+)\s*\(\s*\)")),
    # Bash style: function name {
    (2, "function", re.compile(r"^function\s+(\w+)\s*(?:\(|\{|$)")),
]

# ── Lua ──────────────────────────────────────────────────────────────────────
_LUA: list[_Pattern] = [
    (2, "function", re.compile(r"^(?:local\s+)?function\s+([\w.:]+)\s*\(")),
    (2, "function", re.compile(r"^([\w.]+)\s*=\s*function\s*\(")),
]

# ── Assembly (x86/ARM/MIPS/RISC-V common notations) ─────────────────────────
_ASM: list[_Pattern] = [
    # Label definitions: word followed by colon (e.g. main:, _start:, .loop:)
    (2, "label", re.compile(r"^(\.[a-zA-Z_]\w*|[a-zA-Z_]\w*):")),
    # Common directive names as top-level symbols
    (2, "section", re.compile(r"^\.(text|data|bss|rodata|section)\b")),
]

# ── SQL ───────────────────────────────────────────────────────────────────────
_SQL: list[_Pattern] = [
    (2, "table",     re.compile(r"^CREATE\s+(?:OR\s+REPLACE\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)),
    (2, "view",      re.compile(r"^CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)", re.IGNORECASE)),
    (2, "function",  re.compile(r"^CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(\w+)", re.IGNORECASE)),
    (2, "procedure", re.compile(r"^CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+(\w+)", re.IGNORECASE)),
    (2, "index",     re.compile(r"^CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)),
]

# ── Markdown ─────────────────────────────────────────────────────────────────
_MARKDOWN: list[_Pattern] = [
    # ATX headings: # Title, ## Sub, etc. Capture the heading text.
    (2, "heading", re.compile(r"^#{1,6}\s+(.+?)\s*$")),
]

# ── HTML (id and data-component attribute definitions) ───────────────────────
_HTML: list[_Pattern] = [
    # Elements with id="…" — useful as structural anchors
    (2, "anchor", re.compile(r'<\w+[^>]*\sid="([^"]+)"')),
    # Web component definitions: <custom-element> or data-component="name"
    (2, "component", re.compile(r"<([a-z][\w-]+-[\w-]+)(?:\s|>|/)")),
]

# ── CSS / SCSS ────────────────────────────────────────────────────────────────
_CSS: list[_Pattern] = [
    (2, "class",      re.compile(r"^\.([\w-]+)\s*(?:\{|,|:)")),
    (2, "id",         re.compile(r"^#([\w-]+)\s*(?:\{|,|:)")),
    (2, "keyframes",  re.compile(r"^@keyframes\s+([\w-]+)")),
    (2, "mixin",      re.compile(r"^@mixin\s+([\w-]+)")),
    (2, "function",   re.compile(r"^@function\s+([\w-]+)")),
]

# ── Dockerfile ────────────────────────────────────────────────────────────────
_DOCKERFILE: list[_Pattern] = [
    # ARG NAME and ENV NAME are the most symbol-like directives
    (2, "arg",       re.compile(r"^ARG\s+([\w]+)", re.IGNORECASE)),
    (2, "env",       re.compile(r"^ENV\s+([\w]+)", re.IGNORECASE)),
    # Stage names from multi-stage builds: FROM image AS name
    (2, "stage",     re.compile(r"^FROM\s+\S+\s+AS\s+([\w-]+)", re.IGNORECASE)),
]

# ── TOML ─────────────────────────────────────────────────────────────────────
_TOML: list[_Pattern] = [
    (2, "section",       re.compile(r"^\[([^\[\]]+)\]$")),
    (2, "array_section", re.compile(r"^\[\[([^\[\]]+)\]\]$")),
]


# ── Parser class ──────────────────────────────────────────────────────────────

class RegexLanguageParser:
    """
    Generic regex-based symbol extractor.

    A lightweight, zero-dependency LanguageParser that satisfies the Protocol
    via duck-typing (``language`` and ``extensions`` are regular properties
    rather than ClassVar, which is fine at runtime).
    """

    def __init__(
        self,
        language: str,
        extensions: list[str],
        patterns: list[_Pattern],
    ) -> None:
        self._language = language
        self._extensions = [e.lower() for e in extensions]
        self._patterns = patterns

    # ── LanguageParser protocol ───────────────────────────────────────────────

    @property
    def language(self) -> str:  # type: ignore[override]
        return self._language

    @property
    def extensions(self) -> list[str]:  # type: ignore[override]
        return self._extensions

    def parse_files(self, files: list[File], depth: int = 2) -> nx.DiGraph:
        """
        Scan each file line-by-line and emit depth-2 symbol nodes.

        Parameters
        ----------
        files : list[File]
            Files to parse.  Must have ``raw`` content populated.
        depth : int
            Requested parse depth.  Patterns with ``pattern_depth > depth``
            are skipped (allows callers to request depth-1-only passes).

        Returns
        -------
        nx.DiGraph
            Nodes carry the unified schema.  Root nodes (no in-edges) will be
            connected to their file node by ``UnifiedParserService._merge_subgraph``.
        """
        graph = nx.DiGraph()

        for file in files:
            if not file.raw:
                continue

            basename = Path(file.name).name
            lines = file.raw.splitlines()

            for lineno, line in enumerate(lines, start=1):
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", "//", "/*", "*", "--")):
                    continue  # Skip comments and blank lines early

                for pat_depth, kind, pattern in self._patterns:
                    if pat_depth > depth:
                        continue
                    match = pattern.match(stripped)
                    if match:
                        label = match.group(1)
                        node_id = (
                            f"{self._language}::{basename}::{kind}::{label}::{lineno}"
                        )
                        graph.add_node(
                            node_id,
                            **make_node(
                                node_id,
                                depth=pat_depth,
                                language=self._language,
                                kind=kind,
                                label=label,
                                file=file.url or file.name,
                                line=lineno,
                            ),
                        )
                        break  # One symbol match per line is enough

        return graph


# ── Language instances + registration ─────────────────────────────────────────

_LANGUAGES: list[tuple[str, list[str], list[_Pattern]]] = [
    # ── Existing symbol-bearing languages ─────────────────────────────────────
    ("javascript", [".js", ".jsx", ".mjs", ".cjs"],    _JS),
    ("typescript", [".ts", ".tsx", ".cts", ".mts"],    _TS),
    ("rust",       [".rs"],                            _RUST),
    ("go",         [".go"],                            _GO),
    ("java",       [".java"],                          _JAVA),
    ("csharp",     [".cs"],                            _CSHARP),
    ("kotlin",     [".kt", ".kts"],                    _KOTLIN),
    ("swift",      [".swift"],                         _SWIFT),
    ("ruby",       [".rb"],                            _RUBY),
    ("php",        [".php"],                           _PHP),
    ("scala",      [".scala"],                         _SCALA),
    ("shell",      [".sh", ".bash"],                   _SHELL),
    # ── New additions ──────────────────────────────────────────────────────────
    # Note: bare-filename parsers (Dockerfile, Makefile with no extension)
    # require infrastructure changes in unified_parser_service.py to match
    # by filename stem rather than Path.suffix — not yet supported.
    ("lua",        [".lua"],                           _LUA),
    ("assembly",   [".asm", ".s", ".S"],               _ASM),
    ("sql",        [".sql"],                           _SQL),
    ("markdown",   [".md", ".mdx"],                    _MARKDOWN),
    ("html",       [".html", ".htm", ".xhtml"],        _HTML),
    ("css",        [".css", ".scss", ".sass", ".less"], _CSS),
    ("dockerfile", [".dockerfile"],                    _DOCKERFILE),
    ("toml",       [".toml"],                          _TOML),
]

for _lang, _exts, _pats in _LANGUAGES:
    ParserRegistry.register(RegexLanguageParser(_lang, _exts, _pats))
