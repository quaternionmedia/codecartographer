from pydantic import BaseModel
from typing import Iterator, List, Tuple


class File(BaseModel):
    """The data of a file. [name, size, raw]"""

    url: str = ""
    name: str = ""
    size: int = 0
    raw: str = ""


class Folder(BaseModel):
    """The data of a file. [name, size, files, folders]"""

    name: str = ""
    size: int = 0
    files: List[File] = []
    folders: List["Folder"] = []

    def iter_files(self) -> Iterator[Tuple["Folder", File]]:
        """Yield every (containing_folder, file) pair in this tree, recursively.

        Shared traversal for callers that just need "every file under this
        folder" (e.g. collecting parseable files by extension, fetching raw
        content) instead of each hand-rolling its own recursive walk —
        see docs/llm/next_steps/parser_consolidation_and_scope_drift.md's
        finding 1.4. Not used by graph-building walks (e.g.
        UnifiedParserService._walk_folder) that need per-level parent-id/
        depth context beyond just the immediate containing folder.
        """
        for file in self.files:
            yield self, file
        for sub in self.folders:
            yield from sub.iter_files()


class RepoInfo(BaseModel):
    """The data of a file. [owner, name, url]"""

    owner: str = ""
    name: str = ""
    url: str = ""


class Directory(BaseModel):
    """The data of a file. [info, size, root (files, folders)]"""

    info: RepoInfo
    size: int = 0
    root: Folder
    is_partial: bool = False  # True when only top-level structure was fetched (large repo)
