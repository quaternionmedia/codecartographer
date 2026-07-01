/**
 * AddPanelMenu
 *
 * Small dropdown opened by the header "+" button or a right-click on the
 * dock area. Lists registered panels not currently in the layout (add a
 * window) plus layout save/reset actions. Closes on outside click, on
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

export const AddPanelMenu: m.Component<Attrs> = {
  oncreate: ({ attrs }) => {
    // Defer listener registration one tick so the click that opened the
    // menu doesn't immediately close it via the same event.
    setTimeout(() => {
      document.addEventListener('click', attrs.onClose, { once: true });
      document.addEventListener('keydown', onKeydown);
    }, 0);

    function onKeydown(e: KeyboardEvent): void {
      if (e.key === 'Escape') {
        document.removeEventListener('keydown', onKeydown);
        attrs.onClose();
      }
    }
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
              onclick: () => { ctx.restoreDockPanel(def.id); onClose(); },
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
