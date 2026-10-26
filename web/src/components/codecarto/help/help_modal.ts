/**
 * HelpModal — first-time walkthrough + on-demand help overlay.
 *
 * A page per step of the flow (`web/src/layout/steps.ts`), and the page shown
 * is the step the reader is on: the card has no step of its own, it reads the
 * one the header's rail fills. ← Back, Next → and the dots enter a step, so
 * the step's windows come forward behind the card as it turns, and the rail
 * moves with it. Closing it leaves the reader on the step it showed.
 *
 * First-time behaviour:
 *   Auto-shows on first visit (localStorage 'cc:help-dismissed' absent), on
 *   step 1, which is where a page opens.
 *   Dismissed permanently via "Got it" / clicking outside.
 *
 * On-demand:
 *   Call HelpModal.open() to re-open from a help button, at the current step.
 */

import m from 'mithril';

import { STEPS, nextStep, previousStep, stepNamed, stepNumber } from '../../../layout/steps';
import type { StepId } from '../../../layout/steps';

const DISMISSED_KEY = 'cc:help-dismissed';

let _isOpen = false;

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

interface Attrs {
  /** The step the reader is on, whose page is shown. */
  step: StepId;
  /** Enter a step: what ← Back, Next → and a dot ask for. */
  onStep: (id: StepId) => void;
}

export const HelpModalComponent: m.Component<Attrs> = {
  view({ attrs }) {
    if (!_isOpen) return null;

    const step = stepNamed(attrs.step);
    const previous = previousStep(step.id);
    const next = nextStep(step.id);

    return m('div.cc-modal-backdrop', {
      onclick: (e: MouseEvent) => {
        if ((e.target as HTMLElement).classList.contains('cc-modal-backdrop')) {
          HelpModal.close();
        }
      },
    }, [
      m('div.cc-modal', { 'data-step': step.id }, [
        m('button.cc-modal__close', { onclick: HelpModal.close.bind(HelpModal) }, '×'),

        m('div.cc-modal__step-icon', step.icon),
        m('p.cc-modal__step-count', `Step ${stepNumber(step.id)} of ${STEPS.length} · ${step.label}`),
        m('h2.cc-modal__title', step.title),
        m('p.cc-modal__body', step.body),

        // Step dots
        m('div.cc-modal__dots',
          STEPS.map((s, i) =>
            m('span.cc-modal__dot', {
              class: s.id === step.id ? 'cc-modal__dot--active' : '',
              title: `Step ${i + 1}: ${s.label}`,
              onclick: () => attrs.onStep(s.id),
            })
          )
        ),

        // Navigation
        m('div.cc-modal__actions', [
          previous
            ? m('button.cc-modal__btn.cc-modal__btn--secondary', {
                onclick: () => attrs.onStep(previous.id),
              }, '← Back')
            : null,

          next
            ? m('button.cc-modal__btn.cc-modal__btn--primary', {
                onclick: () => attrs.onStep(next.id),
              }, `Next: ${next.label} →`)
            : m('button.cc-modal__btn.cc-modal__btn--primary', {
                onclick: HelpModal.close.bind(HelpModal),
              }, 'Got it!'),
        ]),
      ]),
    ]);
  },
};
