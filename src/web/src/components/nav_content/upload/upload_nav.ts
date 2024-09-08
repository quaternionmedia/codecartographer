import m, { Vnode } from "mithril";

import "./upload_nav.css";
import { RawFile } from "../../models/source";

export class UploadState {
  nav_content: Vnode[];
  selected_file: RawFile | null;
  files: RawFile[];
  onFileClick: (file: RawFile) => void;
  onWholeSourceClick: () => void;
  update_cell: (upload: UploadState) => void;

  constructor(
    nav_content: Vnode[] = [],
    selected_file: RawFile | null = null,
    files: RawFile[] = [],
    onFileClick: (file: RawFile) => void,
    onWholeSourceClick: () => void,
    update_cell: (upload: UploadState) => void
  ) {
    this.nav_content = nav_content;
    this.selected_file = selected_file;
    this.files = files;
    this.onFileClick = onFileClick;
    this.onWholeSourceClick = onWholeSourceClick;
    this.update_cell = update_cell;
  }

  public setSelectedFile(file: RawFile) {
    this.selected_file = file;
    this.update_cell(this);
    this.onFileClick(file);
  }

  public addFile(file: RawFile) {
    this.files.push(file);
    this.update_cell(this);
  }
}

export const UploadNav = (upload: UploadState) => {
  var tree = Files(upload, (file: RawFile) => {
    upload.setSelectedFile(file);
  });
  var plot_all = m(
    "button.plot_all_files_btn",
    {
      onclick: function () {
        upload.onWholeSourceClick();
      },
    },
    "Plot Uploaded Files"
  );

  upload.nav_content = [m("div.upload_tree", [UploadHeader(upload), tree])];

  return m("div.upload_nav", [upload.nav_content]);
};

export const UploadHeader = (upload: UploadState) => {
  return m("div.upload_header", [
    m("div.upload_header_title", "Uploaded Files"),
    UploadButton(upload),
  ]);
};

export const UploadButton = (upload: UploadState) => {
  return m("div.upload_header_button", [
    m("input.upload_header_button_input", {
      type: "file",
      id: "fileInput",
      style: "display:none",
      accept: ".py",
      onchange: async function (e) {
        if (e.target.files !== null) {
          let exists = false;
          const uploadedFile = e.target.files[0];
          upload.files.forEach((file: RawFile) => {
            if (file.name === uploadedFile.name) {
              exists = true;
            }
          });

          if (!exists) {
            const newFile = new RawFile(
              uploadedFile.name,
              uploadedFile.size,
              await uploadedFile.text()
            );
            upload.addFile(newFile);
          }
        }
      },
    }),
    m("button", {
      class: "upload_header_button_view",
      innerText: "Browse",
      onclick: () => {
        document.getElementById("fileInput")?.click();
      },
    }),
  ]);
};

export const Files = (
  upload: UploadState,
  onFileClick: (file: RawFile) => void
) => {
  return m("div.upload_files", [
    upload.files.map((file: RawFile) =>
      m(File_Btn, {
        file: file,
        onFileClick,
      })
    ),
  ]);
};

export const File_Btn = {
  view: function (vnode) {
    const { file, onFileClick } = vnode.attrs;
    let isDisabled = true;
    let ext = file.name.split(".").pop();

    // Check if the file extension is compatible
    const compatibleExtensions = ["py"];
    if (compatibleExtensions.includes(ext)) {
      isDisabled = false;
    }

    return m("div.file_container", [
      m(
        "div.file",
        {
          class: `file__${ext} ${isDisabled ? "disabled" : ""}`,
          file: file,
          onclick: function () {
            if (!isDisabled) {
              onFileClick(file);
            }
          },
        },
        file.name
      ),
    ]);
  },
};
