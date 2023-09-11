function displayError(elementId, message, consoleMessage) {
  document.getElementById(elementId).innerHTML = message
  if (consoleMessage) {
    console.error(consoleMessage, message)
  }
}

function convertListToButtons(data) {
  // Convert <ul><li> structures to collapsible button structures
  let result = ''
  const parser = new DOMParser()
  const dom = parser.parseFromString(data, 'text/html')
  const items = dom.querySelectorAll('ul > li')

  items.forEach(item => {
    const key = item.querySelector('strong')
      ? item.querySelector('strong').textContent
      : item.textContent
    const nestedUl = item.querySelector('ul')

    if (nestedUl) {
      let nestedContent = ''
      nestedUl.querySelectorAll('li').forEach(li => {
        nestedContent += `${li.innerHTML}`
      })
      result += `<button class="collapsible">${key}</button>`
      result += `<div class="content">${nestedContent}</div>`
    } else {
      result += item.outerHTML
    }
  })

  return result
}

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
