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

interface Attrs {
  ctx: LayoutContext;
  x: number;
  y: number;
  onClose: () => void;
}

interface State {
  /** Removes what `oncreate` put on `document`. */
  teardown?: () => void;
}

export const AddPanelMenu: m.Component<Attrs, State> = {
  oncreate: (vnode) => {
    const { onClose } = vnode.attrs;
    const onKeydown = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onClose();
    };
    // Defer listener registration one tick so the click that opened the
    // menu doesn't immediately close it via the same event.
    const timer = setTimeout(() => {
      document.addEventListener('click', onClose);
      document.addEventListener('keydown', onKeydown);
    }, 0);
    // Removed when the menu goes, however it goes. Choosing a window stops
    // its click short of `document`, so a listener that waits to fire once
    // stays armed after the menu is gone, and closes the next menu the +
    // opens on the very click that opened it.
    vnode.state.teardown = () => {
      clearTimeout(timer);
      document.removeEventListener('click', onClose);
      document.removeEventListener('keydown', onKeydown);
    };
  },

  onremove: (vnode) => {
    vnode.state.teardown?.();
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
