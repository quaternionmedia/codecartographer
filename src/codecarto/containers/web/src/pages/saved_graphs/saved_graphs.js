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
    html = `<a class="deleteLink" href="#" onclick="delete_graphs()">DELETE ALL</a>`;
    html += `<ul>`
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
      // set del link
      html += `<li><strong>${data[i]}</strong>`
      html += `${'&nbsp;'.repeat(2)} - ${'&nbsp;'.repeat(2)}`
      html += `<a class="plotLink" href="${plot_link}" target="_blank">PLOT</a> ${'&nbsp;'.repeat(2)}`
      html += `<a class="deleteLink" href="#" onclick="delete_graph('${data[i]}')">DELETE</a>`;
      html += `</li>`
    }
    html += `</ul>`
  }
  // Return the html
  return html
}

/**
 * Delete the graph from the database.
 * @param {string} name - The name of the graph to be deleted.
 * @returns {string} The HTML content.
 */
async function delete_graph(name) {
  let del_link = `/graphs/delete?name=${name}`
  try {
    const response = await fetch(del_link);
    const responseData = await response.json();

    if (response.ok) {
      if (responseData.status !== 200) {
        displayError(
          'db_data',
          responseData.message,
          `Error with response data: ${responseData.detail}`
        );
      }
      if (responseData.status === 'error') {
        console.error(`Error with response data: ${responseData.message}`);
        document.getElementById('db_data').innerHTML = responseData.message;
      } else {
        console.log(`Received Response: ${responseData.message}`);
        console.log(`Response Results: ${responseData.results}`);
        
        // Reload the page to update the graph list
        location.reload();
      }
    } else {
      document.getElementById('db_data').innerHTML = 'Network error';
      console.error(`Error with response status: ${response.status}`);
    }
  } catch (error) {
    document.getElementById('db_data').innerHTML = 'Network error';
    console.error('Error - db.js - getDatabase():', error);
  }
}

/**
 * Delete all the graphs from the database.
 * @returns {string} The HTML content.
 */
async function delete_graphs() {
  let del_link = `/graphs/delete_all`
  try {
    const response = await fetch(del_link);
    const responseData = await response.json();

    if (response.ok) {
      if (responseData.status !== 200) {
        displayError(
          'db_data',
          responseData.message,
          `Error with response data: ${responseData.detail}`
        );
      }
      if (responseData.status === 'error') {
        console.error(`Error with response data: ${responseData.message}`);
        document.getElementById('db_data').innerHTML = responseData.message;
      } else {
        console.log(`Received Response: ${responseData.message}`);
        console.log(`Response Results: ${responseData.results}`);
        
        // Reload the page to update the graph list
        location.reload();
      }
    } else {
      document.getElementById('db_data').innerHTML = 'Network error';
      console.error(`Error with response status: ${response.status}`);
    }
  } catch (error) {
    document.getElementById('db_data').innerHTML = 'Network error';
    console.error('Error - db.js - getDatabase():', error);
  }
}