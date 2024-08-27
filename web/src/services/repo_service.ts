import { ICell } from '../state';
import { GetRequest, PostJsonRequest } from './request_handler';

class FileData {
  name: string;
  raw: string;
}

class FolderData {
  name: string;
  files: FileData[];
}

class SourceData {
  owner: string; // quaternionmedia
  repo: string; // moe
  folders: FolderData[];
}

/**
 * Get the directories and files from a given GitHub URL.
 * @param {Object} cell - The cell to be updated.
 * @param {Function} updateGithubData - The function to update the GitHub data.
 */
export async function handleGithubURL(
  cell: ICell,
  updateGithubData: (data: any, url: string) => void
): Promise<void> {
  try {
    cell.state.repo_data = [];
    cell.state.directory_content = [];
    cell.state.graph_content = [];
    cell.state.plot_repo_url = '';

    // Check the URL to be processed
    let url = cell.state.repo_url;
    if (!url || url === '') {
      throw new Error('Please enter a URL');
    }
    if (url[url.length - 1] !== '/') url += '/';

    // Encode the url and create the href line
    const procUrl = initRequest(cell);
    const encodedGithubUrl = encodeURIComponent(url);
    const href = `${procUrl}/parser/handle_github_url?github_url=${encodedGithubUrl}`;

    // Try calling the backend
    const repoData = await GetRequest(href);
    if (!repoData) {
      throw new Error('No content received');
    }

    // Update the cell state with the data
    console.log(`sucess getting repo data ${repoData}`);
    updateGithubData(repoData, url);
    updateMessage();
  } catch (error) {
    // Some error occurred with the fetch
    updateMessage(error.message);
    displayError(
      'url_content',
      'JS Error',
      `Error - parse.js - handleGithubURL(): ${error}`
    );
  }
}

/**
 * Send SourceData to the processor to plot the data.
 * @param {ICell} cell
 * @param {SourceData} source
 * @param {Function} handlePlotData
 */
export async function plotSourceData(
  cell: ICell,
  source: SourceData,
  handlePlotData: (data: any) => void
): Promise<void> {
  try {
    cell.state.graph_content = [];

    // Construct the request
    const procUrl = initRequest(cell);
    const baseApi = `${procUrl}/plotter/plot`;
    const formData = new FormData();
    formData.append('file', JSON.stringify(source));

    // Log the FormData content to verify
    for (let [key, value] of formData.entries()) {
      console.log(`FormData key: ${key}, value:`, value);
    }

    // Send the POST request with the FormData
    const plotData: string = await PostJsonRequest(baseApi, formData);
    if (!plotData) {
      throw new Error('No content received');
    }

    // Update the cell state with the data
    console.log('plotData:', plotData);
    handlePlotData(plotData);
    updateMessage();
  } catch (error) {
    // Some error occurred with the fetch
    updateMessage(error.message);
    displayError(
      'source',
      'JS Error',
      `Error - repo_service.js - plotSourceData(): ${error}`
    );
  }
}

/**
 * Plot the content of the GitHub URL.
 * @param {Object} cell - The cell to be updated.
 * @param {Function} handlePlotData - The function to handle the plot data.
 */
export async function plotGithubUrl(
  cell: ICell,
  handlePlotData: (data: any) => void
): Promise<void> {
  try {
    cell.state.graph_content = [];

    // Check the URL to be processed
    let url = cell.state.selected_url_file;
    if (!url || url === '') {
      updateMessage('Please enter a URL');
      return;
    }
    if (url[url.length - 1] !== '/') url += '/';

    // Construct request data
    const procUrl = initRequest(cell);
    const encodedGithubUrl = encodeURIComponent(url);
    const href =
      `${procUrl}/plotter/plot?` +
      `url=${encodedGithubUrl}&` +
      `layout=${'Spectral'}&` +
      `is_repo=${true}&` +
      `gv=${true}`;

    // Send the GET request
    const data = await GetRequest(href);
    console.log('plotGithubUrl data:', data);

    // Check if the data is null
    if (!data) {
      throw new Error('No content received');
    }

    // Update the cell state with the data
    handlePlotData(data);
    updateMessage();
  } catch (error) {
    // Some error occurred with the fetch
    updateMessage(error.message);
    displayError(
      'url',
      'JS Error',
      `Error - repo_service.js - plotGithubUrl(): ${error}`
    );
  }
}

