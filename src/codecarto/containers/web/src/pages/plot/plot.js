// Set up fileUrl if it is defined
const fileUrlDiv = document.getElementById('fileUrl')
if (fileUrlDiv) {
  window.fileUrl = fileUrlDiv.getAttribute('data-url')
  if (window.fileUrl && window.fileUrl !== '') {
    document.getElementById('files').style.display = 'none'
    const fileName = window.fileUrl.substring(
      window.fileUrl.lastIndexOf('/') + 1
    )
    document.getElementById(
      'fileUrl'
    ).innerHTML = `File:&nbsp;&nbsp;${fileName}`
    document.getElementById('fileUrl').style.display = 'inline'

    // check if the file ends with .py
    if (!fileName.endsWith('.py') && !fileName.endsWith('.json')) {
      document.getElementById('single').disabled = true
      document.getElementById('grid').disabled = true
      document.getElementById('plot').innerHTML = '<br>Invalid file type'
    } else if (fileName.endsWith('.json')) {
      document.getElementById('parse_type').style.display = 'inline'
    }
  }
} else {
  console.error('fileUrlDiv not found')
}

/**
 * Plot the data from the GitHub API or from one of the demo files.
 * @param {boolean} all - If true, plot all layouts.
 */
async function plot(all = false) {
  try {
    // Clear plot and show spinner
    document.getElementById('plot').innerHTML = ''
    document.getElementById('plot_loader').style.display = 'inline'

    // Fetch plot data
    const endpoint = generateEndpoint(all)
    const responseData = await fetchPlotData(endpoint)
    handlePlotResponse(responseData)

    // Hide spinner
    document.getElementById('plot_loader').style.display = 'none'
  } catch (error) {
    console.error('Error - plot.js - plot():', error)
    document.getElementById('plot_loader').style.display = 'none'
  }
}

/**
 * Generate the endpoint for the plot API.
 * @param {boolean} all - If true, plot all layouts.
 * @returns {string} The endpoint for the plot API.
 *
 */
function generateEndpoint(all) {
  try {
    // Get the selected layout
    const layoutElement = document.getElementById('layouts')
    const selectedLayout = all ? 'all' : layoutElement.value
    const parseType = document.getElementById('parse_type').value

    // Create a data object to send in the POST request
    let postData = {
      layout: selectedLayout,
      file: '',
      url: '',
      parse_type: parseType, // if parse_type hidden, won't apply to the plot anyway
      debug: false,
    }

    // If fileUrl is defined, add it to the postData object
    if (window.fileUrl && window.fileUrl !== '') {
      postData.url = window.fileUrl
    } else {
      // Otherwise, get the file selector value
      const runElement = document.getElementById('files')
      const selectedRun = runElement.value
      postData.debug = selectedRun === 'debug'
      if (!postData.debug) {
        postData.file = selectedRun
      }
    }

    // Construct the endpoint
    let endpoint = `/plotter/plot?file=${postData.file}&url=${postData.url}&layout=${postData.layout}&debug=${postData.debug}&parse_type=${postData.parse_type}`

    // Return the endpoint
    return endpoint
  } catch (error) {
    console.error('Error - plot.js - generateEndpoint():', error)
    document.getElementById('plot_loader').style.display = 'none'
  }
}

/**
 * Fetch the plot data from the plot API.
 * @param {string} endpoint - The endpoint for the plot API.
 * @returns {object} The response data from the plot API.
 */
async function fetchPlotData(endpoint) {
  try {
    // Fetch the data and wait for the response
    let response = await fetch(endpoint)

    // Check the response status
    if (response.ok) {
      return await response.json()
    } else {
      console.error(`Error with response status: ${response.status}`)
      return { status: 'error', message: 'Network error' }
    }
  } catch (error) {
    console.error('Error - plot.js - fetchPlotData():', error)
    document.getElementById('plot_loader').style.display = 'none'
    return { status: 'error', message: 'Network error' }
  }
}

/**
 * Handle the response from the plot API.
 * @param {object} responseData - The response data from the plot API.
 */
function handlePlotResponse(responseData) {
  try {
    // Check the inner response status (derived from the web container)
    if (responseData.status === 'error') {
      console.error(`Error with response data: ${responseData.message}`)
      document.getElementById('plot').innerHTML = responseData.message
    } else {
      console.log(`Received response: ${responseData.message}`)
      // Style the plot HTML and insert it into the page
      const plotHTML = responseData.results
      let newPlotHTML = stylePlotHTML(plotHTML)
      insertHTMLWithScripts('plot', newPlotHTML)
    }
  } catch (error) {
    console.error('Error - plot.js - handlePlotResponse():', error)
    document.getElementById('plot_loader').style.display = 'none'
  }
}

/**
 * Insert HTML into a div and execute any scripts.
 * @param {string} divId - The ID of the div to insert the HTML into.
 * @param {string} html - The HTML to insert.
 */
function insertHTMLWithScripts(divId, html) {
  try {
    // Clear the existing content
    const container = document.getElementById(divId)
    container.innerHTML = ''

    // Insert the new content
    const parser = new DOMParser()
    const doc = parser.parseFromString(html, 'text/html')
    container.appendChild(doc.body.firstChild)

    // Extract and append scripts
    const scripts = doc.querySelectorAll('script')
    scripts.forEach(oldScript => {
      const newScript = document.createElement('script')
      Array.from(oldScript.attributes).forEach(attr =>
        newScript.setAttribute(attr.name, attr.value)
      )
      newScript.appendChild(document.createTextNode(oldScript.innerHTML))
      container.appendChild(newScript)
    })
  } catch (error) {
    console.error('Error - plot.js - insertHTMLWithScripts():', error)
    document.getElementById('plot_loader').style.display = 'none'
  }
}

/**
 * Style the plot HTML.
 * @param {string} plotHTML - The HTML to style.
 * @returns {string} The styled HTML.
 */
function stylePlotHTML(plotHTML) {
  try {
    // background color
    let newPlotHTML = plotHTML.replace(
      /"axesbg": "#FFFFFF"/g,
      '"axesbg": "#e8dbad"'
    )
    // font size
    newPlotHTML = newPlotHTML.replace(/"fontsize": 12.0/g, '"fontsize": 30.0')
    // return new HTML
    return newPlotHTML
  } catch (error) {
    console.error('Error - plot.js - stylePlotHTML():', error)
    document.getElementById('plot_loader').style.display = 'none'
  }
}
