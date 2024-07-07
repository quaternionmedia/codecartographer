import m from 'mithril';

import { ICell } from '../../state';
import { Plot } from '../plot/plot';
import { UrlInput } from '../url_input/url_input';
import { Directory } from '../directory/directory';
import { Nav } from '../navigation/nav';
import { handleGithubURL, plotGithubUrl } from '../../services/repo_service';
import './codecarto.css';

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

  // const setSelectedUrl = (url: string) => {
  //   cell.state.selected_file_url = url;
  //   plotGithubUrl(cell, handlePlotData);
  // };

  // const handlePlotData = (data: Array<object>) => {
  //   let nbFrame: m.Vnode[] = [];
  //   if (data && data.length > 0) {
  //     // Create an iframe for each output
  //     data.forEach((output) => {
  //       if (output['text/html']) {
  //         nbFrame.push(
  //           m('iframe.graph_content.nbFrame', {
  //             srcdoc: output['text/html'],
  //           })
  //         );
  //       }
  //     });
  //   }

  //   // Update the cell with the new content
  //   cell.update({
  //     graph_content: nbFrame,
  //     showContentNav: false,
  //   });

  //   // Trigger a redraw to update the view
  //   m.redraw();
  // };

  return [
    title,
    UrlInput(cell, handleUrlInput),
    //Nav(cell, 'showContentNav', Directory(cell, setSelectedUrl)),
    Plot(cell),
  ];
};
