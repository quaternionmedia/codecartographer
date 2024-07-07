import m from 'mithril';

import './url_input.css';
import { ICell } from '../../state';

let value = 'https://github.com/quaternionmedia/moe';

export const UrlInput = (cell: ICell, handleUrlInput: () => void) =>
  m('section', { class: 'url' }, [
    m('div', {
      class: 'url_header',
      innerText: 'GitHub Repository URL:',
    }),
    m('input', {
      autofocus: true,
      class: 'url_input',
      placeholder: 'Enter a GitHub URL',
      value: cell.state.repo_url || value,
      onkeypress: function (e) {
        if (e.key == ' ') {
          // prevent the space key
          return false;
        } else {
          if (e.key == 'Enter') {
            // set the value and call the handle
            cell.state.repo_url = e.target.value;
            handleUrlInput();
          } else {
            // add the key to the value
            value = this.value + e.key;
            this.value = this.value + e.key;
            cell.state.repo_url = e.target.value;
          }
        }
      },
    }),
    m('button', {
      class: 'url_btn',
      innerText: 'Submit',
      onclick: () => {
        cell.state.repo_url = value;
        handleUrlInput();
      },
    }),
    m('div', { class: 'loading', style: 'display: none' }, 'Loading ...'),
  ]);
