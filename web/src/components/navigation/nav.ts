import m from 'mithril';

import { ICell } from '../../state';
import './nav.css';

const baseClass = 'nav';

export const Nav = (
  cell: ICell,
  attrName: string,
  content: any,
  side: string = 'left'
) => {
  // Constructs class names dynamically based on the 'side' argument
  const navClass = `${baseClass} ${baseClass}--${side}`;
  const navContentClass = `${baseClass}__content ${baseClass}__content--${side}`;

  // Combines the NavToggle and content into a single component
  return m(
    `.${navClass}`,
    m(`div.nav__wrapper nav__wrapper--${side}`, [
      NavToggle(cell, attrName, side),
      m(`.${navContentClass}`, content),
    ])
  );
};

export const NavToggle = (
  { state, update },
  attrName: string,
  side: string = 'left'
) => {
  // Toggles the state attribute and the open class for the nav
  const toggleNav = () => {
    const newValue = !state[attrName];
    update({ [attrName]: newValue });
  };

  // Constructs class names dynamically
  const toggleClass = `${baseClass}__toggle_btn ${baseClass}__toggle_btn--${side}`;
  const isOpen = state[attrName]
    ? `.${baseClass}__toggle_btn--open ${toggleClass}--open`
    : '';

  // Creates the toggle button with bars
  return m(`button.${toggleClass} ${isOpen}`, { onclick: toggleNav }, [
    state[attrName] ? (side == 'left' ? '<' : '>') : side == 'left' ? '>' : '<',
  ]);
};
