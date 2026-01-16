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

  // Wait for page to stabilize
  await page.waitForLoadState('networkidle').catch(() => { });
  await page.waitForTimeout(500);

  // Check if we're on setup page (no users exist)
  if (page.url().includes('/setup')) {
    throw new Error('No users exist - global setup may have failed. Check password requirements.');
  }

  // Wait for the login form - use specific selectors to avoid matching setup form
  // Login form has a single password field, setup form has password + confirm
  const usernameInput = page.getByLabel(/username/i);
  // Use exact match for "Password" label to avoid matching "Confirm password"
  const passwordInput = page.getByLabel('Password', { exact: true })
    .or(page.locator('input[type="password"]').first());
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

  // Wait for navigation to dashboard - this is the success case
  try {
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    // Brief wait for dashboard to render
    await page.waitForTimeout(500);
    return; // Success!
  } catch {
    // Navigation to dashboard timed out - check what went wrong
  }

  // If we're on dashboard now despite timeout, it's fine
  if (page.url().includes('/dashboard')) {
    await page.waitForTimeout(500);
    return;
  }

  // Take a screenshot for debugging
  await page.screenshot({ path: `login-failed-${username}.png` }).catch(() => { });

  // Check for error messages
  const errorLocator = page.locator('[data-sonner-toast][data-type="error"], .text-red-500, .text-destructive').first();
  const hasError = await errorLocator.isVisible().catch(() => false);

  if (hasError) {
    const errorText = await errorLocator.textContent().catch(() => 'Unknown error');
    throw new Error(`Login failed for user '${username}': ${errorText?.trim() || 'Error displayed but no message'}`);
  }

  // Check for any visible error text
  const visibleError = await page.getByText(/invalid|incorrect|failed|error|wrong/i).first().textContent().catch(() => null);

  throw new Error(`Login failed for user '${username}'. Current URL: ${page.url()}. Error: ${visibleError || 'No error message visible'}`);
}

/**
 * Login as admin user.
 */
export async function loginAsAdmin(page: Page) {
  await login(page, 'admin', ADMIN_PASSWORD);
}
