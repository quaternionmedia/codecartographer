/**
 * GoldenLayoutShell
 *
 * Top-level Mithril component: the application header and the Golden Layout
 * dock under it.
 *
 * Every panel in `panel_registry.ts` is registered here as a Golden Layout
 * component, and the saved layout (or `default_layout.ts`) is loaded, on
 * step 1 of the flow (`steps.ts`). The header holds the "+" add-window menu,
 * the step rail, the GitHub auth indicator and the help button, whose
 * walkthrough is a page per step.
 */

import m from 'mithril';
import { GoldenLayout } from 'golden-layout';

import type { ICell } from '../state/cell_state';
import { LayoutContext } from './layout_context';
import { PanelRegistry } from './panel_registry';
import { AddPanelMenu } from './components/add_panel_menu';
import { StepRail } from './components/step_rail';
import { DEFAULT_LAYOUT_CONFIG } from './default_layout';
import { FIRST_STEP } from './steps';

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
  /** The "+" button, which the focus returns to when the menu closes. */
  let menuOpener: HTMLElement | null = null;

  const closeMenu = (): void => { if (menuOpen) { menuOpen = false; m.redraw(); } };

  /** Mount GL panels after the host element exists in the DOM. */
  function initGoldenLayout(hostElement: HTMLElement): void {
    glInstance = new GoldenLayout(hostElement);
    // **THE DOCK FOLLOWS THE WINDOW.** Golden Layout sizes every stack in
    // pixels, and resizes with its container by itself only when that is the
    // page's body; this host is the shell's own element. Without this a
    // narrowed window cut off the dock's right side, stacks' controls and all,
    // and a widened one left a band of nothing beside it. Golden Layout
    // observes the host either way, and acts on a resize when this is set.
    glInstance.resizeWithContainerAutomatically = true;
    ctx.attachLayoutManager(glInstance);
    // The stack whose tab the reader last clicked is where the "+" menu adds a
    // window. Heard in the capture phase, so before Golden Layout's own tab
    // handler, which is where its focus moves -- and focus also moves from
    // code, which is why it is not read for this.
    hostElement.addEventListener('click', (e) => ctx.noteClick(e.target), { capture: true });

    for (const def of PanelRegistry.all()) {
      glInstance.registerComponentFactoryFunction(def.id, (container) => {
        container.element.style.cssText = `width:100%;height:100%;overflow:${def.overflow};`;
        // A saved layout keeps the tab titles it was saved with, a renamed
        // window's included; the registry's title is the one drawn.
        if (def.config.title) container.setTitle(def.config.title);
        def.mount(ctx, container.element);
      });
    }

    // Known limitation: GL 2.x pop-out opens a new window but Mithril component
    // factories are bound to the original window — components never mount in pop-outs.
    // popInOnClose: true (default_layout.ts) auto-returns panels on pop-out close.
    const initial = ctx.loadInitialLayoutConfig();
    try {
      glInstance.loadLayout(initial);
    } catch (err) {
      // The saved layout passed the check in `loadInitialLayoutConfig` and
      // Golden Layout refused it anyway. Boot the default rather than a page
      // with no windows. The default itself failing is a bug, and throws.
      if (initial === DEFAULT_LAYOUT_CONFIG) throw err;
      ctx.dropSavedLayout(`Golden Layout refused it (${err instanceof Error ? err.message : String(err)})`);
      glInstance.loadLayout(DEFAULT_LAYOUT_CONFIG);
    }

    // The rail says step 1, so the dock shows it: a saved layout may have
    // been kept with another tab in front, or with a stack maximised.
    ctx.enterStep(FIRST_STEP);

    // A `?show=` address opens its showgraph, once the dock exists to open
    // the Show panel in and the canvas has its size to fit the graph to.
    // Not awaited: nothing else at boot waits on a family being measured.
    requestAnimationFrame(() => { void ctx.openShowFromLocation(); });
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
      void ctx.refreshExamples();
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
              menuOpener = e.currentTarget as HTMLElement;
              const rect = menuOpener.getBoundingClientRect();
              menuPos = { x: rect.left, y: rect.bottom };
              menuOpen = !menuOpen;
            },
            title: 'Add a window',
            'aria-expanded': String(menuOpen),
          }, '+'),
          m('h1.gl-app-header__title', [
            m('span.gl-app-header__icon', '◈'),
            'Code Cartographer',
          ]),
          m(StepRail, { ctx }),
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

        menuOpen
          ? m(AddPanelMenu, {
              ctx,
              x: menuPos.x,
              y: menuPos.y,
              onClose: closeMenu,
              opener: menuOpener,
            })
          : null,

        // ── Overlays (modals / toasts — rendered above GL chrome) ─────────
        m('div.gl-overlays', [
          m(HelpModalComponent, { step: ctx.step, onStep: (id) => ctx.enterStep(id) }),
          m(ToastContainer),
        ]),
      ]);
    },
  };
};
