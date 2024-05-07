import m from "mithril"; 

import './home.css'

export const Home = ({ state, update }) => m("div.home", [
  m("button", { onclick: () => update({page: 'palette'}) }, "Palette"),
  m("button", { onclick: () => update({page: 'plotter'}) }, "Plotter"),
  m("button", { onclick: () => update({page: 'parser'}) }, "Parser"),
  m("button", { onclick: () => update({page: 'graphs'}) }, "Saved Graphs")
]);
