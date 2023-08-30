async function plot(all = false) {
  // Clear plot
  document.getElementById('plot').innerHTML = ''
  // Show spinner
  document.getElementById('plot-loader').style.display = 'inline'

  // get the current layout and run
  const layoutElement = document.getElementById('layouts')
  const runElement = document.getElementById('files')
  const selectedLayout = layoutElement.value
  const selectedRun = runElement.value

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

  try {
    const response = await fetch(href_line)
    document.getElementById('plot-loader').style.display = 'none'
    console.log(`Received response: ${response.status}`)
    const responseData = await response.json()
    console.log(`Received response: ${responseData.plot_html}`)

    if (response.ok) {
      const plotHTML = responseData.plot_html
      let newPlotHTML = stylePlotHTML(plotHTML)

      console.log(`Received response: ${newPlotHTML}`)

      insertHTMLWithScripts('plot', newPlotHTML)
    }
  } catch (error) {
    document.getElementById('plot-loader').style.display = 'none'
    console.error('Network error:', error)
  }
  console.log('Started request…')
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
