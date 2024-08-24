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