/**
 * Plot the content of the selected file.
 * @param {Object} cell - The cell to be updated.
 * @param {Function} handlePlotData - The function to handle the plot data.
 */
export async function plotUploadedFile(
  cell: ICell,
  handlePlotData: (data: any) => void
): Promise<void> {
  try {
    cell.state.graph_content = [];
    cell.state.selected_uploaded_file = undefined;

    // // Construct request data
    // const procUrl = initRequest(cell);
    // const urlParser = `${procUrl}/parser/handle_uploaded_file`;
    // const file = cell.state.uploaded_files[0];
    // const formData = new FormData();
    // formData.append('file', file);

    // // Log the FormData content to verify
    // for (let [key, value] of formData.entries()) {
    //   console.log(`FormData key: ${key}, value:`, value);
    // }

    // // Send the POST request with the FormData
    // console.log('Send the POST request');
    // const fileGraph: string = await PostRequest(urlParser, formData);
    // console.log('plotUploadedFile parse response: ', fileGraph);

    // Construct request data
    const procUrl = initRequest(cell);
    const urlParserRaw = `${procUrl}/parser/handle_raw_data?layout=Spectral`;
    const file = cell.state.uploaded_files[0];
    const fileRaw = await getRawFileData(file);
    // const formDataRaw = new FormData();
    // formDataRaw.append('raw_data', JSON.stringify(fileRaw));
    // formDataRaw.append('name', JSON.stringify(file.name));

    // // Log the FormData content to verify
    // for (let [key, value] of formDataRaw.entries()) {
    //   console.log(`FormData key: ${key}, value:`, value);
    // }

    const body = {
      raw_data: fileRaw,
      name: file.name,
    };

    console.log('Send the raw POST request');
    const fileGraph: string = await PostJsonRequest(urlParserRaw, body);
    console.log('plotUploadedFile raw fileGraph response: ', fileGraph);

    handlePlotData(fileGraph);
    updateMessage();
    // // Check if the data is null
    // if (
    //   !fileGraph ||
    //   fileGraph === '' ||
    //   fileGraph === 'null' ||
    //   fileGraph === 'undefined' ||
    //   fileGraph.length === 0
    // ) {
    //   throw new Error('No content received');
    // }

    // // Handle response
    // const plotData: Object = await PostJsonRequest(
    //   `${procUrl}/plotter/plot_nb`,
    //   {
    //     name: file.name,
    //     graph: fileGraph,
    //   }
    // );
    // if (!plotData) {
    //   throw new Error('No graph content received');
    // }
    // console.log('plotUploadedFile plot response: ', plotData);

    // handlePlotData(plotData);
    // updateMessage();
  } catch (error) {
    // Some error occurred with the fetch
    updateMessage(error.message);
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

/**
 * Get the file content from the uploaded file.
 * @param {File} file - The cell to be updated.
 * @returns {string} - The raw file content.
 */
function getRawFileData(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = function () {
      const file_raw = reader.result;
      resolve(file_raw);
    };

    reader.onerror = function (error) {
      reject(error);
    };

    reader.readAsText(file);
  });
}

/**
 * Get the Processor URL from the configurations.
 * @param {ICell} cell - The cell to be updated.
 * @returns {string} - The processor URL.
 * @throws {Error} - If the processor URL is not available.
 */
function getProcessorURL(cell: ICell): string {
  const proc_url = cell.state.configurations.processor_url;
  if (!proc_url) {
    throw new Error(
      'Server is unavailable at the moment. Please try again later.'
    );
  }
  return proc_url;
}

/**
 * Initialize app and the processor URL.
 * @param {ICell} cell - The cell to be updated.
 * @returns {string} - The processor URL.
 * @throws {Error} - If the processor URL is not available.
 */
function initRequest(cell: ICell): string {
  const proc_url = getProcessorURL(cell);
  updateMessage('Loading...');
  return proc_url;
}
