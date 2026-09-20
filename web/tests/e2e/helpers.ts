import { Page } from '@playwright/test';

/**
 * Dismiss the onboarding modal if it is covering the app.
 *
 * Its backdrop (`.cc-modal-backdrop`) intercepts pointer events, so any test
 * that clicks anything must call this first. The modal opens with the page on
 * a first visit -- synchronously, in the shell's `oncreate`, before any network
 * probe -- so a short wait for it to attach is enough, and its absence after
 * that means the visit is not a first one.
 *
 * ESCAPE CLOSES IT, AND THE CLOSE IS A REDRAW AWAY. The first version of this
 * pressed Escape and re-counted the backdrop in the same tick, found it still
 * there (Mithril redraws asynchronously), and went looking for a `×` that had
 * just been removed -- every test then waited thirty seconds for a button that
 * no longer existed. So: press Escape, wait for the backdrop to detach, and
 * only if it does not, press the `×`.
 */
export async function dismissOnboardingModal(page: Page): Promise<void> {
  const backdrop = page.locator('.cc-modal-backdrop');
  await backdrop.waitFor({ state: 'attached', timeout: 1_500 }).catch(() => undefined);
  if ((await backdrop.count()) === 0) return;
  await page.keyboard.press('Escape');
  const gone = await backdrop
    .waitFor({ state: 'detached', timeout: 2_000 })
    .then(() => true)
    .catch(() => false);
  if (gone) return;
  await backdrop.locator('button', { hasText: '×' }).first().click({ force: true });
  await backdrop.waitFor({ state: 'detached', timeout: 5_000 });
}
