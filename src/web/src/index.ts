import m from 'mithril';
import { meiosisSetup } from 'meiosis-setup';
import { getViewPortSize } from './utility';
import { ICell, ICellState, CellState } from './state/cell_state';
import './styles/index.css';
import { CodeCarto } from './components/codecarto/codecarto';

var intiialState = new CellState();

// Initialize the app
const App = {
  initial: intiialState,
  services: [],
  view: (cell: ICell) => [
    //m('div.ui', [Nav(cell, 'debugActive', 'right', DebugNavContent(cell))]),
    CodeCarto(cell),
    //var codecarto = new CodeCarto();
    //codecarto.View(cell),
  ],
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
getViewPortSize();

// Debug
declare global {
  interface Window {
    cells: any;
  }
}
window.cells = cells;
// Tracer(cells);
