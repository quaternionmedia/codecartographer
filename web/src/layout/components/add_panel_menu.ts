/**
 * AddPanelMenu
 *
 * Small dropdown opened by the header "+" button, the one way to add a
 * window. Lists every registered panel not in the layout, closed ones
 * included, plus layout save/reset actions. Closes on outside click, on
 * Escape, or after an action is taken.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { closeOnOutsideClickOrEscape } from './menu_dismissal';

interface Attrs {
  ctx: LayoutContext;
  x: number;
  y: number;
  onClose: () => void;
  /** The "+" button that opened the menu, which the focus goes back to. */
  opener: HTMLElement | null;
}

interface MenuState {
  /** Removes the outside-click and Escape listeners (`menu_dismissal.ts`). */
  disarm: () => void;
}

export const AddPanelMenu: m.Component<Attrs, MenuState> = {
  oncreate: (vnode) => {
    // Armed a tick later, so the click that opened the menu does not close it.
    vnode.state.disarm = closeOnOutsideClickOrEscape(
      document,
      vnode.attrs.onClose,
      (fn) => { setTimeout(fn, 0); },
    );
    // **THE FOCUS GOES INTO THE MENU.** It stayed on "+", so a keyboard
    // reader had to Tab through the header and the whole dock to reach the
    // list, which is drawn last in the page.
    (vnode.dom as HTMLElement).querySelector<HTMLElement>('button')?.focus();
  },

  // However the menu closed -- a click outside, Escape, one of its items, or
  // "+" again -- nothing it listened with outlives it.
  onremove: (vnode) => {
    vnode.state.disarm();
    // Still in the DOM here. Focus inside the menu goes back to "+"; focus a
    // click outside put elsewhere stays where the reader put it.
    if ((vnode.dom as HTMLElement).contains(document.activeElement)) vnode.attrs.opener?.focus();
  },

  view: ({ attrs }) => {
    const { ctx, x, y, onClose } = attrs;
    const addable = ctx.addablePanels();

    return m('div.gl-add-panel-menu', {
      style: { left: `${x}px`, top: `${y}px` },
      onclick: (e: Event) => e.stopPropagation(), // don't let our own clicks bubble to the outside-click closer
    }, [
      m('div.gl-add-panel-menu__section-title', 'Add window'),
      addable.length > 0
        ? addable.map((def) =>
            m('button.gl-add-panel-menu__item', {
              onclick: () => { ctx.openPanel(def.id); onClose(); },
            }, def.menuLabel),
          )
        : m('div.gl-add-panel-menu__empty', 'All panels open'),

      m('div.gl-add-panel-menu__divider'),
      m('div.gl-add-panel-menu__section-title', 'Layout'),
      m('button.gl-add-panel-menu__item', {
        onclick: () => { ctx.saveLayoutAsDefault(); onClose(); },
      }, 'Save current as default'),
      m('button.gl-add-panel-menu__item', {
        onclick: () => { ctx.resetLayoutToBuiltinDefault(); onClose(); },
      }, 'Reset to built-in default'),
    ]);
  },
};
