import { ICell } from '../state';
import { Request } from './request_handler';

/**
 * Get the directories and files from a given GitHub URL.
 * @param {Object} cell - The cell to be updated.
 */
export async function handleGithubURL(
  cell: ICell,
  updateRepoData: (data: any, url: string) => void
): Promise<void> {
  // empty the content
  const directory = getHTMLElement('directory');
  if (directory) directory.innerHTML = '';
  cell.state.repo_data = [];
  cell.state.directory_content = [];

  // get the url input
  const urlInput = getHTMLElement('url_input') as HTMLInputElement;
  if (urlInput) {
    let url = urlInput.value;

    // return if the url is empty
    if (!url || url === '') {
      updateMessage('Please enter a URL');
      return;
    }
    updateMessage('Loading...');

    // check for the trailing slash
    if (url[url.length - 1] !== '/') url += '/';

    // encode the url and create the href line
    const encodedGithubUrl = encodeURIComponent(url);
    const proc_url = cell.state.configurations.processor_url;
    const href_line = `${proc_url}/parser/handle_github_url?github_url=${encodedGithubUrl}`;

    // try calling the backend
    try {
      var data = await Request(href_line);

      // Check if the data is null
      if (!data) {
        updateMessage('No content received');
      } else {
        const showFiles = getHTMLElement('nav__toggle');
        if (showFiles) showFiles.classList.add('nav__toggle--open');
        updateRepoData(data, url);
        updateMessage();
      }
    } catch (error) {
      // some error occurred with the fetch
      displayError(
        'url_content',
        'JS Error',
        `Error - parse.js - handleGithubURL(): ${error}`
      );
    }
  }
}

// ###################### DIRECTORY UTILITIES ######################
/**
 * Update the message displayed to the user.
 * @param {string} message - The message to be displayed.
 */
function updateMessage(message: string = '') {
  const MessageComp = getHTMLElement('loading') as HTMLElement;
  if (MessageComp) {
    MessageComp.innerHTML = message;
    MessageComp.style.display = message === '' ? 'none' : 'inline';
  }
}

/**
 * Display an error message to the user.
 * @param {string} elementId - The ID of the element to be updated.
 * @param {string} message - The error message to be displayed.
 * @param {string} detail - The error detail to be displayed.
 */
function displayError(elementId: string, message: string, detail: string) {
  updateMessage(message);
  console.error(elementId, message, detail);
}

/**
 * Get HTML element by class name. Returns first in list of all.
 * @param {string} classname - The class name of the element.
 * @returns {Element | null} - The HTML element.
 */
function getHTMLElement(classname: string): Element | null {
  const elemList = document.getElementsByClassName(classname);
  if (elemList && elemList.length > 0) return elemList[0];
  return null;
}
