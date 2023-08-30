// THIS IS JUST A TEMP DEV SOLUTION TO RELOAD
// THE PAGE WHEN THE CSS/HTML FILE CHANGES
// IT WILL BE REMOVED WHEN DEVELOPMENT IS DONE

// Object to store initial content of each file
const monitoredFiles = {}

// Function to fetch a file and compare its content
const checkForChange = async filePath => {
  try {
    const response = await fetch(filePath)
    const newContent = await response.text()

    if (!monitoredFiles[filePath]) {
      monitoredFiles[filePath] = newContent
    } else if (monitoredFiles[filePath] !== newContent) {
      location.reload()
    }
  } catch (error) {
    console.error(`Error fetching file: ${filePath}`, error)
  }
}

// Function to monitor multiple files
const monitorFiles = filePaths => {
  filePaths.forEach(filePath => {
    setInterval(() => checkForChange(filePath), 2000)
  })
}

// Usage
const filesToMonitor = [
  '/pages/home/home.css',
  '/pages/home/home.html',
  '/pages/home/home.js',
  '/pages/palette/palette.css',
  '/pages/palette/palette.html',
  '/pages/palette/palette.js',
  '/pages/parse/parse.css',
  '/pages/parse/parse.html',
  '/pages/parse/parse.js',
  '/pages/plot/plot.css',
  '/pages/plot/plot.html',
  '/pages/plot/plot.js',
  '/pages/base.css',
  '/pages/base.html',
]

monitorFiles(filesToMonitor)
