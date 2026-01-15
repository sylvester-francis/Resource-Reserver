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

  // Wait for the page to be fully loaded and stable
  await page.waitForLoadState('networkidle');

  // Check if we're redirected to setup (no users exist)
  const currentUrl = page.url();
  if (currentUrl.includes('/setup')) {
    throw new Error('No users exist - global setup may have failed. Check password requirements.');
  }

  // Wait for the login form to be stable (React hydration complete)
  const usernameInput = page.getByLabel(/username/i);
  const passwordInput = page.getByLabel(/password/i);
  const submitButton = page.getByRole('button', { name: /sign in/i });

  // Wait for all form elements to be visible and stable
  await expect(usernameInput).toBeVisible({ timeout: 15000 });
  await expect(passwordInput).toBeVisible({ timeout: 15000 });
  await expect(submitButton).toBeVisible({ timeout: 15000 });

  // Small delay to ensure React hydration is complete
  await page.waitForTimeout(500);

  // Fill the form with explicit clearing first
  await usernameInput.clear();
  await usernameInput.fill(username);
  await passwordInput.clear();
  await passwordInput.fill(password);

  // Wait a moment for form state to settle
  await page.waitForTimeout(200);

  await submitButton.click();

  // Wait for either dashboard redirect or error message
  const dashboardUrl = page.waitForURL(/\/dashboard/, { timeout: 15000 });
  const errorMessage = page.getByText(/invalid|incorrect|failed|error/i).first();

  // Race between successful redirect and error message
  const result = await Promise.race([
    dashboardUrl.then(() => 'success'),
    errorMessage.waitFor({ state: 'visible', timeout: 5000 }).then(() => 'error').catch(() => null),
  ]);

  if (result === 'error') {
    const errorText = await errorMessage.textContent();
    throw new Error(`Login failed with error: ${errorText}`);
  }

  // Verify we're on dashboard
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 5000 });

  // Wait for dashboard to be fully loaded
  await page.waitForLoadState('networkidle');
}

/**
 * Login as admin user.
 */
export async function loginAsAdmin(page: Page) {
  await login(page, 'admin', ADMIN_PASSWORD);
}
