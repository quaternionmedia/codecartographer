import m from 'mithril';

import './palette.css';
import { getPalette } from '../../../services/parser_service';

window.onload = function () {
  //getPalette()
};

export const Palette = ({ state, update }) => [
  m('section#palette_desc', [
    m('h2', { style: 'margin-top: -20px' }, 'Palette'),
    m('button', { onclick: () => update({ page: 'home' }) }, 'Return Home'),
  ]),
  m('br'),
  m('section#palette_display', [
    m('h2', 'Default Palette Properties'),
    m('div#pal_data'),
  ]),
];
