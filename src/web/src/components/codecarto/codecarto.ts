import m from "mithril";

import { ICell, StateController } from "../../state";
import { Nav } from "../navigation/nav";
import { UrlInput, InputState } from "../url_input/url_input";
import { Plot } from "../plot/plot";
import {
  DirectoryState,
  DirectoryNav,
} from "../nav_content/directory/directory_nav";
import { UploadState, UploadNav } from "../nav_content/upload/upload_nav";
import { RepoService } from "../../services/repo_service";
import { PlotService } from "../../services/plot_service";
import { handleDemoData } from "../../services/demo_service";
import { displayError } from "../../utility";
import "./codecarto.css";
import { RawFile, Repo } from "../models/source";

export const CodeCarto = (cell: ICell) => {
  StateController.initialize(cell);

  function get_proc_url(): string {
    const proc_url =
      StateController.currentCell.state.configurations.processorUrl;
    if (!proc_url) displayError("Server is unavailable. Try again later.");
    return proc_url as string;
  }

  const handlePlotData = (data: Array<object>) => {
    // Create an iframe for each output
    let nbFrame: m.Vnode[] = [];
    if (data && data.length > 0) {
      data.forEach((output) => {
        if (output["text/html"]) {
          nbFrame.push(
            m("iframe.graph_content.nbFrame", {
              srcdoc: output["text/html"],
            })
          );
        }
      });
    }
    StateController.update({
      graphContent: nbFrame,
      showDirectoryNav: false,
      showUploadNav: false,
    });
    m.redraw();
  };

  const handleUrlInput = (data: Repo, url: string) => {
    StateController.update({
      repoData: data,
      selectedUrl: url,
      showDirectoryNav: true,
    });
    m.redraw();
  };

  const onUrlInput = async (url: string) => {
    // Check the URL to be processed
    if (!url || url === "") {
      displayError("Please enter a URL");
    }
    const parts = url.split("/");
    if (parts.length < 5 || parts[2] !== "github.com") {
      displayError("Invalid GitHub URL format");
    }

    StateController.clearGithubData();
    StateController.clearGraphContent();
    m.redraw();

    // Get the data from the URL
    const repoData = await RepoService.getGithubRepo(url, get_proc_url());
    if (repoData !== undefined) handleUrlInput(repoData, url);
  };

  const onUrlFileClicked = async () => {
    if (
      !StateController.currentCell.state.selectedUrl ||
      StateController.currentCell.state.selectedUrl === ""
    ) {
      displayError("Please select a file");
      return;
    }

    StateController.clearGraphContent();
    m.redraw();

    const data = await PlotService.plotGithubFile(
      StateController.currentCell.state.selectedUrl,
      get_proc_url()
    );
    if (data !== null) handlePlotData(data);
  };

  const onWholeRepoClicked = async () => {
    if (
      !StateController.currentCell.state.selectedUrl ||
      StateController.currentCell.state.selectedUrl === ""
    ) {
      displayError("Please enter a URL");
      return;
    }

    StateController.clearGraphContent();
    m.redraw();

    const data = await PlotService.plotGithubWhole(
      StateController.currentCell.state.selectedUrl,
      get_proc_url()
    );
    if (data !== null) handlePlotData(data);
  };

  const onUploadedFileClick = async (file: RawFile) => {
    if (!file) {
      displayError("Please select a file");
      return;
    }

    StateController.clearGraphContent();
    m.redraw();

    const data = await PlotService.plotFile(file, get_proc_url());
    if (data !== null) handlePlotData(data);
  };

  const onWholeSourceClicked = async () => {};

  const demo_button = m("button", {
    class: "demo_btn",
    innerText: "Demo",
    onclick: async () => {
      StateController.clearGraphContent();
      m.redraw();

      handleDemoData(handlePlotData);
    },
  });
  const title = m("div.header.app_header", ["Code Cartographer", demo_button]);

  return [
    Nav(
      "left",
      StateController.currentCell.state.showDirectoryNav,
      DirectoryNav(
        new DirectoryState(
          StateController.currentCell.state.dirNavContent,
          StateController.currentCell.state.selectedUrl,
          StateController.currentCell.state.repoData,
          onUrlFileClicked,
          onWholeRepoClicked,
          (directory: DirectoryState) => {
            StateController.update({
              dirNavContent: directory.navContent,
              selectedUrl: directory.selectedUrl,
            });
          }
        )
      ),
      () => {
        StateController.toggleDirectoryNav();
      }
    ),
    Nav(
      "right",
      StateController.currentCell.state.showUploadNav,
      UploadNav(
        new UploadState(
          StateController.currentCell.state.uploadNavContent,
          StateController.currentCell.state.selectedFile,
          StateController.currentCell.state.uploadedFiles,
          onUploadedFileClick,
          onWholeSourceClicked,
          (upload: UploadState) => {
            StateController.update({
              uploadNavContent: upload.nav_content,
              uploadedFiles: upload.files,
              selectedFile: upload.selected_file,
            });
          }
        )
      ),
      () => {
        StateController.toggleUploadNav();
      }
    ),
    m("div.codecarto", [
      title,
      UrlInput(
        new InputState(
          StateController.currentCell.state.inputUrl,
          onUrlInput,
          (input: InputState) => {
            StateController.update({ inputUrl: input.url });
          }
        )
      ),
      Plot(StateController.currentCell.state.graphContent),
    ]),
  ];
};
