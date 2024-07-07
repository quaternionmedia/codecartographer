import m from 'mithril';

import './nav.css';
import { ICell } from '../../state';

const baseClass = 'nav';

export const Nav = (cell: ICell, attrName: string, content: any) => {
  // Constructs class names dynamically based on the 'side' argument
  const navClass = `${baseClass}`;
  const navContentClass = `${baseClass}__content`;

  // Combines the NavToggle and content into a single component
  return m(
    `.${navClass}`,
    m('div.nav__wrapper', [
      NavToggle(cell, attrName),
      m(`.${navContentClass}`, content),
    ])
  );
};

export const NavToggle = ({ state, update }, attrName: string) => {
  // Toggles the state attribute and the open class for the nav
  const toggleNav = () => {
    const newValue = !state[attrName];
    update({ [attrName]: newValue });
  };

  // Constructs class names dynamically
  const toggleClass = `${baseClass}__toggle_btn`;
  const isOpen = state[attrName] ? `.${toggleClass}--open` : '';

  // Creates the toggle button with bars
  return m(`button.${toggleClass} ${isOpen}`, { onclick: toggleNav }, [
    state.showContentNav ? '<' : '>',
  ]);
};
