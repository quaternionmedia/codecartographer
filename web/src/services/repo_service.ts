import m from 'mithril';

import { ICell } from '../state';
import { Request } from './request_handler';
import { parseContents } from '../components/directory/directory';

/**
 * Get the directories and files from a given GitHub URL.
 * @param {Object} cell - The cell to be updated.
 */
export async function handleGithubURL(cell: ICell): Promise<void> {
  // empty the content
  const directory = getHTMLElement('directory');
  if (directory) directory.innerHTML = '';
  cell.state.repo_data = [];
  cell.state.directory_content = [];

  // get the url input
  const urlInput = getHTMLElement('url_input') as HTMLInputElement;
  if (urlInput) {
    const url = urlInput.value;

    // return if the url is empty
    if (!url || url === '') {
      updateMessage('Please enter a URL');
      return;
    }
    updateMessage('Loading...');

    // check for the trailing slash
    let repoUrl = url;
    if (repoUrl && repoUrl[repoUrl.length - 1] !== '/') {
      repoUrl += '/';
    }
    cell.state.repo_url = repoUrl;

    // encode the url and create the href line
    const encodedGithubUrl = encodeURIComponent(repoUrl);
    const proc_url = cell.state.configurations.processor_url;
    const href_line = `${proc_url}/parser/handle_github_url?github_url=${encodedGithubUrl}`;

    // try calling the backend
    try {
      var data = (await Request(href_line)) as IRepoData;

      parseGithubResults(cell, data, repoUrl);

      const showFiles = getHTMLElement('nav__toggle');
      if (showFiles) showFiles.classList.add('nav__toggle--open');

      updateMessage();
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

// ###################### DIRECTORY FUNCTIONS ######################
/**
 * Attach collapsible listeners to the collapsible buttons.
 * @param {Object} cell - The cell to be updated.
 * @param {Object} data - The GitHub data to be converted.
 * @param {string} repoUrl - The URL of the GitHub repository.
 */
function parseGithubResults(
  cell: ICell,
  data: IRepoData,
  repoUrl: string
): void {
  // Check if the data is null
  if (!data) {
    const content = getHTMLElement('directory');
    if (content) content.innerHTML = 'No content received';
  }

  // Extract the owner, repo, and contents from the data
  const repoOwner = data.package_owner;
  const repoName = data.package_name;
  const plot_link = `/plotter/?is_repo=true&file_url=${repoUrl}`;
  const repoData = parseRepoData(data.contents, repoName);

  // Create the content for the cell
  let plot_whole_link = m('a', {
    href: plot_link,
    class: 'whole_plot_link',
    target: '_blank',
    innerText: 'Plot Whole Repo',
  });

  let content = [
    plot_whole_link,
    m('div', { class: 'root' }, parseContents(data.contents, 'root')),
  ];

  // Update the cell with the new content
  cell.update({
    repo_owner: repoOwner,
    repo_name: repoName,
    repo_data: repoData as unknown as m.Vnode<{}, {}>[],
    directory_content: content,
    showContentNav: true,
  });
}

/** Parse the data from the GitHub repository.
 * @param {Object} data - The data to be parsed.
 * @param {string} repoName - The name of the repository.
 * @returns {(IFolder | IFiles)[]} - The parsed data.
 */
function parseRepoData(data: Object, repoName: string): (IFolder | IFiles)[] {
  // data is a dictionary of files and or folders
  // folders can have files and or folders as well
  // {folder_name: {}, files: []}

  function translateData(data: Object, parent = 'root') {
    const result: (IFolder | IFiles)[] = [];
    for (const key in data) {
      if (key == 'files') {
        // create an array for the file objects
        const files = data[key];
        const file_list: IFiles = {
          type: 'files',
          name: `${parent}_files`, // the parent folder name
          data: [],
        };
        // add each file to the array
        for (const item of files) {
          const file: IFile = {
            type: 'file',
            name: item.name, // the file name
            data: item.download_url,
          };
          file_list.data.push(file);
        }
        // return the file list
        result.push(file_list);
      } else {
        // create a folder object
        const folder_content = data[key];
        const folder: IFolder = {
          type: 'folder',
          name: key,
          data: translateData(folder_content, key),
        };
        result.push(folder);
      }
    }
    return result;
  }

  return translateData(data, repoName);
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

/** Get HTML element by class name. Returns first in list of all.
 * @param {string} classname - The class name of the element.
 * @returns {Element | null} - The HTML element.
 */
function getHTMLElement(classname: string): Element | null {
  const elemList = document.getElementsByClassName(classname);
  if (elemList && elemList.length > 0) return elemList[0];
  return null;
}

// ###################### DIRECTORY INTERFACES ######################
export interface IRepoData {
  package_owner: string;
  package_name: string;
  contents: object;
}

export interface IContent {
  type: string;
  name: string;
  data: Object | Array<Object>;
}

export interface IFolder extends IContent {
  data: (IFolder | IFiles)[]; // list of files or folders
}

export interface IFiles extends IContent {
  data: IFile[]; // list of files
}

export interface IFile extends IContent {
  data: string; // url to raw file
}
