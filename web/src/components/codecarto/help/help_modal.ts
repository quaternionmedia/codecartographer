/**
 * HelpModal — first-time walkthrough + on-demand help overlay.
 *
 * First-time behaviour:
 *   Auto-shows on first visit (localStorage 'cc:help-dismissed' absent).
 *   Dismissed permanently via "Got it" / clicking outside.
 *
 * On-demand:
 *   Call HelpModal.open() to re-open from a help button.
 */

import m from 'mithril';

const DISMISSED_KEY = 'cc:help-dismissed';

const STEPS = [
  {
    icon: '📁',
    title: 'Load a repository',
    body: 'Paste a GitHub URL or a local path in the Repository tab and press → Fetch, or drop files in the Upload tab. ⚡ Load Demo draws a sample graph. The ▶ Actions tab plots and cancels.',
  },
  {
    icon: '◈',
    title: 'Explore the graph',
    body: 'Scroll to zoom, drag the canvas to pan, and drag individual nodes to rearrange. Hover a node for details.',
  },
  {
    icon: '⚙',
    title: 'Tune the visualization',
    body: 'Open the Graph Settings tab to choose the renderer and the layout algorithm, adjust node size, labels and color, and pick a theme.',
  },
  {
    icon: '⊞',
    title: 'Manage panels',
    body: 'Drag tabs to rearrange, and drag the dividers to resize. Click ✕ to close a panel. The + button in the top bar adds a panel, closed ones included, and saves or resets the layout.',
  },
];

let _isOpen = false;
let _step = 0;

/**
 * Escape closes it. A modal that only closes on its own `×` is one every
 * keyboard reader and every browser test presses Escape at first, and the
 * dismiss helper in `web/tests/e2e/helpers.ts` did exactly that and then had
 * to fall back to hunting for the button.
 */
function onKey(e: KeyboardEvent): void {
  if (e.key === 'Escape' && _isOpen) HelpModal.close();
}

export const HelpModal = {
  /** Open the help modal (always). */
  open(): void {
    _isOpen = true;
    _step = 0;
    document.addEventListener('keydown', onKey);
    m.redraw();
  },

  /** Show only if user has never dismissed it. */
  maybeShowFirstTime(): void {
    if (!localStorage.getItem(DISMISSED_KEY)) {
      this.open();
    }
  },

  close(): void {
    _isOpen = false;
    document.removeEventListener('keydown', onKey);
    localStorage.setItem(DISMISSED_KEY, '1');
    m.redraw();
  },
};

export const HelpModalComponent: m.Component = {
  view() {
    if (!_isOpen) return null;

    const step = STEPS[_step];
    const isLast = _step === STEPS.length - 1;

    return m('div.cc-modal-backdrop', {
      onclick: (e: MouseEvent) => {
        if ((e.target as HTMLElement).classList.contains('cc-modal-backdrop')) {
          HelpModal.close();
        }
      },
    }, [
      m('div.cc-modal', [
        m('button.cc-modal__close', { onclick: HelpModal.close.bind(HelpModal) }, '×'),

        m('div.cc-modal__step-icon', step.icon),
        m('h2.cc-modal__title', step.title),
        m('p.cc-modal__body', step.body),

        // Step dots
        m('div.cc-modal__dots',
          STEPS.map((_, i) =>
            m('span.cc-modal__dot', {
              class: i === _step ? 'cc-modal__dot--active' : '',
              onclick: () => { _step = i; m.redraw(); },
            })
          )
        ),

        // Navigation
        m('div.cc-modal__actions', [
          _step > 0
            ? m('button.cc-modal__btn.cc-modal__btn--secondary', {
                onclick: () => { _step--; m.redraw(); },
              }, '← Back')
            : null,

          isLast
            ? m('button.cc-modal__btn.cc-modal__btn--primary', {
                onclick: HelpModal.close.bind(HelpModal),
              }, 'Got it!')
            : m('button.cc-modal__btn.cc-modal__btn--primary', {
                onclick: () => { _step++; m.redraw(); },
              }, 'Next →'),
        ]),
      ]),
    ]);
  },
};
