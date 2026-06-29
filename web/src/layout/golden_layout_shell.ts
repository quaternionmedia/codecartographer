/**
 * GoldenLayoutShell
 *
 * Top-level Mithril component that bootstraps a Golden Layout instance and
 * distributes the application UI across dockable panels.
 *
 * Panels registered:
 *   • 'graph'         — D3 / vis-network visualisation canvas
 *   • 'control-panel' — Source loader + graph settings drawer
 *   • 'file-tree'     — Repository / uploaded-file browser
 *
 * Activate via URL flag: append  ?layout=golden  to any app URL.
 * The classic CodeCarto layout remains the default.
 */

import m from 'mithril';
import { GoldenLayout } from 'golden-layout';

import type { ICell } from '../state/cell_state';
import { LayoutContext } from './layout_context';
import { DEFAULT_LAYOUT_CONFIG } from './default_layout';
import { createGraphPanel } from './panels/graph_panel';
import { createControlPanelWrapper } from './panels/control_panel_wrapper';
import { createFileTreePanel } from './panels/file_tree_panel';

import { HelpModal, HelpModalComponent } from '../components/codecarto/help/help_modal';
import { ToastContainer } from '../components/codecarto/help/toast';

// GL CSS — order matters: base → dark theme → terminal overrides
import 'golden-layout/dist/css/goldenlayout-base.css';
import 'golden-layout/dist/css/themes/goldenlayout-dark-theme.css';
import './golden_layout_theme.css';
import '../components/codecarto/help/help_modal.css';

/**
 * Factory function that returns a closure Mithril component, following the
 * same pattern as the existing `CodeCarto` component.
 *
 * @param getCell  Accessor for the current Meiosis cell (state atom).
 */
export const GoldenLayoutShell = (getCell: () => ICell): m.Component => {
  const initialCell = getCell();
  const ctx = new LayoutContext(initialCell, getCell);

  let glInstance: GoldenLayout | null = null;

  /** Mount GL panels after the host element exists in the DOM. */
  function initGoldenLayout(hostElement: HTMLElement): void {
    glInstance = new GoldenLayout(hostElement);

    glInstance.registerComponentFactoryFunction('graph', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:hidden;';
      m.mount(container.element, createGraphPanel(ctx));
    });

    glInstance.registerComponentFactoryFunction('control-panel', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:auto;';
      m.mount(container.element, createControlPanelWrapper(ctx));
    });

    glInstance.registerComponentFactoryFunction('file-tree', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:auto;';
      m.mount(container.element, createFileTreePanel(ctx));
    });

    glInstance.loadLayout(DEFAULT_LAYOUT_CONFIG);
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
    },

    view: () => {
      return m('div.gl-shell', [
        // ── App header ────────────────────────────────────────────────────
        m('header.gl-app-header', [
          m('h1.gl-app-header__title', [
            m('span.gl-app-header__icon', '◈'),
            'Code Cartographer',
          ]),
          m('p.gl-app-header__subtitle', 'Golden Layout'),
          m('span.gl-app-header__spacer'),
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
        }),

        // ── Overlays (modals / toasts — rendered above GL chrome) ─────────
        m('div.gl-overlays', [
          m(HelpModalComponent),
          m(ToastContainer),
        ]),
      ]);
    },
  };
};
