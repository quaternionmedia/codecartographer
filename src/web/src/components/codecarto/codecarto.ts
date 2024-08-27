import m from 'mithril';

import { ICell, StateController } from '../../state';
import { Nav } from '../navigation/nav';
import { UrlInput } from '../url_input/url_input';
import { Plot } from '../plot/plot';
import { DirectoryNav } from '../nav_content/directory/directory_nav';
import { UploadNav } from '../nav_content/upload/upload_nav';
import { RepoService } from '../../services/repo_service';
import { PlotService } from '../../services/plot_service';
import { handleDemoData } from '../../services/demo_service';
import { displayError } from '../../utility';
import './codecarto.css';

export const CodeCarto = (cell: ICell) => {
  function get_proc_url(): string {
    const proc_url = cell.state.configurations.processor_url;
    if (!proc_url) {
      displayError('Server is unavailable. Try again later.');
    }
    return proc_url as string;
  }

  const handleWholeRepo = async () => {
    StateController.clearGraphContent(cell);
    m.redraw();

    if (!cell.state.repo_url || cell.state.repo_url === '') {
      displayError('Please enter a URL');
    }

    const data = await PlotService.plotGithubWhole(
      cell.state.repo_url,
      get_proc_url()
    );
    if (data !== null) {
      handlePlotData(data);
    }
  };

  const handleUrlInput = async (url: string) => {
    // Check the URL to be processed
    if (!url || url === '') {
      displayError('Please enter a URL');
    }
    const parts = url.split('/');
    if (parts.length < 5 || parts[2] !== 'github.com') {
      displayError('Invalid GitHub URL format');
    }

    // Get the data from the URL
    const data = await RepoService.getGithubRepo(url, get_proc_url());
    if (data !== undefined) {
      StateController.update(cell, {
        repo_url: url,
        repo_owner: data.package_owner,
        repo_name: data.package_name,
        repo_data: data.contents,
        showDirectoryNav: true,
      });
      m.redraw();
    }
  };

  const handleUrlSelect = async (url: string) => {
    if (!url || url === '') {
      displayError('Please select a URL');
    }

    StateController.clearGraphContent(cell);
    m.redraw();

    const data = await PlotService.plotGithubFile(url, get_proc_url());
    if (data !== null) {
      handlePlotData(data);
    }
  };

  const onUploadedFileClick = async (file: File) => {
    StateController.clearGraphContent(cell);
    m.redraw();

    if (!file) {
      displayError('Please select a file');
    }

    const data = await PlotService.plotFile(file, get_proc_url());
    if (data !== null) {
      handlePlotData(data);
    }
  };

  const handlePlotData = (data: Array<object>) => {
    // Create an iframe for each output
    let nbFrame: m.Vnode[] = [];
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
    StateController.update(cell, {
      graph_content: nbFrame,
      showDirectoryNav: false,
      showUploadNav: false,
    });
    m.redraw();
  };

  const demo_button = m('button', {
    class: 'demo_btn',
    innerText: 'Demo',
    onclick: async () => {
      StateController.clearGraphContent(cell);
      m.redraw();

      handleDemoData(handlePlotData);
    },
  });
  const title = m('div.header.app_header', ['Code Cartographer', demo_button]);

  return [
    Nav(
      cell,
      'showDirectoryNav',
      DirectoryNav(cell, handleUrlSelect, handleWholeRepo),
      'left'
    ),
    Nav(cell, 'showUploadNav', UploadNav(cell, onUploadedFileClick), 'right'),
    m('div.codecarto', [title, UrlInput(handleUrlInput), Plot(cell)]),
  ];
};
