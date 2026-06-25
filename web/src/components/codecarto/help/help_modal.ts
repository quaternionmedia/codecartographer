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
    body: 'Open the Source tab, paste a GitHub URL or upload files, then click "Plot Directory" to visualize the structure.',
  },
  {
    icon: '◈',
    title: 'Explore the graph',
    body: 'Scroll to zoom, drag the canvas to pan, and drag individual nodes to rearrange. Hover a node for details.',
  },
  {
    icon: '⚙',
    title: 'Tune the visualization',
    body: 'Switch to the Graph tab to change the layout algorithm, toggle physics, adjust node size, and pick a color theme.',
  },
];

let _isOpen = false;
let _step = 0;

export const HelpModal = {
  /** Open the help modal (always). */
  open(): void {
    _isOpen = true;
    _step = 0;
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
