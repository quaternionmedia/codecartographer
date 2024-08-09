import m from 'mithril';

import { ICell } from '../../state';
import { Nav } from '../navigation/nav';
import { UrlInput } from '../url_input/url_input';
import { Plot } from '../plot/plot';
import { DirectoryNav } from '../nav_content/directory/directory_nav';
import { Upload } from '../nav_content/upload/upload';
import {
  handleGithubURL,
  plotGithubUrl,
  plotUploadedFile,
} from '../../services/repo_service';
import { handleDemoData } from '../../services/demo_service';
import './codecarto.css';

export const CodeCarto = (cell: ICell) => {
  const handleUrlInput = async () => {
    handleGithubURL(cell, updateGithubData);
  };

  const updateGithubData = (data: any, url: string) => {
    // Update the cell with the new content
    cell.update({
      plot_repo_url: `/plotter/?is_repo=true&file_url=${url}`,
      repo_url: url,
      repo_owner: data.package_owner,
      repo_name: data.package_name,
      repo_data: data.contents,
      showDirectoryNav: true,
    });

    // Trigger a redraw to update the view
    m.redraw();
  };

  const setSelectedUrlFile = (url: string) => {
    cell.state.selected_url_file = url;
    plotGithubUrl(cell, handlePlotData);
  };

  const setSelectedUploadedFile = (file: File) => {
    cell.state.selected_uploaded_file = file;
    plotUploadedFile(cell, handlePlotData);
  };

  const handlePlotData = (data: Array<object>) => {
    let nbFrame: m.Vnode[] = [];
    if (data && data.length > 0) {
      // Create an iframe for each output
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

    // Update the cell with the new content
    cell.update({
      graph_content: nbFrame,
      showDirectoryNav: false,
    });

    // Trigger a redraw to update the view
    m.redraw();
  };

  const demo_button = m('button', {
    class: 'demo_btn',
    innerText: 'Demo',
    onclick: async () => {
      cell.update({
        repo_data: [],
        directory_content: [],
        graph_content: [],
        plot_repo_url: '',
      });
      handleDemoData(handlePlotData);
    },
  });
  const title = m('div.header.app_header', ['Code Cartographer', demo_button]);

  return [
    Nav(cell, 'showDirectoryNav', DirectoryNav(cell, setSelectedUrlFile)),
    Nav(cell, 'showUploadNav', Upload(cell, setSelectedUploadedFile), 'right'),
    m('div.codecarto', [title, UrlInput(cell, handleUrlInput), Plot(cell)]),
  ];
};
