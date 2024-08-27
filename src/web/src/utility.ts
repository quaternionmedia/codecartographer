export function getViewPortSize() {
  // Set a CSS variable on the root element with the current viewport
  document.documentElement.style.setProperty(
    '--vh',
    `${window.innerHeight * 0.01}px`
  );
  document.documentElement.style.setProperty(
    '--vw',
    `${window.innerWidth * 0.01}px`
  );
}

/** Log error and display message */
export function displayError(message: string = '') {
  console.log(message);
  const elemList = document.getElementsByClassName('loading');
  if (elemList && elemList.length > 0) {
    if (elemList[0]) {
      const messageComp = elemList[0] as HTMLElement;
      messageComp.innerHTML = 'Error from the server';
      messageComp.style.display = message === '' ? 'none' : 'inline';
    }
  }
}

/** Get the file content from the given file. */
export function readFile(file: File) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = function () {
      const file_raw = reader.result;
      resolve(file_raw);
    };

    reader.onerror = function (error) {
      reject(error);
    };

    reader.readAsText(file);
  });
}
