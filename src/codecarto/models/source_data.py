# TODO: SourceData will be used by the parser
# is could be a single file, a folder of files,
# or a folder of folders and/or files

# the files will have names and raw data content, buth in sting format
# the folders will have names and a list of files and/or folders

from pydantic import BaseModel
from typing import Dict, List


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


class Source(BaseModel):
    """The data of a file. [owner, name, size, source (files, folders)]"""

    owner: str = ""
    name: str = ""
    size: int = 0
    source: Dict[str, File | Folder] = {}


class RepoInfo(BaseModel):
    """The data of a file. [owner, repo, size, url, raw (files, folders)]"""

    owner: str = ""
    repo: str = ""
    url: str = ""


class Repo:
    """The data of a file. [name, size, raw (files, folders)]"""

    info: RepoInfo
    size: int = 0
    source: dict[str, File | Folder] = {}

    def __init__(
        self,
        info: RepoInfo,
        size: int = 0,
        raw: dict[str, File | Folder] = {},
    ):
        self.info = info
        self.size = size
        self.raw = raw

    def dict(self):
        return {
            "info": self.info.dict(),
            "size": self.size,
            "raw": self.raw,
        }
