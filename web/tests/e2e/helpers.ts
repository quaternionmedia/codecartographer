import { Page } from '@playwright/test';

/**
 * Dismiss the onboarding modal if it's covering the app on first load.
 * Its backdrop (`.cc-modal-backdrop`) intercepts pointer events, so any
 * test that needs to click something in the control panel must call this
 * first.
 */
export async function dismissOnboardingModal(page: Page): Promise<void> {
  const backdrop = page.locator('.cc-modal-backdrop');
  if ((await backdrop.count()) === 0) return;
  await page.keyboard.press('Escape');
  if ((await backdrop.count()) > 0) {
    await backdrop.locator('button', { hasText: '×' }).first().click({ force: true });
  }
}
