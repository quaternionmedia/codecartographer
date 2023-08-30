async function singlePlot() {
  // get the current layout and run
  const layoutElement = document.getElementById('layouts')
  const runElement = document.getElementById('run')
  const selectedLayout = layoutElement.value
  const selectedRun = runElement.value

  let debug = false
  let file = selectedRun
  if (selectedRun === 'debug') {
    debug = true
    file = ''
  }
  var href_line = `/plotter/plot?grid=false&debug=${debug}&file=${file}&layout=${selectedLayout}`

  try {
    const response = await fetch(href_line)
    console.log(`Received response: ${response.status}`)
    const responseData = await response.json()

    if (response.ok) {
      //console.log(`Received response: ${responseData.plot_html}`)
      const plotHTML = responseData.plot_html
      insertHTMLWithScripts('plot', plotHTML)
    }
  } catch (error) {
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

function gridPlot() {
  fetch('/plotter/plot?grid=true')
    .then(response => response.json())
    .then(data => {
      console.log(data)
      document.getElementById('plot').innerHTML = data
    })
    .catch(error => {
      console.error('Network error:', error)
    })
}
