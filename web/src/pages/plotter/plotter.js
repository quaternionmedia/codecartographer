import m from 'mithril';

import './plotter.css';
import { plot } from '../../services/plotter_service';

//TODO: translate the original html/js code to mithril

export const Plotter = ({ state, update }) => [
  m('section#parser_desc', [
    m('h2', { style: 'margin-top: -20px' }, 'Plotter'),
    m('button', { onclick: () => update({ page: 'home' }) }, 'Return Home'),
  ]),
  m('section#plot_config', [
    m('h2', 'Plot Graph'),
    m('select', { name: 'layouts', id: 'layouts' }, [
      m('option', { value: 'Circular' }, 'Circular'),
      m('option', { value: 'Spectral' }, 'Spectral'),
      m('option', { value: 'Shell' }, 'Shell'),
      m('option', { value: 'Spiral' }, 'Spiral'),
      m('option', { value: 'Spring' }, 'Spring'),
      m('option', { value: 'Sorted_Square' }, 'Square'),
    ]),
    m('select', { name: 'demos', id: 'demos' }, [
      m('option', { value: 'demo' }, 'Demo Graph'),
      m('option', { value: 'src/plotter/palette.py' }, 'palette.py'),
      m('option', { value: 'src/parser/parser.py' }, 'parser.py'),
      m('option', { value: 'src/plotter/plotter.py' }, 'plotter.py'),
      m('option', { value: 'src/polygraph/polygraph.py' }, 'polygraph.py'),
      m('option', { value: 'src/plotter/positions.py' }, 'positions.py'),
      m('option', { value: 'src/processor.py' }, 'processor.py'),
    ]),
    m(
      'div#fileUrl',
      { 'data-url': state.source_code_path },
      state.source_code_path
    ),
    m('br'),
    m('button#gv_single', { onclick: () => plot(state) }, 'Single Layout'),
    m(
      'button#gv_grid.red_button',
      { onclick: () => plot(state, false, true, true) },
      'Grid of d3, vis, three'
    ),
    m('br'),
    //m("button#plot_moe", { onclick: () => openInMoe(true), style: "display: none" }, "Open in Moe"),
    m('div#plot_loader.loader', { style: 'display: none' }, 'Loading ...'),
    m('div#plot_sent_to_moe.loader', { style: 'display: none' }, 'Sent to Moe'),
  ]),
  m('section#plot_display', [m('div#plot'), m('section#output')]),
];
