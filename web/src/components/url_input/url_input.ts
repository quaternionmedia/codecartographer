import m from 'mithril';

import { ICell } from '../../state';
import './url_input.css';

let trackedValue = '';

export const UrlInput = (cell: ICell, handleUrlInput: () => void) =>
  m('section.url', [
    title,
    input(cell, handleUrlInput),
    submit(cell, handleUrlInput),
    message,
  ]);

const title = m('div.header', {
  class: 'url_header',
  innerText: 'GitHub Repository URL:',
});

const message = m('div', {
  class: 'loading',
  style: 'display: none',
});

const input = (cell: ICell, handleUrlInput: () => void) =>
  m('input', {
    autofocus: true,
    class: 'url_input',
    placeholder: 'Enter a GitHub URL',
    // needs to be keyup up to set value after something like ctrl+v
    onkeyup: (e) => {
      trackedValue = e.target.value;
      cell.state.repo_url = e.target.value;
      if (e.key === 'Enter') {
        handleUrlInput();
      }
    },
  });

const submit = (cell: ICell, handleUrlInput: () => void) =>
  m('button', {
    class: 'url_btn',
    innerText: 'Submit',
    onclick: () => {
      cell.state.repo_url = trackedValue;
      handleUrlInput();
    },
  });
