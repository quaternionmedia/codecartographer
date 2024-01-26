/**
 * Gets all the current graphs in database.
 * @return {Promise} A promise that resolves to the database.
 */
async function getDatabase() {
    var href_line = `/graphs/list`
    try {
      const response = await fetch(href_line)
      const responseData = await response.json()
  
      if (response.ok) {
        if (responseData.status !== 200) {
          displayError(
            'db_data',
            responseData.message,
            `Error with response data: ${responseData.detail}`
          )
        }
        if (responseData.status === 'error') {
          console.error(`Error with response data: ${responseData.message}`)
          document.getElementById('db_data').innerHTML = responseData.message
        } else {
          console.log(`Received response: ${responseData.message}`)
          const data = responseData.results
          const content = handleContents(data)
          document.getElementById('db_data').innerHTML = content
          attachCollapsibleListeners()
        }
      } else {
        document.getElementById('db_data').innerHTML = 'Network error'
        console.error(`Error with response status: ${response.status}`)
      }
    } catch (error) {
      document.getElementById('db_data').innerHTML = 'Network error'
      console.error('Error - db.js - getDatabase():', error)
    }
}


/**
 * Handle the response data.
 * @param {string} data - The data to be displayed.
 * @returns {string} The HTML content.
 */
function handleContents(data) { 
  //loop list of graph names in database
  let html = ''
  if (typeof data !== 'object') {
    html += `<span>Invalid format: ${obj}</span>`
  } else if (data.length === 0) {
    html += `<span>No graphs in database</span>`
  } else {
    // Iterate through the array
    const arrayLength = data.length;
    html = `<ul>`
    for (var i = 0; i < arrayLength; i++) {
      // set plot link
      let plot_link = ``
      if (!(data[i].includes('.py'))) {
        // if not a python file, then it is a repo
        plot_link = `/plotter/?is_repo=true&db_graph=true&file_url=https://github.com/${data[i]}/`
      } else {
        // if python file
        plot_link = `/plotter/?db_graph=true&file_url=${data[i]}`
      }
      html += `<li><strong>${data[i]}</strong>`
      html += `${'&nbsp;'.repeat(2)} - ${'&nbsp;'.repeat(2)}`
      html += `<a class="plotLink" href="${plot_link}" target="_blank">PLOT</a>`
      html += `</li>`
    }
    html += `</ul>`
  }
  // Return the html
  return html
}