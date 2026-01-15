/**
 * Shared E2E test utilities.
 */

import { Page, expect } from '@playwright/test';

// Passwords must have uppercase letter, special character, and NOT contain username
const DEFAULT_PASSWORD = 'Secure@Pass456!';
const ADMIN_PASSWORD = 'Secure@Pass123!';

/**
 * Login helper that waits for page stability before interacting.
 * This prevents "element was detached from the DOM" errors during React hydration.
 */
export async function login(page: Page, username = 'testuser', password = DEFAULT_PASSWORD) {
  // Clear cookies to ensure fresh login state
  await page.context().clearCookies();

  await page.goto('/login');

  // Wait for DOM content to load (don't wait for all network requests)
  await page.waitForLoadState('domcontentloaded');

  // Check if we're redirected to setup (no users exist) - with short timeout
  try {
    await page.waitForURL(/\/(login|setup)/, { timeout: 5000 });
  } catch {
    // If timeout, check current URL
  }

  const currentUrl = page.url();
  if (currentUrl.includes('/setup')) {
    throw new Error('No users exist - global setup may have failed. Check password requirements.');
  }

  // Wait for the login form elements to be visible
  const usernameInput = page.getByLabel(/username/i);
  const passwordInput = page.getByLabel(/password/i);
  const submitButton = page.getByRole('button', { name: /sign in/i });

  // Wait for form elements with reasonable timeout
  await expect(usernameInput).toBeVisible({ timeout: 10000 });
  await expect(passwordInput).toBeVisible({ timeout: 5000 });
  await expect(submitButton).toBeVisible({ timeout: 5000 });

  // Small delay to ensure React hydration is complete
  await page.waitForTimeout(300);

  // Fill the form
  await usernameInput.fill(username);
  await passwordInput.fill(password);

  await submitButton.click();

  // Wait for either dashboard redirect OR error message
  const dashboardPromise = page.waitForURL(/\/dashboard/, { timeout: 10000 });
  const errorLocator = page.locator('[role="alert"], .text-destructive, .text-red-500').first();

  try {
    // Race between dashboard redirect and error appearing
    await Promise.race([
      dashboardPromise,
      errorLocator.waitFor({ state: 'visible', timeout: 5000 }).then(() => {
        throw new Error('LOGIN_ERROR');
      }),
    ]);
  } catch (e) {
    if (e instanceof Error && e.message === 'LOGIN_ERROR') {
      // Get the error text
      const errorText = await errorLocator.textContent().catch(() => 'Unknown error');
      throw new Error(`Login failed for user '${username}': ${errorText}`);
    }
    // Check if we're still on login page
    if (page.url().includes('/login')) {
      // Check for any visible error text
      const visibleError = await page.getByText(/invalid|incorrect|failed|error|wrong/i).first().textContent().catch(() => null);
      throw new Error(`Login failed for user '${username}'. Still on login page. Error: ${visibleError || 'No error message visible'}`);
    }
    throw e;
  }

  // Brief wait for dashboard to render
  await page.waitForTimeout(500);
}

/**
 * Login as admin user.
 */
export async function loginAsAdmin(page: Page) {
  await login(page, 'admin', ADMIN_PASSWORD);
}
