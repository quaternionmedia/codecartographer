export function getViewPortSize() {
  // Set a CSS variable on the root element with the current viewport
  document.documentElement.style.setProperty(
    "--vh",
    `${window.innerHeight * 0.01}px`
  );
  document.documentElement.style.setProperty(
    "--vw",
    `${window.innerWidth * 0.01}px`
  );
}

/** Log error and display message */
export function displayError(message: string = "") {
  console.log(message);
  const elemList = document.getElementsByClassName("loading");
  if (elemList && elemList.length > 0) {
    if (elemList[0]) {
      const messageComp = elemList[0] as HTMLElement;
      messageComp.innerHTML = message;
      messageComp.style.display = message === "" ? "none" : "inline";
    }
  }
}
export function readFile(file: File) {
  console.log("File being passed to readAsText:", file); // Log to inspect file object

  return new Promise((resolve, reject) => {
    const reader = new FileReader();

    reader.onload = (event) => {
      if (event.target) {
        console.log("File read successfully:", event.target.result); // Log the result
        resolve(event.target.result);
      }
    };

    reader.onerror = (error) => {
      console.error("Error reading file:", error); // Log the error for better insight
      reject(error);
    };

    reader.readAsText(file); // This is where it reads the file's content as text
  });
}
