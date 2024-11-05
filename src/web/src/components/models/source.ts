/**
 * Holds the folders and or files of a directory.
 *
 * As well as the repository information [ owner, name, url ].
 */
export class Directory {
  info: RepoInfo;
  size: number;
  root: RawFolder;

  constructor(
    info: RepoInfo = new RepoInfo(),
    size: number = 0,
    root: RawFolder = new RawFolder()
  ) {
    this.info = info;
    this.size = size;
    this.root = root;
  }

  get isEmpty() {
    return Object.keys(this.root).length === 0;
  }
}

/**
 * The repository information. [ owner, name, url ]
 */
export class RepoInfo {
  owner: string;
  name: string;
  url: string;

  constructor(owner: string = '', name: string = '', url: string = '') {
    this.owner = owner;
    this.name = name;
    this.url = url;
  }
}

/**
 * A dictionary of the directory files and folders.
 * * Key: The folder name
 * * Value: Either a sub folder or a collection of files.
 */
export type Root = RawFile[] | RawFolder[] | RawFolder;

/**
 * A folder in the directory.
 * * name - The name of the folder
 * * size - The size of the folder
 * * files - A dictionary of files in the folder
 *   - Key: The file name
 *   - Value: The file object
 * * folders - A dictionary of sub folders in the folder
 *   - Key: The sub folder name
 *   - Value: The sub folder object
 */
export class RawFolder {
  name: string;
  size: number;
  files: RawFile[];
  folders: RawFolder[];

  constructor(
    name: string = '',
    size: number = 0,
    files: RawFile[] = [],
    folders: RawFolder[] = []
  ) {
    this.name = name;
    this.size = size;
    this.files = files;
    this.folders = folders;
  }
}

/**
 * A file in the directory.
 * * url - A URL pointing to the file
 * * name - The name of the file
 * * size - The size of the file
 * * raw - The content of the file
 */
export class RawFile {
  url: string;
  name: string;
  size: number;
  raw: string;

  constructor(
    name: string = '',
    size: number = 0,
    raw: string = '',
    url: string = ''
  ) {
    this.name = name;
    this.size = size;
    this.raw = raw;
    this.url = url;
  }
}
