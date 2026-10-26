/**
 * StepRail
 *
 * The four steps (`steps.ts`) in the header, numbered, the one the reader is
 * on filled, and then what comes next: always shown, so the whole flow reads
 * at a glance, as alfred's stage rail does. A step's button enters it, the
 * step already on included -- which brings its windows forward again, one
 * closed since among them. Next enters the step after; the last step has no
 * Next.
 *
 * An ordered list of buttons with `aria-current="step"`, which is what a step
 * indicator is, rather than alfred's tablist: these buttons show no tab panel
 * of their own, and a tablist promises arrow keys between its tabs.
 */

import m from 'mithril';
import type { LayoutContext } from '../layout_context';
import { STEPS, nextStep, stepNumber } from '../steps';

interface Attrs {
  ctx: LayoutContext;
}

export const StepRail: m.Component<Attrs> = {
  view: ({ attrs: { ctx } }) => {
    const next = nextStep(ctx.step);
    return m('nav.gl-steps', { 'aria-label': 'Steps' }, [
      m('ol.gl-steps__list',
        STEPS.map((step, i) => {
          const current = step.id === ctx.step;
          return m('li', m('button.gl-steps__step', {
            'data-step': step.id,
            class: current ? 'gl-steps__step--current' : '',
            // On the current step only; Mithril leaves an undefined attribute out.
            'aria-current': current ? 'step' : undefined,
            title: `Step ${i + 1}: ${step.hint}`,
            onclick: () => ctx.enterStep(step.id),
          }, [m('span.gl-steps__num', String(i + 1)), m('span.gl-steps__label', step.label)]));
        }),
      ),
      next
        ? m('button.gl-steps__next', {
            title: `Step ${stepNumber(next.id)}: ${next.hint}`,
            onclick: () => ctx.enterStep(next.id),
          }, ['Next ', m('span.gl-steps__num', String(stepNumber(next.id))), ` ${next.label} →`])
        : null,
    ]);
  },
};
