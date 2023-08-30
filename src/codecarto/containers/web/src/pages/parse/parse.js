function getGraphDesc() {
  fetch('/parser/get_graph_desc')
    .then(response => response.json())
    .then(data => {
      // Create the content of the <div>
      var content = '<pre>' + data['graph_desc'] + '</pre>'
      // Update the content of the <div>
      document.getElementById('graph_desc').innerHTML = content
    })
    .catch(error => {
      document.getElementById('graph_desc').innerHTML =
        'Error getting graph description'
      console.error('An error occurred:', error)
    })
}
