import m from 'mithril';

import { ICell } from '../../state/cell_state';
import { StateController } from '../../state/state_controller';
import { Directory, RawFile, RawFolder, RepoInfo } from '../models/source';

import { Nav, NavSide } from '../qm_comp_lib/navigation/base/nav';
import { DirectoryNavState, DirectoryNav } from './directory/directory_nav';
import { UploadNavState, UploadNav } from './upload/upload_nav';
import { UrlInput, InputState } from './url_input/url_input';
import { Plot } from './plot/plot';

import { RepoService } from '../../services/repo_service';
import { PlotService } from '../../services/plot_service';
import { handleDemoData as getDemoData } from '../../services/demo_service';

import './codecarto.css';

/** The Code Cartographer app component */
export const CodeCarto = (cell: ICell) => {
  var appState = new StateController(cell);

  function handlePlotData(data: Array<object>) {
    // Create an iframe for each output
    let nbFrame: m.Vnode[] = [];
    data.forEach((output) => {
      if (output['text/html']) {
        nbFrame.push(
          m('iframe.graph_content.nbFrame', {
            srcdoc: output['text/html'],
          })
        );
      }
    });
    appState.updatePlotFrame(nbFrame);
  }

  async function onUrlInput(url: string) {
    appState.clear();
    appState.updateRepoContent(
      await RepoService.getGithubRepo(url, appState.api.repoReader)
    );
  }

  async function onUrlFileClicked(url: string) {
    appState.clear();
    handlePlotData(await PlotService.plotUrlFile(url, appState.api.plotter));
  }

  async function onWholeRepoClicked() {
    appState.clear();
    handlePlotData(
      await PlotService.plotRepoWhole(
        appState.repo.content,
        appState.api.plotter
      )
    );
  }

  async function onUploadedFileClick(file: RawFile) {
    appState.clear();
    handlePlotData(await PlotService.plotFile(file, appState.api.plotter));
  }

  async function onWholeSourceClicked() {}

  async function plotDemo() {
    appState.clear();
    handlePlotData(await getDemoData());
  }

  const demo_button = m('button.demo_btn', { onclick: plotDemo }, 'Demo');
  const title = m('div.header.app_header', ['Code Cartographer', demo_button]);
  const inputState = new InputState(onUrlInput, appState.state.inputRepoUrl);
  const codeCarto = m('div.codecarto', [
    title,
    UrlInput(inputState),
    Plot(appState.state.graphContent),
  ]);

  return [
    RepoNav(appState, onUrlFileClicked, onWholeRepoClicked),
    UploadFileNav(appState, onUploadedFileClick, onWholeSourceClicked),
    codeCarto,
  ];
};

const RepoNav = (
  appState: StateController,
  fileClicked: (url: string) => void,
  wholeRepoClicked: () => void
) => {
  function handleRepoUpdated(directory: DirectoryNavState) {
    appState.update({
      repo: {
        selectedUrl: directory.controller.selectedUrl,
        component: directory.controller.component,
      },
    });
  }

  function toggleNav() {
    appState.toggleDirectoryNav();
  }

  let dirNavState = new DirectoryNavState(
    appState.repo,
    fileClicked,
    wholeRepoClicked,
    handleRepoUpdated
  );

  return Nav(
    NavSide.LEFT,
    appState.repo.isMenuOpen,
    DirectoryNav(dirNavState),
    toggleNav
  );
};

const UploadFileNav = (
  appState: StateController,
  fileClicked: (file: RawFile) => void,
  wholeSourceClicked: () => void
) => {
  function handleFileUpload(upload: UploadNavState) {
    appState.update({
      local: {
        selectedFile: upload.selectedFile,
        component: upload.navContent,
        content: new Directory(
          new RepoInfo(),
          upload.files.length,
          new RawFolder('root', 0, upload.files)
        ),
      },
    });
  }

  function toggleNav() {
    appState.toggleUploadNav();
  }

  let uploadNavState = new UploadNavState(
    appState.local,
    fileClicked,
    wholeSourceClicked,
    handleFileUpload
  );

  return Nav(
    NavSide.RIGHT,
    appState.local.isMenuOpen,
    UploadNav(uploadNavState),
    toggleNav
  );
};
