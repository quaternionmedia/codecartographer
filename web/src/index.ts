import m from "mithril";
import { meiosisSetup } from "meiosis-setup";

import { DebugNavContent, Tracer } from "./components/debug/Debug";
import { State } from "./state";
import { Nav } from "./components/navigation/nav";
import { Router } from "./router";
import "./pages/index.css";

const initial: State = {
  debug: {
    menu: false,
    tracer: true,
  },
  page: "home",
};

export const App = {
  initial,
  services: [],
  view: (cell) => [
    m("div.ui", [Nav(cell, "debugActive", "right", DebugNavContent(cell))]),
    m("div.page", [m("h1.header", "Code Cartographer"), Router(cell)]),
  ],
};

// Initialize Meiosis
const cells = meiosisSetup<State>({ app: App });

m.mount(document.getElementById("app"), {
  view: () => App.view(cells()),
});

cells.map((state) => {
  //   console.log('cells', state)

  //   Persist state to local storage
  //   localStorage.setItem('meiosis', JSON.stringify(state))
  m.redraw();
  adjustForURLBar();
});

function adjustForURLBar() {
  // Set a CSS variable on the root element with the current viewport
  document.documentElement.style.setProperty("--vh", `${window.innerHeight * 0.01}px`);
  document.documentElement.style.setProperty("--vw", `${window.innerWidth * 0.01}px`);
}

// Debug
declare global {
  interface Window {
    cells: any;
  }
}
window.cells = cells;

Tracer(cells);
