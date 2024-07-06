import m from 'mithril';

import './codecarto.css';
import { ICell } from '../../state';
import { Plot } from '../plot/plot';
import { UrlInput } from '../url_input/url_input';

export const CodeCarto = (cell: ICell) => {
  const title = m('div.header', 'Code Cartographer');

  const setSelectedUrl = (url: string) => {
    // Call PlotFile or any other processing needed
    cell.state.selected_url = url;
    PlotFile(url);
  };

  const updateRepoData = (data: any, url: string) => {
    // Update the cell with the new content
    cell.update({
      plot_repo_url: `/plotter/?is_repo=true&file_url=${url}`,
      repo_url: url,
      repo_owner: data.package_owner,
      repo_name: data.package_name,
      repo_data: data.contents,
      showContentNav: true,
    });

    // Trigger a redraw to update the view
    m.redraw();
  };

  const PlotFile = (url: string) => {
    // Implement the logic to plot the file using the URL
    console.log('Plotting file from URL:', url);
  };

  return [title, UrlInput(cell, updateRepoData), Plot(cell, setSelectedUrl)];
};
