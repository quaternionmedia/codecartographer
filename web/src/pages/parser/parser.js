import m from 'mithril';

import './parser.css';
import { getGraphDesc, handleGithubURL } from '../../services/parser_service';

export const Parser = ({ state, update }) => [
  m('section#parser_desc', [
    m('h2', { style: 'margin-top: -20px' }, 'Parser'),
    m('button', { onclick: () => update({ page: 'home' }) }, 'Return Home'),
  ]),
  m('section#github_url', [
    m('form#githubForm', [
      m('h3', { for: 'githubUrl' }, 'GitHub Repository URL:'),
      m('input', { type: 'text', id: 'githubUrl', name: 'githubUrl' }),
      m(
        'button',
        {
          id: 'githubUrl_btn',
          type: 'button',
          onclick: handleGithubURL(state),
        },
        'Submit'
      ),
      m(
        'div#github_loader',
        { class: 'loader', style: 'display: none' },
        'Loading ...'
      ),
    ]),
    m('div#url_content'),
  ]),
  m('section#parser_display', [m('div#graph_desc', getGraphDesc(state))]),
];
