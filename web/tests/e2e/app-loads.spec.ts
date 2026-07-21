import { test, expect } from '@playwright/test';
import { dismissOnboardingModal } from './helpers';

test('app loads and shows the control panel', async ({ page }) => {
  await page.goto('/');
  await dismissOnboardingModal(page);

  await expect(page).toHaveTitle('Code Cartographer');
  await expect(
    page.getByRole('button', { name: /Load Demo/i }).first()
  ).toBeVisible();
});
