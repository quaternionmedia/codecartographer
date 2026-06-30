import './styles/index.css';

import m from 'mithril';
import { meiosisSetup } from 'meiosis-setup';

import { qmComponentSetup } from './utility';
import { ICell, ICellState, CellState } from './state/cell_state';
import { GoldenLayoutShell } from './layout/golden_layout_shell';

qmComponentSetup();

var debugDefaultUrl = 'https://github.com/quaternionmedia/codecartographer';

// Initialize the app
const App = {
  initial: new CellState(),
  services: [],
};

// Initialize Meiosis
const cells = meiosisSetup<ICellState>({ app: App });

// Redraw on every state change
cells.map(() => {
  m.redraw();
});

// Mount the app
const app = document.getElementById('app');
if (app) {
  m.mount(app, GoldenLayoutShell(() => cells()));
}

// DEBUG
declare global {
  interface Window {
    cells: ReturnType<typeof cells>;
  }
}
window.cells = cells;
// Tracer(cells);
