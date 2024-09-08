export class RawFile {
  url: string;
  name: string;
  size: number;
  raw: string;

  constructor(
    name: string = "",
    size: number = 0,
    raw: string = "",
    url: string = ""
  ) {
    this.name = name;
    this.size = size;
    this.raw = raw;
    this.url = url;
  }
}

export class RawFolder {
  name: string;
  size: number;
  files: Record<string, RawFile>;
  folders: Record<string, RawFolder>;

  constructor(
    name: string,
    size: number,
    files: Record<string, RawFile>,
    folders: Record<string, RawFolder>
  ) {
    this.name = name;
    this.size = size;
    this.files = files;
    this.folders = folders;
  }
}

export type Raw = Record<string, RawFile[] | RawFolder>;

export class RepoInfo {
  owner: string;
  repo: string;
  url: string;

  constructor(owner: string = "", repo: string = "", url: string = "") {
    this.owner = owner;
    this.repo = repo;
    this.url = url;
  }
}

export class Repo {
  info: RepoInfo;
  size: number;
  raw: Raw;

  constructor(
    info: RepoInfo = new RepoInfo(),
    size: number = 0,
    raw: Raw = {}
  ) {
    this.info = info;
    this.size = size;
    this.raw = raw;
  }
}
