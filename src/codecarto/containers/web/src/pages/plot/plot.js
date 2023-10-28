// Get db_graph from url
function getQueryParam(key) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(key);
}
const dbGraphValue = getQueryParam('db_graph'); 
window.dbGraph = dbGraphValue === 'true'; 
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
 */
async function plot(all = false) {
  try {
    console.log('Plotting...')

    // Clear plot and show spinner
    document.getElementById('plot').innerHTML = ''
    document.getElementById('plot_loader').style.display = 'inline'

    // Fetch plot data
    const endpoint = generatePlotEndpoint(all)
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
function generatePlotEndpoint(all) {
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
    let endpoint = `/plotter/plot?url=${postData.url}&graph_data=${graphData}&db_graph=${window.dbGraph}&demo=${postData.demo}&demo_file=${postData.file}&layout=${postData.layout}`
    if (window.dbGraph) {
      console.log('Grabbing graph from database...')
    }

    // Return the endpoint
    return endpoint
  } catch (error) {
    console.error('Error - plot.js - generatePlotEndpoint():', error)
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
      // console.log(`Received response: ${responseData.message}`)
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

/**
 * Open the graph in Moe
 * @param {string} graphId - The ID of the graph to open.
 */
async function openInMoe(graphId) {
  try {
    let url
    // If fileUrl is defined, add it to the postData object
    if (window.fileUrl && window.fileUrl !== '') {
      url = window.fileUrl
    } else {
      // throw error for no url
      throw 'No url found'
    }

    // Construct the endpoint for the url_to_json API
    // TODO: This is temporary until we have a graph database, which will return a graph ID
    // let graphEndpoint = `/polygraph/url_to_json?file_url=${postData.url}`
    // const graphResponse = await fetch(graphEndpoint)
    // const graphResponseData = await graphResponse.json()

    // Construct Moe API endpoint
    const moe = 'http://localhost:5000/#!/graph'
    const moeURL = `${moe}?url=${url}`
    // TODO: This is temporary until we have a graph database, which will send a graph ID
    //const endpoint = `${moe}?graph=${graphResponseData}` // generateMoeEndpoint(all)

    // Open the new tab
    window.open(moeURL, '_blank')
    document.getElementById('plot_sent_to_moe').style.display = 'block'

    // // Fetch the data and wait for the response
    // const response = await fetch(endpoint)

    // // Check the response status
    // if (response.ok) {
    //   //Show sent message
    //   document.getElementById('plot_sent_to_moe').style.display = 'block'
    // } else {
    //   console.error(`Error with response status: ${response.status}`)
    //   return { status: 'error', message: 'Network error' }
    // }
  } catch (error) {
    document.getElementById('plot_sent_to_moe').style.display = 'block'
    document.getElementById('plot_sent_to_moe').innterHTML = 'Error opening Moe'
    console.error('Error - plot.js - openInMoe():', error)
    return { status: 'error', message: 'Network error' }
  }
}

// /**
//  * Generate the endpoint to call Moe.
//  * @param {boolean} all - If true, plot all layouts.
//  * @returns {string} The endpoint for calling Moe.
//  *
//  */
// async function generateMoeEndpoint(all) {
//   // TODO: Temporary solution is to send graph as json obj to Moe
//   // will eventually send just an id to graph from a database

//   try {
//     // Construct the endpoint for Moe
//     let endpoint = `/moe?graph=${responseData.results}`

//     // Return the endpoint
//     return endpoint
//   } catch (error) {
//     console.error('Error - plot.js - generateMoeEndpoint():', error)
//     document.getElementById('plot_loader').style.display = 'none'
//   }
// }
