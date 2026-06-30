/**
 * GoldenLayoutShell
 *
 * Top-level Mithril component that bootstraps a Golden Layout instance and
 * distributes the application UI across dockable panels.
 *
 * Panels registered:
 *   • 'graph'         — D3 / vis-network visualisation canvas
 *   • 'file-tree'     — Repository / uploaded-file browser
 *
 * Golden Layout is now the primary shell.
 */

import m from 'mithril';
import { GoldenLayout } from 'golden-layout';

import type { ICell } from '../state/cell_state';
import { LayoutContext } from './layout_context';
import { PanelRegistry, DockPanelId } from './panel_registry';
import { AddPanelMenu } from './components/add_panel_menu';

import { HelpModal, HelpModalComponent } from '../components/codecarto/help/help_modal';
import { ToastContainer } from '../components/codecarto/help/toast';

// GL CSS — order matters: base → dark theme → terminal overrides
import 'golden-layout/dist/css/goldenlayout-base.css';
import 'golden-layout/dist/css/themes/goldenlayout-dark-theme.css';
import './golden_layout_theme.css';
import '../components/codecarto/help/help_modal.css';

/**
 * Factory function that returns the Mithril component for the Golden Layout
 * shell.
 *
 * @param getCell  Accessor for the current Meiosis cell (state atom).
 */
export const GoldenLayoutShell = (getCell: () => ICell): m.Component => {
  const initialCell = getCell();
  const ctx = new LayoutContext(initialCell);

  let glInstance: GoldenLayout | null = null;
  let menuOpen = false;
  let menuPos = { x: 0, y: 0 };

  const closeMenu = (): void => { if (menuOpen) { menuOpen = false; m.redraw(); } };

  const registerDockPanelLifecycle = (container: any, panelId: DockPanelId): void => {
    // GL2 destroys the container on close — 'beforeComponentRelease' is the correct event.
    // 'close' is not emitted by ComponentContainer in GL 2.x.
    container.on('beforeComponentRelease', () => ctx.hideDockPanel(panelId));
    container.on('show', () => ctx.showDockPanel(panelId));
  };

  /** Mount GL panels after the host element exists in the DOM. */
  function initGoldenLayout(hostElement: HTMLElement): void {
    glInstance = new GoldenLayout(hostElement);
    ctx.attachLayoutManager(glInstance);

    for (const def of PanelRegistry.all()) {
      glInstance.registerComponentFactoryFunction(def.id, (container) => {
        container.element.style.cssText = `width:100%;height:100%;overflow:${def.overflow};`;
        registerDockPanelLifecycle(container, def.id);
        def.mount(ctx, container.element);
      });
    }

    // Known limitation: GL 2.x pop-out opens a new window but Mithril component
    // factories are bound to the original window — components never mount in pop-outs.
    // popInOnClose: true (default_layout.ts) auto-returns panels on pop-out close.
    glInstance.loadLayout(ctx.loadInitialLayoutConfig());
  }

  return {
    oncreate: async () => {
      // Apply default theme
      const theme = ctx.panelState.currentTheme;
      document.documentElement.setAttribute('data-theme', theme === 'terminal' ? '' : theme);

      // Initialise languages + cache (non-blocking)
      try { await ctx.actions.plot.initializeLanguages(); m.redraw(); } catch { /* non-fatal */ }
      await ctx.refreshCache();

      HelpModal.maybeShowFirstTime();
    },

    ondestroy: () => {
      glInstance?.destroy();
      glInstance = null;
      ctx.attachLayoutManager(null);
    },

    view: () => {
      return m('div.gl-shell', [
        // ── App header ────────────────────────────────────────────────────
        m('header.gl-app-header', [
          m('button.gl-app-header__add-btn', {
            onclick: (e: MouseEvent) => {
              const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
              menuPos = { x: rect.left, y: rect.bottom };
              menuOpen = !menuOpen;
            },
            title: 'Add a window',
          }, '+'),
          m('h1.gl-app-header__title', [
            m('span.gl-app-header__icon', '◈'),
            'Code Cartographer',
          ]),
          m('span.gl-app-header__spacer'),
          ctx.hiddenDockPanels.length > 0
            ? m('div.gl-app-header__restore',
                ctx.hiddenDockPanels.map((panelId) =>
                  m('button.gl-app-header__restore-btn', {
                    onclick: () => ctx.restoreDockPanel(panelId),
                    title: `Restore ${panelId}`,
                  }, `Restore ${PanelRegistry.get(panelId)?.menuLabel ?? panelId}`),
                ),
              )
            : null,
          m('button.gl-app-header__help-btn', {
            onclick: () => HelpModal.open(),
            title: 'Help & walkthrough',
          }, '?'),
        ]),

        // ── GL host ───────────────────────────────────────────────────────
        // We use oncreate/onremove on the inner div so that GL is created
        // exactly once when the element first enters the DOM.
        m('div.gl-shell__body', {
          oncreate: (vnode: m.VnodeDOM) => {
            initGoldenLayout(vnode.dom as HTMLElement);
          },
          onremove: () => {
            glInstance?.destroy();
            glInstance = null;
          },
          // Right-click on the tab/dock area also opens the add-window menu.
          oncontextmenu: (e: MouseEvent) => {
            e.preventDefault();
            menuPos = { x: e.clientX, y: e.clientY };
            menuOpen = true;
            m.redraw();
          },
        }),

        menuOpen
          ? m(AddPanelMenu, {
              ctx,
              x: menuPos.x,
              y: menuPos.y,
              onClose: closeMenu,
            })
          : null,

        // ── Overlays (modals / toasts — rendered above GL chrome) ─────────
        m('div.gl-overlays', [
          m(HelpModalComponent),
          m(ToastContainer),
        ]),
      ]);
    },
  };
};
