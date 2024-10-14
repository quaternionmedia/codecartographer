import m from 'mithril';

import { StateController } from '../../state/state_controller';
import { ICell } from '../../state/cell_state';
import { Nav } from '../navigation/nav';
import { UrlInput, InputState } from '../url_input/url_input';
import { Plot } from '../plot/plot';
import {
  DirectoryState,
  DirectoryNav,
} from '../nav_content/directory/directory_nav';
import { UploadState, UploadNav } from '../nav_content/upload/upload_nav';
import { RepoService } from '../../services/repo_service';
import { PlotService } from '../../services/plot_service';
import { handleDemoData } from '../../services/demo_service';
import { displayError } from '../../utility';
import { Directory, RawFile, RepoInfo } from '../models/source';
import './codecarto.css';

/** The Code Cartographer app component */
export const CodeCarto = (cell: ICell) => {
  var appState = new StateController(cell);

  /** Create an iframe for each output */
  const handlePlotData = (data: Array<object>) => {
    let nbFrame: m.Vnode[] = [];

    // Check if the output is an HTML file
    if (data && data.length > 0) {
      data.forEach((output) => {
        if (output['text/html']) {
          nbFrame.push(
            m('iframe.graph_content.nbFrame', {
              srcdoc: output['text/html'],
            })
          );
        }
      });
    }

    // Update the app state with the new graph content
    appState.toggleNavs();
    appState.update({ graphContent: nbFrame });
    m.redraw();
  };

  /** Check the inputted URL to be processed */
  const onUrlInput = async (url: string) => {
    // Check if the URL is valid GitHub URL
    if (!url || url === '') {
      displayError('Please enter a URL');
    } else if (url.includes('github.com') || url.split('/').length < 5) {
      displayError('Invalid GitHub URL format');
    }

    // Clear the current repo data and graph content
    appState.clearRepoData();
    appState.clearGraphContent();
    m.redraw();

    // Get the data from the URL
    const repoData = await RepoService.getGithubRepo(url, appState.api.parser);
    if (repoData !== undefined) {
      appState.update({
        repo: { selectedURL: url, content: repoData, isMenuOpen: true },
      });
      m.redraw();
    }
  };

  /** Plot the file using the file's URL */
  const onUrlFileClicked = async () => {
    // Check if the file is selected
    if (!appState.repo.selectedFile || appState.repo.selectedFile.size === 0) {
      displayError('Please select a file');
      return;
    }

    // Clear the current graph content
    appState.clearGraphContent();
    m.redraw();

    // Plot the file using the file's URL
    const data = await PlotService.plotGithubFile(
      appState.repo.selectedFile.url,
      appState.api.plotter
    );
    if (data !== null) handlePlotData(data);
  };

  /** Plot the file using the file's raw data */
  const onUploadedFileClick = async (file: RawFile) => {
    // Check if the file is selected
    if (!file) {
      displayError('Please select a file');
      return;
    }

    // Clear the current graph content
    appState.clearGraphContent();
    m.redraw();

    // Plot the file using the file
    const data = await PlotService.plotFile(file, appState.api.plotter);
    if (data !== null) handlePlotData(data);
  };

  /** Plot the entire loaded repo */
  const onWholeRepoClicked = async () => {
    // Check if the file is selected
    if (!appState.repo.selectedFile || appState.repo.selectedFile.size === 0) {
      displayError('Please enter a URL');
      return;
    }

    // Clear the current graph content
    appState.clearGraphContent();
    m.redraw();

    // Plot the entire repo
    const data = await PlotService.plotGithubWhole(
      appState.repo.selectedFile.url,
      appState.api.plotter
    );
    if (data !== null) handlePlotData(data);
  };

  /** Plot the entire uploaded files as a single source */
  const onWholeSourceClicked = async () => {};

  /** Plot the demo data */
  const demo_button = m('button', {
    class: 'demo_btn',
    innerText: 'Demo',
    onclick: async () => {
      appState.clearGraphContent();
      m.redraw();

      handleDemoData(handlePlotData);
    },
  });

  /** The app's title component */
  const title = m('div.header.app_header', ['Code Cartographer', demo_button]);

  return [
    Nav(
      'left',
      appState.cell.state.repo.isMenuOpen,
      DirectoryNav(
        new DirectoryState(
          appState.repo.component,
          appState.repo.selectedFile.url,
          appState.repo.content,
          onUrlFileClicked,
          onWholeRepoClicked,
          (directory: DirectoryState) => {
            appState.update({
              repo: {
                selectedURL: directory.selectedUrl,
                component: directory.navContent,
              },
            });
          }
        )
      ),
      () => {
        appState.toggleDirectoryNav();
      }
    ),
    Nav(
      'right',
      appState.local.isMenuOpen,
      UploadNav(
        new UploadState(
          appState.local.component,
          appState.local.selectedFile,
          appState.local.content.root.files as RawFile[],
          onUploadedFileClick,
          onWholeSourceClicked,
          (upload: UploadState) => {
            appState.update({
              local: {
                selectedFile: upload.selected_file,
                component: upload.nav_content,
                content: new Directory(new RepoInfo(), upload.files.length, {
                  files: upload.files,
                }),
              },
            });
          }
        )
      ),
      () => {
        appState.toggleUploadNav();
      }
    ),
    m('div.codecarto', [
      title,
      UrlInput(new InputState(onUrlInput)),
      Plot(appState.cell.state.graphContent),
    ]),
  ];
};
