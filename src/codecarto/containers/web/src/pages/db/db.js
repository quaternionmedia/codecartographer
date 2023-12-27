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
  //loop list of graph names in data 
  let content = ''
  var arrayLength = data.length;
  for (var i = 0; i < arrayLength; i++) {
      console.log(data[i]);
      content += `${data[i]}`;
  }
}