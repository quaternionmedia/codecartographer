async function getGraphDesc() {
  var href_line = `/polygraph/get_graph_desc`
  try {
    const response = await fetch(href_line)
    console.log(`Received response status: ${response.status}`)
    const responseData = await response.json()
    console.log(`Received response data: ${responseData}`)

    if (response.ok) {
      if (responseData.error) {
        console.log(`Received response error: ERROR WITH RESPONSE DATA`)
        document.getElementById('graph_desc').innerHTML =
          'Could not display graph description'
      } else {
        console.log(`Getting graph_desc`)
        const graph_desc = responseData.graph_desc
        console.log(`Checking graph_desc is object: ${graph_desc}`)
        console.log(`Parsing graph_desc to HTML`)
        let graphDescHTML =
          '<div id="graph_desc">The graph data (JSON obj) needs to structured as the following:'
        graphDescHTML += graphDescToHTML(graph_desc)
        graphDescHTML += '</div>'
        document.getElementById('graph_desc').innerHTML = graphDescHTML
      }
    }
  } catch (error) {
    document.getElementById('graph_desc').innerHTML = 'Network error'
    console.error('Network error:', error)
  }
  console.log('Started request…')
}

function graphDescToHTML(obj) {
  if (typeof obj !== 'object') {
    return `<span>${obj}</span>`
  }

  let html = `<ul>`
  for (const [key, value] of Object.entries(obj)) {
    html += `<li><strong>${key}</strong>: ${graphDescToHTML(value)}</li>`
  }
  html += `</ul>`
  return html
}
