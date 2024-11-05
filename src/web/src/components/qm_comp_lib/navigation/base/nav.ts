import m from 'mithril';
import './nav.css';

const baseClass = 'nav';

export enum NavSide {
  LEFT = 'left',
  RIGHT = 'right',
}

export const Nav = (
  side: NavSide = NavSide.LEFT,
  attrValue: boolean,
  content: any,
  toggle: () => void
) => {
  const navClass = `${baseClass} ${baseClass}--${side}`;

  const wrapperClass = `${baseClass}__wrapper`;
  const navWrapperClass = `${wrapperClass} ${wrapperClass}--${side}`;

  const contentClass = `${baseClass}__content`;
  const navContentClass = `${contentClass} ${contentClass}--${side}`;

  return m(
    `.${navClass}`,
    m(`div.${navWrapperClass}`, [
      NavToggle(attrValue, side, toggle),
      m(`.${navContentClass}`, content),
    ])
  );
};

export const NavToggle = (
  attrValue: boolean,
  side: NavSide = NavSide.LEFT,
  toggle: () => void
) => {
  const toggleBtnClass = `${baseClass}__toggle_btn`;
  const toggleBtnSideClass = `${toggleBtnClass}--${side}`;
  const toggleClass = `${toggleBtnClass} ${toggleBtnSideClass}`;

  const openClass = `${toggleBtnClass}--open ${toggleBtnSideClass}--open`;
  const isOpen = attrValue ? openClass : '';

  const icon = attrValue
    ? side == NavSide.LEFT
      ? '<'
      : '>'
    : side == NavSide.LEFT
    ? '>'
    : '<';

  return m(`button.${toggleClass}.${isOpen}`, { onclick: toggle }, [icon]);
};
