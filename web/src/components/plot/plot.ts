import m from 'mithril';

import { ICell } from '../../state';
import { Nav } from '../navigation/nav';
import { Directory } from '../directory/directory';
import { plotGithubUrl } from '../../services/repo_service';
import './plot.css';

export const Plot = (cell: ICell) => {
  const setSelectedUrl = (url: string) => {
    cell.state.selected_file_url = url;
    plotGithubUrl(cell, handlePlotData);
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
      showContentNav: false,
    });

    // Trigger a redraw to update the view
    m.redraw();
  };

  return m('div.plot', [Graph(cell), DirectoryNav(cell, setSelectedUrl)]);
};

const DirectoryNav = (cell: ICell, setSelectedUrl: (url: string) => void) =>
  Nav(cell, 'showContentNav', Directory(cell, setSelectedUrl));

const Graph = (cell: ICell) => m('div.graph', [cell.state.graph_content]);
