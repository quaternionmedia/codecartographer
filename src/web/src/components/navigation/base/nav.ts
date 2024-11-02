import m from 'mithril';

import './nav.css';

const baseClass = 'nav';

export const Nav = (
  side: string = 'left',
  attrValue: boolean,
  content: any,
  toggle: () => void
) => {
  // Constructs class names dynamically based on the 'side' argument
  const navClass = `${baseClass} ${baseClass}--${side}`;
  const navContentClass = `${baseClass}__content ${baseClass}__content--${side}`;

  // Combines the NavToggle and content into a single component
  return m(
    `.${navClass}`,
    m(`div.nav__wrapper nav__wrapper--${side}`, [
      NavToggle(attrValue, side, toggle),
      m(`.${navContentClass}`, content),
    ])
  );
};

export const NavToggle = (
  attrValue: boolean,
  side: string = 'left',
  toggle: () => void
) => {
  // Constructs class names dynamically
  const toggleClass = `${baseClass}__toggle_btn ${baseClass}__toggle_btn--${side}`;
  const isOpen = attrValue
    ? `.${baseClass}__toggle_btn--open ${toggleClass}--open`
    : '';

  // Creates the toggle button with bars
  return m(`button.${toggleClass} ${isOpen}`, { onclick: toggle }, [
    attrValue ? (side == 'left' ? '<' : '>') : side == 'left' ? '>' : '<',
  ]);
};
