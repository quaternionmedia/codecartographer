import m, { Vnode } from "mithril";
import { Raw, RawFile, RawFolder, Repo } from "../../models/source";

import "./directory_nav.css";

export class DirectoryState {
  navContent: Vnode[];
  selectedUrl: string;
  repo: Repo;
  onUrlFileClicked: (url: string) => void;
  onWholeRepoClicked: () => void;
  UpdateCell: (upload: DirectoryState) => void;

  constructor(
    navContent: Vnode[] = [],
    selectedUrl: string = "",
    repo: Repo = new Repo(),
    onUrlFileClicked: (url: string) => void,
    onWholeRepoClicked: () => void,
    UpdateCell: (upload: DirectoryState) => void
  ) {
    this.navContent = navContent;
    this.selectedUrl = selectedUrl;
    this.repo = repo;
    this.onUrlFileClicked = onUrlFileClicked;
    this.onWholeRepoClicked = onWholeRepoClicked;
    this.UpdateCell = UpdateCell;
  }

  // Arrow function to automatically bind `this`
  public setSelectedUrl = (url: string) => {
    this.selectedUrl = url;
    this.UpdateCell(this);
    this.onUrlFileClicked(url);
  };
}

export const DirectoryNav = (directory: DirectoryState) => {
  if (directory.selectedUrl !== "") {
    var tree = recursiveDirectoryParse(
      directory.repo.raw,
      "root",
      directory.setSelectedUrl
    );
    var plotAll = m(
      "button.plot_whole_repo_btn",
      {
        onclick: function () {
          directory.onWholeRepoClicked();
        },
      },
      "Plot Whole Repo"
    );

    directory.navContent = [m("div.directory_tree", [tree]), plotAll];
  }

  return m("div.directory_nav", [directory.navContent]);
};

export function recursiveDirectoryParse(
  data: Raw,
  name: string,
  onUrlFileClicked: (url: string) => void
): m.Vnode<any, any>[] {
  const folderElements: m.Vnode<any, any>[] = [];
  const fileElements: m.Vnode<any, any>[] = [];

  Object.entries(data).forEach(([key, value]) => {
    if (key === "files") {
      fileElements.push(
        m(FileList, {
          parent: name,
          children: value as RawFile[],
          onUrlFileClicked: onUrlFileClicked,
        })
      );
    } else if (value instanceof Object) {
      folderElements.push(
        m(Folder, {
          name: key,
          children: value,
          onUrlFileClicked: onUrlFileClicked,
        })
      );
    }
  });

  // Ensure folders are listed before files
  return [...folderElements, ...fileElements];
}

interface FolderAttrs {
  name: string;
  children: any;
  onUrlFileClicked: (url: string) => void;
}

interface FileListAttrs {
  parent: string;
  children: RawFile[];
  onUrlFileClicked: (url: string) => void;
}

interface FileAttrs {
  name: string;
  url: string;
  onUrlFileClicked: (url: string) => void;
}

interface FolderState {
  isOpen: boolean;
}

export const Folder: m.Component<FolderAttrs> = {
  view(vnode) {
    const { name, children, onUrlFileClicked } = vnode.attrs;
    const state = vnode.state as FolderState; // Type assertion for state

    return m(`div.folder.folder__${name}`, [
      m(
        "div.folder_button",
        {
          onclick: function () {
            this.classList.toggle("active");
            state.isOpen = !state.isOpen;
            m.redraw(); // Trigger a redraw to update the view
          },
        },
        name
      ),
      m(
        "div.folder_content",
        recursiveDirectoryParse(children, name, onUrlFileClicked)
      ),
    ]);
  },
};

export const FileList: m.Component<FileListAttrs> = {
  view(vnode) {
    const { parent, children, onUrlFileClicked } = vnode.attrs;

    return m(`div.files.files__${parent}`, [
      children.map((child: RawFile) =>
        m("div.file_container", [
          m(File, {
            name: child.name,
            url: child.url,
            onUrlFileClicked: onUrlFileClicked,
          }),
          m("a.file_raw_btn", { href: child.url, target: "_blank" }, "raw"),
        ])
      ),
    ]);
  },
};

export const File: m.Component<FileAttrs> = {
  view(vnode) {
    const { name, url, onUrlFileClicked } = vnode.attrs;
    const ext = name.split(".").pop() ?? "";
    const isDisabled = !["py"].includes(ext);

    return m(
      "div.file",
      {
        class: `file__${ext} ${isDisabled ? "disabled" : ""}`,
        onclick: () => !isDisabled && onUrlFileClicked(url),
      },
      name
    );
  },
};
