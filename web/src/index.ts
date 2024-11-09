import './styles/index.css';

import m from 'mithril';
import { meiosisSetup } from 'meiosis-setup';

import { qmComponentSetup } from './utility';
import { ICell, ICellState, CellState } from './state/cell_state';
import { CodeCarto } from './components/codecarto/codecarto';

qmComponentSetup();

var debugDefaultUrl = 'https://github.com/quaternionmedia/codecartographer';

// Initialize the app
const App = {
  initial: new CellState(debugDefaultUrl),
  services: [],
  view: (cell: ICell) => [CodeCarto(cell)],
};

// Initialize Meiosis
const cells = meiosisSetup<ICellState>({ app: App });
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

// DEBUG
declare global {
  interface Window {
    cells: any;
  }
}
window.cells = cells;
// Tracer(cells);
