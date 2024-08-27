import m from 'mithril';
import { meiosisSetup } from 'meiosis-setup';

import './styles/index.css';
import { InitialState, ICell, State } from './state';
import { CodeCarto } from './components/codecarto/codecarto';
import { getViewPortSize } from './utility';

// Initialize the app
const App = {
  initial: InitialState,
  services: [],
  view: (cell: ICell) => [
    //m('div.ui', [Nav(cell, 'debugActive', 'right', DebugNavContent(cell))]),
    CodeCarto(cell),
  ],
};

// Initialize Meiosis
const cells = meiosisSetup<State>({ app: App });
cells.map(() => {
  m.redraw();
});

// Mount the app
const app = document.getElementById('app');
if (app) {
  m.mount(app, {
    view: () => App.view!(cells()),
  });
}
getViewPortSize();

// Debug
declare global {
  interface Window {
    cells: any;
  }
}
window.cells = cells;
// Tracer(cells);
