function attachCollapsibleListeners() {
  var coll = document.getElementsByClassName('collapsible')
  var i
  for (i = 0; i < coll.length; i++) {
    coll[i].addEventListener('click', function () {
      this.classList.toggle('active')
      var content = this.nextElementSibling
      if (content.style.display === 'block') {
        content.style.display = 'none'
      } else {
        content.style.display = 'block'
      }
    })
  }
}

function getPalette() {
  fetch('/palette/get_palette')
    .then(response => response.json())
    .then(data => {
      // Create a string variable with the content of the <div>
      let content = ''
      for (const [key, value] of Object.entries(data)) {
        // check if value is a dictionary
        if (typeof value === 'object') {
          content += `<button class="collapsible">${key}</button>`
          content += `<div class="content">`
          // if so, iterate through the dictionary
          for (const [k, v] of Object.entries(value)) {
            // Concatenating key-value pairs
            content += `${k}: ${v}<br>`
          }
          // remove last <br>
          content = content.slice(0, -4)
          content += `</div><br>`
        }
      }
      // Update the content of the <div>
      document.getElementById('pal_data').innerHTML = content
      attachCollapsibleListeners()
    })
    .catch(error => {
      document.getElementById('pal_data').innerHTML =
        'Error getting palette data'
      console.error('An error occurred in palette.html getPalette():', error)
    })
}
