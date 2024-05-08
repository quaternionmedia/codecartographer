import m from 'mithril';

import { Home } from './pages/home/home';
import { Palette } from './pages/palette/palette';
import { Parser } from './pages/parser/parser';
import { Plotter } from './pages/plotter/plotter';
import { SavedGraphs } from './pages/graphs/graphs';

export const Router = (cell) => {
  let content = Home(cell);
  switch (cell.state.page) {
    case 'palette':
      content = Palette(cell);
      break;
    case 'parser':
      content = Parser(cell);
      break;
    case 'plotter':
      content = Plotter(cell);
      break;
    case 'graphs':
      content = SavedGraphs(cell);
      break;
    default:
      content = Home(cell);
      break;
  }

  return m('div.container', content);
};
