from pydantic import BaseModel
from typing import List


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
