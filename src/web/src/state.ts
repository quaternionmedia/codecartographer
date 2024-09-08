import m from "mithril";
import { MeiosisCell, Patch } from "meiosis-setup/types";
import { RawFile, Repo } from "./components/models/source";

export interface ICell extends MeiosisCell<State> {}

export interface DebugOptions {
  menu?: boolean;
  tracer?: boolean;
}

export interface Configurations {
  processorUrl?: string;
}

export interface State {
  debug: DebugOptions;
  configurations: Configurations;

  inputUrl: string;
  selectedUrl: string;
  repoData: Repo;
  showDirectoryNav: boolean;
  dirNavContent: m.Vnode[];

  selectedFile: RawFile | null;
  uploadedFiles: RawFile[];
  showUploadNav: boolean;
  uploadNavContent: m.Vnode[];

  graphContent: m.Vnode[];
}

export const InitialState: State = {
  debug: {
    menu: false,
    tracer: false,
  },

  configurations: {
    processorUrl: "http://localhost:2020",
  },

  inputUrl: "",
  selectedUrl: "",
  repoData: new Repo(),
  showDirectoryNav: false,
  dirNavContent: [],

  selectedFile: null,
  uploadedFiles: [],
  showUploadNav: false,
  uploadNavContent: [],

  graphContent: [],
};

export class StateController {
  public static currentCell: ICell;

  public static initialize(cell: ICell) {
    this.currentCell = cell;
  }

  public static clearGithubData() {
    if (this.currentCell) {
      this.update({
        repoData: new Repo(),
        dirNavContent: [],
      });
    }
  }
  public static clearAllFileData() {
    if (this.currentCell) {
      this.update({
        uploadedFiles: [],
        uploadNavContent: [],
        selectedFile: undefined,
      });
    }
  }
  public static clearGraphContent() {
    if (this.currentCell) {
      this.update({ graphContent: [] });
    }
  }
  public static clearSelectedFile() {
    if (this.currentCell) {
      this.update({ selectedFile: undefined });
    }
  }

  /** Clear all data from the cell */
  public static clear() {
    if (this.currentCell) {
      this.clearGithubData();
      this.clearAllFileData();
      this.clearGraphContent();
    }
  }

  /** Update the cell with the new content */
  public static update(state: Patch<State>) {
    if (this.currentCell) {
      console.log("StateController.update: passed state: \n", state);
      this.currentCell.update(state);
      console.log(
        "StateController.update: updated state: ",
        this.currentCell.state
      );
    }
  }

  public static setSelectedFile(file: RawFile) {
    if (this.currentCell) {
      this.update({ selectedFile: file });
    }
  }

  /** toggle directory nav */
  public static toggleDirectoryNav() {
    if (this.currentCell) {
      this.update({
        showDirectoryNav: !this.currentCell.state.showDirectoryNav,
      });
    }
  }

  /** toggle upload nav */
  public static toggleUploadNav() {
    if (this.currentCell) {
      this.update({
        showUploadNav: !this.currentCell.state.showUploadNav,
      });
    }
  }
}
