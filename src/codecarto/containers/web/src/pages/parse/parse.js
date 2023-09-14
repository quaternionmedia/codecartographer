/**
 * Attach event listeners to the collapsible buttons.
 */
async function getGraphDesc() {
  try {
    // Get the graph description from the backend
    const href_line = `/polygraph/get_graph_desc`
    const response = await fetch(href_line)
    const responseData = await response.json()

    if (response.ok) {
      // Check if the response is an error from the backend
      if (responseData.status === 'error') {
        displayError(
          'graph_desc',
          responseData.message,
          `Error with response data: `
        )
      } else {
        // Convert the data to html and display it
        const graph_desc = responseData.results
        let graphDescHTML =
          '<div id="graph_desc">The graph data (JSON obj) needs to structured as the following:'
        graphDescHTML += graphDescToHTML(graph_desc)
        graphDescHTML += '</div>'
        document.getElementById('graph_desc').innerHTML = graphDescHTML
      }
    } else {
      displayError(
        'graph_desc',
        'API Error',
        `Error with response status: ${response.status}`
      )
    }
  } catch (error) {
    displayError(
      'graph_desc',
      'JS Error',
      `Error - parse.js - getGraphDesc(): ${error}`
    )
  }
}

/**
 * Convert the given graph description object to HTML.
 * @param {Object} obj - The graph description object.
 * @return {string} - The formatted HTML content.
 */
function graphDescToHTML(obj) {
  // Check if the object is null
  let html = ''
  if (typeof obj !== 'object') {
    html += `<span>Invalid format: ${obj}</span>`
  } else {
    // Iterate through the object
    html = `<ul>`
    for (const [key, value] of Object.entries(obj)) {
      html += `<li><strong>${key}</strong>: ${graphDescToHTML(value)}</li>`
    }
    html += `</ul>`
  }
  // Return the html
  return html
}

/**
 * Get the directories and files from the given GitHub URL.
 */
async function handleGithubURL() {
  // Check if the url input is blank or not
  if (document.getElementById('githubUrl').value === '') {
    document.getElementById('url_content').innerHTML = 'Please enter a URL'
    return
  } else {
    try {
      // Get the url from the input, and encode it
      document.getElementById('url_content').innerHTML = ''
      document.getElementById('github_loader').style.display = 'inline'
      let githubUrl = document.getElementById('githubUrl').value
      if (githubUrl[githubUrl.length - 1] !== '/') {
        githubUrl += '/'
      }
      const encodedGithubUrl = encodeURIComponent(githubUrl)
      const href_line = `/parser/handle_github_url?github_url=${encodedGithubUrl}`
      const response = await fetch(href_line)
      const responseData = await response.json()

      if (response.ok) {
        // Check if the response is an error from the backend
        if (responseData.status === 'error') {
          displayError(
            'url_content',
            responseData.message,
            `Error with response data: ${responseData.detail}`
          )
        } else {
          // Refactor the data and display it
          const data = responseData.results
          const refactoredData = refactorGitHubData(data)
          document.getElementById('url_content').innerHTML = refactoredData
          attachCollapsibleListeners()
        }
      } else {
        displayError(
          'url_content',
          'API Error',
          `Error with response status: ${response.status}`
        )
      }
    } catch (error) {
      displayError(
        'url_content',
        'JS Error',
        `Error - parse.js - handleGithubURL(): ${error}`
      )
    } finally {
      document.getElementById('github_loader').style.display = 'none'
    }
  }
}

/**
 * Attach collapsible listeners to the collapsible buttons.
 * @param {Object} data - The GitHub data to be converted.
 * @return {string} - The formatted HTML content.
 */
function refactorGitHubData(data) {
  // Check if the data is null
  let html = ''
  if (!data) {
    html += `<span>There is no content to display</span>`
  } else {
    // Extract the owner, repo, and contents from the data
    const dataOwner = data.package_owner
    const dataRepo = data.package_name
    const dataContents = data.contents
    const dataDict = { contents: dataContents }
    const contentHtml = handleGitHubData(dataDict)
    // Add package owner and name to the html
    html += `<pre>`
    html += `Package Owner: ${dataOwner}<br>`
    html += `Package Name: ${dataRepo}`
    html += `</pre>`
    html += `${contentHtml}`
  }
  // Return the html
  return html
}

/**
 * Create a collapsible button structure from the given GitHub data.
 * @param {Object} data - The GitHub data to be converted.
 * @param {boolean} nested - Whether the data is nested or not.
 * @return {string} - The formatted HTML content.
 */
function handleGitHubData(data, nested = false) {
  // Iterate through the data
  let content = ''
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === 'object') {
      // If the key is "files", it's a list of filenames
      if (key === 'files') {
        link_style = 'style="color: #e1c48f; text-decoration: none;"'
        for (const file of value) {
          let json_link = `/polygraph/raw_to_json?file_url=${file['download_url']}`
          let plot_link = `/plotter/?file_url=${file['download_url']}`
          content += `<div>`
          content += `<a class="gitLink" href="${file['html_url']}" target="_blank">${file['name']}</a>`
          content += `  `
          content += `<a class="jsonLink" href="${json_link}" target="_blank">JSON</a>`
          content += `  `
          content += `<a class="plotLink" href="${plot_link}" target="_blank">PLOT</a>`
          content += `</div>`
        }
      } else {
        // Else, it's a directory
        content += `<button class="collapsible">${key}</button>`
        content += `<div class="content">`
        content += handleGitHubData(value, nested) // Recursive call for nested directories
        content += `</div>`
      }
    }
  }
  // Return the content
  return content
}
