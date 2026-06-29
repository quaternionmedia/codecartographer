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
import { DEFAULT_LAYOUT_CONFIG } from './default_layout';
import { createGraphPanel } from './panels/graph_panel';
import { createFileTreePanel } from './panels/file_tree_panel';
import { createSourcePanel } from './panels/source_panel';
import { createGraphSettingsPanel } from './panels/graph_settings_panel';

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
  const ctx = new LayoutContext(initialCell, getCell);

  let glInstance: GoldenLayout | null = null;

  const registerDockPanelLifecycle = (container: any, panelId: 'graph' | 'file-tree' | 'source-panel' | 'graph-settings-panel'): void => {
    container.on('close', () => ctx.hideDockPanel(panelId));
    container.on('show', () => ctx.showDockPanel(panelId));
  };

  /** Mount GL panels after the host element exists in the DOM. */
  function initGoldenLayout(hostElement: HTMLElement): void {
    glInstance = new GoldenLayout(hostElement);
    ctx.attachLayoutManager(glInstance);

    glInstance.registerComponentFactoryFunction('graph', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:hidden;';
      registerDockPanelLifecycle(container, 'graph');
      m.mount(container.element, createGraphPanel(ctx));
    });

    glInstance.registerComponentFactoryFunction('source-panel', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:auto;';
      registerDockPanelLifecycle(container, 'source-panel');
      m.mount(container.element, createSourcePanel(ctx));
    });

    glInstance.registerComponentFactoryFunction('graph-settings-panel', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:auto;';
      registerDockPanelLifecycle(container, 'graph-settings-panel');
      m.mount(container.element, createGraphSettingsPanel(ctx));
    });

    glInstance.registerComponentFactoryFunction('file-tree', (container) => {
      container.element.style.cssText = 'width:100%;height:100%;overflow:auto;';
      registerDockPanelLifecycle(container, 'file-tree');
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
      ctx.attachLayoutManager(null);
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
          ctx.hiddenDockPanels.length > 0
            ? m('div.gl-app-header__restore',
                ctx.hiddenDockPanels.map((panelId) =>
                  m('button.gl-app-header__restore-btn', {
                    onclick: () => ctx.restoreDockPanel(panelId),
                    title: `Restore ${panelId}`,
                  }, panelId === 'source-panel'
                    ? 'Restore Source'
                    : panelId === 'graph-settings-panel'
                      ? 'Restore Settings'
                      : panelId === 'graph'
                        ? 'Restore Graph'
                        : 'Restore Files'),
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
