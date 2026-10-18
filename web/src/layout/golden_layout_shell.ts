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
import type { ComponentContainer } from 'golden-layout';

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

  const registerDockPanelLifecycle = (container: ComponentContainer, panelId: DockPanelId): void => {
    // GL2 destroys the container on close — 'beforeComponentRelease' is the correct event.
    // 'close' is not emitted by ComponentContainer in GL 2.x.
    container.on('beforeComponentRelease', () => {
      // **A CLOSED PANEL IS TAKEN DOWN, NOT ONLY TAKEN AWAY.** Golden Layout
      // removes the container's element and forgets it, but the Mithril root
      // mounted in that element is Mithril's to forget, and nothing told it.
      // Every redraw went on drawing the closed panel into an element nobody
      // could see -- a closed Actions panel kept up with each upload -- and a
      // Graph panel closed and opened again left two roots drawing the one
      // canvas vnode the state holds, which Mithril reported as a failed
      // `removeChild` on the next plot. Unmounting also runs the panel's
      // `onremove`, so whatever a panel sets up it can take down with it.
      // alfred's workspace, which copied this shell, unmounts here too.
      m.mount(container.element, null);
      ctx.hideDockPanel(panelId);
    });
    container.on('show', () => ctx.showDockPanel(panelId));
  };

  /** Mount GL panels after the host element exists in the DOM. */
  function initGoldenLayout(hostElement: HTMLElement): void {
    glInstance = new GoldenLayout(hostElement);
    // **THE DOCK FOLLOWS ITS ELEMENT, AND AT ONCE.** Golden Layout follows its
    // container's size by itself only when the container is <body>, and this
    // one is the shell's body element: the dock kept the size it was built
    // at, so a taller window left a band of nothing under it and a narrower
    // one cut the panels off at the edge. Followed, it waits 100ms after the
    // last resize by default, and longer while resizes keep coming -- for
    // that long every panel is where it was, and a press lands on whatever
    // used to be under it. alfred's workspace found that in its browser suite
    // and follows at once; so does this. The cost is a layout per frame while
    // a window is dragged, which Golden Layout's sizing is cheap enough for.
    glInstance.resizeWithContainerAutomatically = true;
    glInstance.resizeDebounceInterval = 0;
    glInstance.resizeDebounceExtendedWhenPossible = false;
    ctx.attachLayoutManager(glInstance);

    for (const def of PanelRegistry.all()) {
      glInstance.registerComponentFactoryFunction(def.id, (container) => {
        container.element.style.cssText = `width:100%;height:100%;overflow:${def.overflow};`;
        registerDockPanelLifecycle(container, def.id);
        def.mount(ctx, container.element);
      });
    }

    // No panel pops out: the factories above mount Mithril roots in this
    // window, and Golden Layout does not run them again in a popout window,
    // which would open with nothing in it. So the dock offers no popout
    // control (`header.popout: false`, default_layout.ts).
    glInstance.loadLayout(ctx.loadInitialLayoutConfig());
  }

  return {
    oncreate: async () => {
      // Apply default theme
      const theme = ctx.panelState.currentTheme;
      document.documentElement.setAttribute('data-theme', theme === 'terminal' ? '' : theme);

      // **FIRST, AND BEFORE ANY AWAIT.** This used to run last, after four
      // network probes -- so on a first visit the modal appeared seconds after
      // the page did, over whatever the reader had started doing, and its
      // backdrop intercepted every click. It read as "the modal reappears"; it
      // was only ever late. A modal that opens with the page is one the reader
      // (and the browser tests' dismiss helper) meets before anything else.
      HelpModal.maybeShowFirstTime();

      // Initialise languages, filesystem cache, graphbase and GitHub auth (all non-blocking)
      try { await ctx.actions.plot.initializeLanguages(); m.redraw(); } catch { /* non-fatal */ }
      try { await ctx.actions.plot.initializeLexiconLanguages(); m.redraw(); } catch { /* non-fatal */ }
      await ctx.refreshCache();
      ctx.refreshGraphbase();        // probe graphbase — sets graphbaseAvailable
      ctx.refreshGithubAuthStatus(); // probe GitHub auth — surfaces bad-token early
    },

    // Mithril's real removal hook is `onremove`, not `ondestroy` (which
    // isn't a recognized lifecycle name at all -- Mithril silently ignores
    // unknown vnode properties, so this cleanup never ran).
    onremove: () => {
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
          // ── GitHub auth indicator ───────────────────────────────────────
          ctx.githubAuthStatus
            ? m('div.gl-app-header__gh-auth', {
                title: ctx.githubAuthStatus.authenticated
                  ? `GitHub: authenticated via ${ctx.githubAuthStatus.source}`
                  : `GitHub: unauthenticated (60 req/h) — set CC_GITHUB_TOKEN or run 'gh auth login'`,
                class: ctx.githubAuthStatus.authenticated
                  ? 'gl-app-header__gh-auth--ok'
                  : 'gl-app-header__gh-auth--warn',
              }, [
                m('span.gl-app-header__gh-dot'),
                m('span.gl-app-header__gh-label',
                  ctx.githubAuthStatus.authenticated ? 'GH' : 'GH?'),
              ])
            : null,
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
          // Ctrl+right-click on the dock area opens the add-window menu.
          // Plain right-click is left to the graph renderer's own contextmenu
          // handlers (which call preventDefault themselves for node targets) or
          // falls through to the browser's native menu on empty chrome areas.
          oncontextmenu: (e: MouseEvent) => {
            if (!e.ctrlKey) return;
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
