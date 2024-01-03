// Get db_graph from url
function getQueryParam(key) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(key);
}
const dbGraphValue = getQueryParam('db_graph'); 
window.dbGraph = dbGraphValue === 'true';  

console.log('dbGraph:', window.dbGraph)
if (window.dbGraph == true) {

  document.getElementById('gv_single').style.display = 'inline'
  document.getElementById('gv_grid').style.display = 'inline'
}

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
    document.getElementById('plot_moe').style.display = 'inline'

    // check if the file ends with .py
    if (!fileName.endsWith('.py')) {
      document.getElementById('single').disabled = true
      document.getElementById('grid').disabled = true
      document.getElementById('plot_moe').disabled = true
      document.getElementById('plot').innerHTML = '<br>Invalid file type'
    }
  } else {
    document.getElementById('plot_moe').style.display = 'none'
  }
} else {
  document.getElementById('plot_moe').style.display = 'none'
  console.error('fileUrlDiv not found')
}

/**
 * Plot the data from the GitHub API or from one of the demo files.
 * @param {boolean} all - If true, plot all layouts.
 * @param {boolean} gv - If true, plot using gv.
 * @param {boolean} all_gv - If true, plot all gv types.
 */
async function plot(all = false, gv = false, all_gv = false) {
  try {
    // Clear the existing content
    document.getElementById('plot_loader').style.display = 'inline'
    document.getElementById('plot').innerHTML = ''

    console.log('Plotting...')

    // Fetch plot data
    const endpoint = generatePlotEndpoint(all, gv, all_gv)
    const responseData = await fetchPlotData(endpoint)
    handlePlotResponse(responseData)
  } catch (error) {
    console.error('Error - plot.js - plot():', error)
  } finally { 
    document.getElementById('plot_loader').style.display = 'none'
  }
}

/**
 * Generate the endpoint for the plot API.
 * @param {boolean} all - If true, plot all layouts.
 * @param {boolean} gv - If true, plot using gv.
 * @param {boolean} all_gv - If true, plot all gv types.
 * @returns {string} The endpoint for the plot API.
 */
function generatePlotEndpoint(all, gv, all_gv) {
  try {
    // Get the selected layout
    const layoutElement = document.getElementById('layouts')
    const selectedLayout = all ? 'all' : layoutElement.value

    // Create a data object to send in the POST request
    let postData = {
      layout: selectedLayout,
      file: '',
      url: '',
      demo: false,
    }
    let graphData = {
      name: '',
    }

    if (window.fileUrl && window.fileUrl !== '' && !window.dbGraph) {
      // If fileUrl is defined, add it to the postData object
      postData.url = window.fileUrl
    } else if (window.dbGraph) {
      // Otherwise, set the url to the graph name (file name)
      postData.url = window.fileUrl
    } else {
      // Otherwise, get the file selector value
      const runElement = document.getElementById('files')
      const selectedRun = runElement.value
      postData.demo = selectedRun === 'demo'
      if (!postData.demo) {
        postData.file = selectedRun
      }
    }

    // Construct the endpoint
    let type = all_gv ? 'all' : 'd3'
    let endpoint = `/plotter/plot?url=${postData.url}&graph_data=${graphData}&db_graph=${window.dbGraph}&demo=${postData.demo}&demo_file=${postData.file}&layout=${postData.layout}&gv=${gv}&type=${type}`
    if (window.dbGraph) {
      console.log('Grabbing graph from database...')
    }

    // Return the endpoint
    return endpoint
  } catch (error) {
    console.error('Error - plot.js - generatePlotEndpoint():', error)
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
      // console.log(`Received response: ${responseData.message}`)
      // Style the plot HTML and insert it into the page
      if (responseData.results.includes('!function(mpld3){')) {
        const plotHTML = responseData.results
        let newPlotHTML = stylePlotHTML(plotHTML)
        insertHTMLWithScripts('plot', newPlotHTML)
      } else { 
        handleNotebook(responseData)
      }
    }
  } catch (error) {
    console.error('Error - plot.js - handlePlotResponse():', error)
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
    
    // .mpld3-baseaxes > .mpld3-text {
    //   color: white;
    //   fill: rgb(255,255,255)
    // }
    
    // font size
    newPlotHTML = newPlotHTML.replace(/"fontsize": 12.0/g, '"fontsize": 30.0')
    // return new HTML
    return newPlotHTML
  } catch (error) {
    console.error('Error - plot.js - stylePlotHTML():', error)
  }
}

/**
 * Open the graph in Moe
 * @param {string} graphId - The ID of the graph to open.
 */
async function openInMoe(graphId) {
  try {
    document.getElementById('plot_moe').disabled = true
    document.getElementById('plot_loader').style.display = 'inline'
    let url
    // If fileUrl is defined, add it to the postData object
    if (window.fileUrl && window.fileUrl !== '') {
      url = window.fileUrl
    } else {
      // throw error for no url
      throw 'No url found'
    }

    // TODO: This is temporary until we have a graph database, which will return a graph ID
    // Construct Moe API endpoint
    const moe = 'http://localhost:5000/#!/graph'
    const moeURL = `${moe}?url=${url}`

    // Open the new tab
    window.open(moeURL, '_blank')
  } catch (error) {
    document.getElementById('plot_sent_to_moe').innterHTML = 'Error opening Moe'
    console.error('Error - plot.js - openInMoe():', error)
    return { status: 'error', message: 'Network error' }
  } finally {
    document.getElementById('plot_moe').disabled = false
    document.getElementById('plot_loader').style.display = 'none' 
  }
}

/**
 * Handle ipynb output.
 * @param {string} type - The type of output to get.
 */
async function handleNotebook(responseData) {
  try { 
    document.getElementById('plot_loader').style.display = 'inline'
    document.getElementById('plot').innerHTML = ''
    console.log('Getting notebook output...')

    // Get the plot div
    const plotElement = document.getElementById('plot')

    // Check if the response data contains the expected output
    if (responseData && responseData.results.length > 0) {
      responseData.results.forEach(output => {
        console.log(output)
        if (output['text/html']) {
            // Create an iframe for each output
            let iframe = document.createElement('iframe');
            iframe.className = 'nbFrame';
            iframe.srcdoc = output['text/html'];
            iframe.style.width = '800px';
            iframe.style.height = '475px';
            iframe.style.border = 'none';
            plotElement.appendChild(iframe);
        }
      });
    } else {
      plotElement.innerHTML = 'No notebook found'
    }
  } catch (error) {
    console.error('Error - plot.js - handleNotebook():', error) 
  } finally { 
    document.getElementById('plot_loader').style.display = 'none'
  }
}