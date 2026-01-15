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
  await page.goto('/login');

  // Wait for the page to be fully loaded and stable
  await page.waitForLoadState('networkidle');

  // Wait for the login form to be stable (React hydration complete)
  const usernameInput = page.getByLabel(/username/i);
  const passwordInput = page.getByLabel(/password/i);
  const submitButton = page.getByRole('button', { name: /sign in/i });

  // Wait for all form elements to be visible and stable
  await expect(usernameInput).toBeVisible({ timeout: 15000 });
  await expect(passwordInput).toBeVisible({ timeout: 15000 });
  await expect(submitButton).toBeVisible({ timeout: 15000 });

  // Small delay to ensure React hydration is complete
  await page.waitForTimeout(1000);

  // Fill the form
  await usernameInput.fill(username);
  await passwordInput.fill(password);
  await submitButton.click();

  // Wait for redirect to dashboard with longer timeout
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });

  // Wait for dashboard to be fully loaded
  await page.waitForLoadState('networkidle');
}

/**
 * Login as admin user.
 */
export async function loginAsAdmin(page: Page) {
  await login(page, 'admin', ADMIN_PASSWORD);
}
