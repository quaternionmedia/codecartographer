async function getPalette() {
  var href_line = `/palette/get_palette`
  try {
    const response = await fetch(href_line)
    const responseData = await response.json()

    if (response.ok) {
      if (responseData.status === 'error') {
        console.error(`Error with response data: ${responseData.message}`)
        document.getElementById('pal_data').innerHTML = responseData.message
      } else {
        console.log(`Received response: ${responseData.message}`)
        const data = responseData.results
        const content = handleContents(data)
        document.getElementById('pal_data').innerHTML = content
        attachCollapsibleListeners()
      }
    } else {
      document.getElementById('pal_data').innerHTML = 'Network error'
      console.error(`Error with response status: ${response.status}`)
    }
  } catch (error) {
    document.getElementById('pal_data').innerHTML = 'Network error'
    console.error('Error - palette.js - getPalette():', error)
  }
}

function handleContents(data) {
  let content = ''

  for (const [key, value] of Object.entries(data)) {
    if (typeof value === 'object') {
      // If the value is an object (directory)
      content += `<button class="collapsible">${key}</button>`
      content += `<div class="content">`
      for (const [k, v] of Object.entries(value)) {
        // Concatenating key-value pairs
        content += `${k}: ${v}<br>`
      }
      // remove last <br>
      content = content.slice(0, -4)
      content += `</div><br>`
    } else {
      // If the value is not an object (file)
      if (key === 'file') {
        content += `<div>${value}</div><br>`
      } else {
        content += `<div>${key}</div><br>`
      }
    }
  }

  return content
}
