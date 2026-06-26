"""
Importing this package registers all language parsers with ParserRegistry.

Registration itself is cheap — these modules don't import heavy backends
(libclang, tree-sitter, etc.) at module load. Backend imports are deferred
to inside parse_files() so the adapters can fail gracefully when a backend
isn't installed.
"""
from . import python_language_parser  # noqa: F401
from . import c_language_parser       # noqa: F401
from . import regex_language_parser   # noqa: F401