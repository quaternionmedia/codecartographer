import m from 'mithril';

import './url_input.css';
import { ICell } from '../../state';
import { handleGithubURL } from '../../services/repo_service';

export const UrlInput = (
  cell: ICell,
  updateRepoData: (data: any, url: string) => void
) =>
  m('section', { class: 'url' }, [
    title,
    input(cell, updateRepoData),
    button(cell, updateRepoData),
    loading,
  ]);

let defaultUrl = 'https://github.com/quaternionmedia/moe';

const title = m('div', {
  class: 'url_header',
  innerText: 'GitHub Repository URL:',
});

const input = (cell: ICell, updateRepoData: (data: any, url: string) => void) =>
  m('input', {
    autofocus: true,
    class: 'url_input',
    placeholder: 'Enter a GitHub URL',
    // if cell.state.repo_url is empty, then use the default value
    value: cell.state.repo_url || defaultUrl,
    oninput: (e) => {
      cell.update({ repo_url: e.target.value });
    },
    onkeypress: (e) => {
      if (e.key === 'Enter') {
        handleGithubURL(cell, updateRepoData);
      }
    },
  });

const button = (
  cell: ICell,
  updateRepoData: (data: any, url: string) => void
) =>
  m('button', {
    class: 'url_btn',
    innerText: 'Submit',
    onclick: () => {
      handleGithubURL(cell, updateRepoData);
    },
  });

const loading = m(
  'div',
  { class: 'loading', style: 'display: none' },
  'Loading ...'
);
