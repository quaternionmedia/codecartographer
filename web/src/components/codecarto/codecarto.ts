import m from 'mithril';

import './codecarto.css';
import { ICell } from '../../state';
import { Plot } from '../plot/plot';
import { UrlInput } from '../url_input/url_input';
import { handleGithubURL } from '../../services/repo_service';

export const CodeCarto = (cell: ICell) => {
  const title = m('div.header', 'Code Cartographer');

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
      showContentNav: true,
    });

    // Trigger a redraw to update the view
    m.redraw();
  };

  return [title, UrlInput(cell, handleUrlInput), Plot(cell)];
};
