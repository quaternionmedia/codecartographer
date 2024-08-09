import m from 'mithril';
import { ICell } from '../state';
import { Request } from './request_handler';

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
  updateMessage('Feature is still a work in progress');
  return;
  // empty the content
  cell.state.graph_content = [];

  // Check the selected URL and the processor URL
  let file_content = cell.state.uploaded_files[0];
  const proc_url = cell.state.configurations.processor_url;
  if (!proc_url) {
    displayError(
      'url_content',
      'Server is unavailable at the moment. Please try again later.',
      'Error - parse.js - plotUploadedFile(): Processor URL not found'
    );
    return;
  }

  // return if the url is empty
  if (!file_content) {
    updateMessage('Please upload a file');
    return;
  }
  console.log(file_content);
  updateMessage('Loading...');

  // encode the url and create the href line
  // const encodedGithubUrl = encodeURIComponent(url);
  const href_line =
    `${proc_url}/plotter/plot?` +
    `is_repo=${true}&` +
    `graph_data=${{ name: '' }}&` +
    `db_graph=${false}&` +
    `demo=${false}&` +
    `demo_file=${''}&` +
    `layout=${'Spectral'}&` +
    `gv=${true}&` +
    `type=${'d3'}`;

  // Usage example
  const fileInput = { files: file_content };
  const fileContent = fileInput.files ? fileInput.files[0] : null;
  const procUrl = 'your_processor_url_here';

  sendFile(fileContent, procUrl);

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

async function sendFile(fileContent: File, procUrl: string) {
  if (!fileContent) {
    updateMessage('Please upload a file');
    return;
  }
  console.log(fileContent);
  updateMessage('Loading...');

  // Create FormData object
  const formData = new FormData();
  formData.append('file', fileContent);
  formData.append('is_repo', 'true');
  formData.append('graph_data', JSON.stringify({ name: '' }));
  formData.append('db_graph', 'false');
  formData.append('demo', 'false');
  formData.append('demo_file', '');
  formData.append('layout', 'Spectral');
  formData.append('gv', 'true');
  formData.append('type', 'd3');

  try {
    // Send the POST request with the FormData
    const response = await m.request({
      method: 'POST',
      url: `${procUrl}/plotter/plot`,
      body: formData,
      serialize: (data) => data, // Ensure Mithril doesn't serialize FormData
    });

    // Handle response
    console.log(response);
    updateMessage('File uploaded successfully');
  } catch (error) {
    console.error(error);
    updateMessage('Failed to upload file');
  }
}
