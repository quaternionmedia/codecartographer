async function plot(all = false) {
  // Clear plot
  document.getElementById('plot').innerHTML = ''
  // Show spinner
  document.getElementById('plot_loader').style.display = 'inline'

  // get the current layout and run
  const layoutElement = document.getElementById('layouts')
  const runElement = document.getElementById('files')
  const selectedLayout = layoutElement.value
  const selectedRun = runElement.value

  // get the variables for the request
  let debug = false
  let file = selectedRun
  let layout = selectedLayout
  if (selectedRun === 'debug') {
    debug = true
    file = ''
  }
  if (all == true) {
    layout = 'all'
  } else {
    layout = selectedLayout
  }
  var href_line = `/plotter/plot?grid=false&debug=${debug}&file=${file}&layout=${layout}`

  // make the request
  try {
    document.getElementById('plot_loader').style.display = 'none'
    const response = await fetch(href_line)
    const responseData = await response.json()

    if (response.ok) {
      if (responseData.status === 'error') {
        console.error(`Error with response data: ${responseData.message}`)
        document.getElementById('plot').innerHTML = responseData.message
      } else {
        console.log(`Received response: ${responseData.message}`)
        const plotHTML = responseData.results
        let newPlotHTML = stylePlotHTML(plotHTML)

        insertHTMLWithScripts('plot', newPlotHTML)
      }
    } else {
      document.getElementById('plot').innerHTML = 'Network error'
      console.error(`Error with response status: ${response.status}`)
    }
  } catch (error) {
    document.getElementById('plot_loader').style.display = 'none'
    document.getElementById('plot').innerHTML = 'Network error'
    console.error('Error - plot.js - plot():', error)
  }
}

function insertHTMLWithScripts(containerId, html) {
  const container = document.getElementById(containerId)
  container.innerHTML = '' // Clear the existing content

  // Insert the HTML part
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
}

function stylePlotHTML(plotHTML) {
  let newPlotHTML = plotHTML.replace(
    /"axesbg": "#FFFFFF"/g,
    '"axesbg": "#e8dbad"'
  )
  newPlotHTML = newPlotHTML.replace(/"fontsize": 12.0/g, '"fontsize": 30.0')
  return newPlotHTML
}
