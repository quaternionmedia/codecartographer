import m from "mithril";

import "./url_input.css";

let trackedValue = "";

export class InputState {
  onUrlInput: (url: string) => void;

  constructor(onUrlInput: (url: string) => void) {
    this.onUrlInput = onUrlInput;
  }
}

export const UrlInput = (urlInput: InputState) =>
  m("section.url", [title, input(urlInput), submit(urlInput), message]);

const title = m("div.header", {
  class: "url_header",
  innerText: "GitHub Repository URL:",
});

const message = m("div", {
  class: "loading",
  style: "display: none",
});

const input = (urlInput: InputState) =>
  m("input", {
    autofocus: true,
    class: "url_input",
    placeholder: "Enter a GitHub URL",
    // needs to be keyup up to set value after something like ctrl+v
    onkeyup: (e) => {
      trackedValue = e.target.value;
      if (e.key === "Enter") {
        urlInput.onUrlInput(trackedValue);
      }
    },
  });

const submit = (urlInput: InputState) =>
  m("button", {
    class: "url_btn",
    innerText: "Submit",
    onclick: () => {
      urlInput.onUrlInput(trackedValue);
    },
  });
