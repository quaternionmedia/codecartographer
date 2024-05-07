import m from 'mithril'
import './nav.css'

// Defines the base nav class
const baseClass = 'nav'

// Nav component
export const Nav = (cell, attrName, side, content) => {
  // Constructs class names dynamically based on the 'side' argument
  const navClass = `${baseClass} .${baseClass}_${side}`
  const navContentClass = `${baseClass}__content .${baseClass}_${side}__content`

  // Combines the NavToggle and content into a single component
  return m(`.${navClass}`, [
    NavToggle(cell, attrName, side),
    m(`.${navContentClass}`, content),
  ])
}

// NavToggle component
export const NavToggle = ({ state, update }, attrName, side) => {
  // Toggles the state attribute and the open class for the nav
  const toggleNav = () => {
    const newValue = !state[attrName]
    update({ [attrName]: newValue })
  }

  // Constructs class names dynamically
  const toggleClass = `${baseClass}__toggle`
  const toggleSideClass = `.${baseClass}_${side}__toggle`
  const isOpen = state[attrName]
    ? `.${toggleClass}--open .${toggleSideClass}--open`
    : ''

  // Creates the toggle button with bars
  return m(
    `button.${toggleClass} ${toggleSideClass} ${isOpen}`,
    { onclick: toggleNav },
    [
      m(`.${toggleClass}__bar ${toggleSideClass}__bar__1`),
      m(`.${toggleClass}__bar ${toggleSideClass}__bar__2`),
      m(`.${toggleClass}__bar ${toggleSideClass}__bar__3`),
    ]
  )
}

document.addEventListener('DOMContentLoaded', () => {
  // Logic for hiding the nav toggle on mobile devices
  // in landscape mode after 3 seconds of inactivity
  const navToggles = document.querySelectorAll('.nav__toggle')
  if (!navToggles) return // Ensures the navToggle exists

  let timeoutId

  function hideNavToggle() {
    navToggles.forEach(navToggle => {
      // Check if the toggle is not open
      if (!navToggle.classList.contains('nav__toggle--open')) {
        navToggle.classList.remove('nav__toggle--visible')
        navToggle.classList.add('nav__toggle--hidden')
      }
    })
  }

  function showNavToggle() {
    clearTimeout(timeoutId)
    navToggles.forEach(navToggle => {
      navToggle.classList.remove('nav__toggle--hidden')
      navToggle.classList.add('nav__toggle--visible')
    })
    delayHideNavToggle() // Reset the timer to hide the toggle again
  }

  // Delays hiding the nav toggle
  function delayHideNavToggle() {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(hideNavToggle, 1500) // Delay of 2 seconds
  }

  // Check if the device is in landscape mode
  function checkOrientation() {
    if (window.innerWidth > window.innerHeight) {
      delayHideNavToggle()
    } else {
      clearTimeout(timeoutId)
      showNavToggle()
    }
  }

  // Event listener for touch events
  document.addEventListener('touchstart', showNavToggle)

  // Event listener for orientation changes
  window.addEventListener('orientationchange', checkOrientation)

  // Initial check on load
  checkOrientation()
})
