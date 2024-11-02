import m from 'mithril';

import './url_input.css';

export class InputState {
  onUrlInput: (url: string) => void;
  url: string = '';

  constructor(onUrlInput: (url: string) => void, defaultUrl: string = '') {
    this.onUrlInput = onUrlInput;
    this.url = defaultUrl; // Used during development & testing
  }

  input = () =>
    m('input', {
      autofocus: true,
      class: 'url_input',
      placeholder: 'Enter a GitHub URL',
      // needs to be keyup up to set value after something like ctrl+v
      onkeyup: (e: any) => {
        this.url = e.target.value;
        if (e.key === 'Enter') {
          this.onUrlInput(this.url);
        }
      },
    });

  submit = () =>
    m('button', {
      class: 'url_btn',
      innerText: 'Submit',
      onclick: () => {
        this.onUrlInput(this.url);
      },
    });
}

const title = m('div.header', {
  class: 'url_header',
  innerText: 'GitHub Repository URL:',
});

const message = m('div', {
  class: 'loading',
  style: 'display: none',
});

export const UrlInput = (urlInput: InputState) =>
  m('section.url', [title, urlInput.input(), urlInput.submit(), message]);
