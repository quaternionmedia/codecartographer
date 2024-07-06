import m from 'mithril';

import './url_input.css';
import { ICell } from '../../state';
import { handleGithubURL } from '../../services/repo_service';

export const UrlInput = (cell: ICell) =>
  m('section', { class: 'url' }, [title, input(cell), button(cell), loading]);

let defaultUrl = 'https://github.com/quaternionmedia/moe';

const title = m('div', {
  class: 'url_header',
  innerText: 'GitHub Repository URL:',
});

const button = (cell: ICell) =>
  m('button', {
    class: 'url_btn',
    innerText: 'Submit',
    onclick: () => {
      handleGithubURL(cell);
    },
  });

const input = (cell: ICell) =>
  m('input.', {
    class: 'url_input',
    autofocus: true,
    placeholder: 'Enter a GitHub URL',
    // if cell.state.repo_url is empty, then use the default value
    value: cell.state.repo_url === '' ? defaultUrl : cell.state.repo_url,
    oninput: (e) => {
      cell.state.repo_url = e.target.value;
    },
    onkeypress: (e) => {
      if (e.key === 'Enter') {
        handleGithubURL(cell);
      }
    },
  });

const loading = m('div.loading', { style: 'display: none' }, 'Loading ...');
