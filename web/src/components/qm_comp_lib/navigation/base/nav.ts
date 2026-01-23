import m from 'mithril';
import { animations, animationController } from '../../../../core/animations';
import './nav.css';

const baseClass = 'nav';

export enum NavSide {
  LEFT = 'left',
  RIGHT = 'right',
}

interface NavAttrs {
  side: NavSide;
  isOpen: boolean;
  content: m.Children;
  toggle: () => void;
}

/** Navigation panel component with slide animations */
export const NavComponent: m.Component<NavAttrs> = {
  oncreate(vnode) {
    const wrapper = vnode.dom.querySelector(`.${baseClass}__wrapper`) as HTMLElement;
    if (wrapper) {
      // Set initial state without animation
      wrapper.style.transform = vnode.attrs.isOpen 
        ? 'translateX(0%)' 
        : `translateX(${vnode.attrs.side === 'left' ? '-100%' : '100%'})`;
    }
  },

  onupdate(vnode) {
    const wrapper = vnode.dom.querySelector(`.${baseClass}__wrapper`) as HTMLElement;
    if (wrapper) {
      const animId = `nav-${vnode.attrs.side}`;
      animationController.play(
        animId,
        animations.slideNav(wrapper, vnode.attrs.isOpen, vnode.attrs.side)
      );
    }
  },

  view(vnode) {
    const { side, isOpen, content, toggle } = vnode.attrs;
    
    const navClass = `${baseClass} ${baseClass}--${side}`;
    const wrapperClass = `${baseClass}__wrapper`;
    const navWrapperClass = `${wrapperClass} ${wrapperClass}--${side}`;
    const contentClass = `${baseClass}__content`;
    const navContentClass = `${contentClass} ${contentClass}--${side}`;

    return m(
      `.${navClass}`,
      m(`div.${navWrapperClass}`, [
        NavToggle(isOpen, side, toggle),
        m(`.${navContentClass}`, content),
      ])
    );
  }
};

/** Legacy function-based Nav for backward compatibility */
export const Nav = (
  side: NavSide = NavSide.LEFT,
  attrValue: boolean,
  content: m.Children,
  toggle: () => void
) => {
  return m(NavComponent, { side, isOpen: attrValue, content, toggle });
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

  return m(`button.${toggleClass}.${isOpen}`, { 
    onclick: (e: MouseEvent) => {
      // Add button press animation
      animations.buttonPress(e.currentTarget as Element);
      toggle();
    }
  }, [icon]);
};
