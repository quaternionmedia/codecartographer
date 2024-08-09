import m from 'mithril';
import { ICell } from '../state';
import { Request, PostRequest } from './request_handler';

/**
 * Get the directories and files from a given GitHub URL.
 * @param {Object} cell - The cell to be updated.
 */
export async function handleGithubURL(
  cell: ICell,
  updateGithubData: (data: any, url: string) => void
): Promise<void> {
  // empty the content
  cell.state.repo_data = [];
  cell.state.directory_content = [];
  cell.state.graph_content = [];
  cell.state.plot_repo_url = '';

  // Check the URL to be processed
  let url = cell.state.repo_url;
  const proc_url = cell.state.configurations.processor_url;
  if (!proc_url) {
    displayError(
      'url_content',
      'Server is unavailable at the moment. Please try again later.',
      'Error - parse.js - plotGithubUrl(): Processor URL not found'
    );
    return;
  }

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
  const href_line = `${proc_url}/parser/handle_github_url?github_url=${encodedGithubUrl}`;

  try {
    // try calling the backend
    var data = await Request(href_line);

    // Check if the data is null
    if (!data) {
      updateMessage('No content received');
    } else if (typeof data === 'string') {
      updateMessage(data);
    } else {
      updateGithubData(data, url);
      updateMessage();
    }
  } catch (error) {
    // console.log(error.results.data);
    // some error occurred with the fetch
    displayError(
      'url_content',
      'JS Error',
      `Error - parse.js - handleGithubURL(): ${error}`
    );
  }
}
/**
 * Plot the content of the GitHub URL.
 * @param {string} url - The URL to be plotted.
 */
export async function plotGithubUrl(
  cell: ICell,
  handlePlotData: (data: any) => void
): Promise<void> {
  // empty the content
  cell.state.graph_content = [];

  // Check the selected URL and the processor URL
  let url = cell.state.selected_url_file;
  const proc_url = cell.state.configurations.processor_url;
  if (!proc_url) {
    displayError(
      'url_content',
      'Server is unavailable at the moment. Please try again later.',
      'Error - parse.js - plotGithubUrl(): Processor URL not found'
    );
    return;
  }

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
  const href_line =
    `${proc_url}/plotter/plot?` +
    `url=${encodedGithubUrl}&` +
    `is_repo=${true}&` +
    `graph_data=${{ name: '' }}&` +
    `db_graph=${false}&` +
    `demo=${false}&` +
    `demo_file=${''}&` +
    `layout=${'Spectral'}&` +
    `gv=${true}&` +
    `type=${'d3'}`;

  try {
    // try calling the backend
    var data = await Request(href_line);

    // Check if the data is null
    if (!data) {
      updateMessage('No content received');
    } else {
      handlePlotData(data);
      updateMessage();
    }
  } catch (error) {
    // some error occurred with the fetch
    displayError(
      'url',
      'JS Error',
      `Error - parse.js - plotGithubUrl(): ${error}`
    );
  }
}

/**
 * Plot the content of the GitHub URL.
 * @param {string} url - The URL to be plotted.
 */
export async function plotUploadedFile(
  cell: ICell,
  handlePlotData: (data: any) => void
): Promise<void> {
  // empty the content
  cell.state.graph_content = [];

  // Check the selected file and the processor URL
  const proc_url = cell.state.configurations.processor_url;
  if (!proc_url) {
    displayError(
      'url_content',
      'Server is unavailable at the moment. Please try again later.',
      'Error - parse.js - plotUploadedFile(): Processor URL not found'
    );
    return;
  } else if (!cell.state.uploaded_files[0]) {
    updateMessage('Please upload a file');
    return;
  }

  // Construct the file input
  updateMessage('Loading...');

  const fileContent = cell.state.uploaded_files[0];
  const url = `${proc_url}/parser/handle_uploaded_file`;

  // Create FormData object
  const formData = new FormData();
  formData.append('file', fileContent);

  // Log the FormData content to verify
  for (let [key, value] of formData.entries()) {
    console.log(`FormData key: ${key}, value:`, value);
  }

  try {
    // Send the POST request with the FormData
    const data: String = await PostRequest(url, formData);

    // Handle response
    console.log('Data:', data);

    // Check if the data is null
    if (!data) {
      updateMessage('No content received');
    } else {
      //handlePlotData(response);
      updateMessage();
    }
  } catch (error) {
    // some error occurred with the fetch
    displayError(
      'file',
      'JS Error',
      `Error - parse.js - plotUploadedFile(): ${error}`
    );
  }
}

// ###################### UTILITIES ######################
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
