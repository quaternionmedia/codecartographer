import m from 'mithril';

import './url_input.css';

let trackedValue = '';

export const UrlInput = (handleUrlInput: (url: string) => void) =>
  m('section.url', [
    title,
    input(handleUrlInput),
    submit(handleUrlInput),
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

const input = (handleUrlInput: (url: string) => void) =>
  m('input', {
    autofocus: true,
    class: 'url_input',
    placeholder: 'Enter a GitHub URL',
    // needs to be keyup up to set value after something like ctrl+v
    onkeyup: (e) => {
      trackedValue = e.target.value;
      if (e.key === 'Enter') {
        handleUrlInput(trackedValue);
      }
    },
  });

const submit = (handleUrlInput: (url: string) => void) =>
  m('button', {
    class: 'url_btn',
    innerText: 'Submit',
    onclick: () => {
      handleUrlInput(trackedValue);
    },
  });
