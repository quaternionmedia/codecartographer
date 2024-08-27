# TODO: SourceData will be used by the parser
# is could be a single file, a folder of files,
# or a folder of folders and/or files

# the files will have names and raw data content, buth in sting format
# the folders will have names and a list of files and/or folders

from pydantic import BaseModel
from typing import List, Union


class File(BaseModel):
    """The data of a file. [name, size, raw]"""

    name: str
    size: int
    raw: str


class Folder(BaseModel):
    """The data of a file. [name, size, files, folders]"""

    name: str
    size: int
    files: list[File]
    folders: list["Folder"]


class Source(BaseModel):
    """The data of a file. [name, size, source (files, folders)]"""

    name: str
    size: int
    source: List
