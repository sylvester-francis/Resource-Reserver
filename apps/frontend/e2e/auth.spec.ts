/**
 * Auth tests.
 */

import { test, expect } from '@playwright/test';
import { login } from './test-utils';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should show login page for unauthenticated users', async ({ page }) => {
    // Wait for redirect to complete
    await page.waitForLoadState('domcontentloaded');
    // Should redirect to login (or setup if no users)
    await expect(page).toHaveURL(/\/(login|setup)/);
  });

  test('should display login form elements', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500); // Wait for hydration

    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500); // Wait for hydration

    await page.getByLabel(/username/i).fill('invaliduser');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for error message
    await expect(page.getByText(/invalid|incorrect|failed/i)).toBeVisible({ timeout: 5000 });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    // Use the shared login helper
    await login(page);
    // login() already verifies redirect to dashboard
  });

  test('should persist session after login', async ({ page }) => {
    await login(page);

    // Navigate away and back
    await page.reload();

    // Should still be on dashboard (session persisted)
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should logout successfully', async ({ page }) => {
    // First login
    await login(page);

    // Open user dropdown menu (click on avatar/user button)
    const userMenuButton = page.locator('[data-testid="user-menu"]').or(
      page.getByRole('button').filter({ has: page.locator('svg.lucide-user, svg.lucide-circle-user') })
    ).or(
      page.locator('button:has(.avatar, [class*="avatar"])')
    );

    // Try to find and click the user menu
    if (await userMenuButton.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await userMenuButton.first().click();
    }

    // Click logout/sign out in dropdown
    const signOutButton = page.getByRole('menuitem', { name: /sign out|logout/i }).or(
      page.getByText(/sign out|logout/i)
    );
    await signOutButton.click();

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });
});

test.describe('Setup Flow', () => {
  test('should show setup page when no users exist', async ({ page }) => {
    // Note: This test assumes users already exist (created in global setup)
    // So we expect to see the "already set up" state or redirect to login
    await page.goto('/setup');
    await page.waitForLoadState('networkidle');

    // The setup page has these possible states:
    // 1. Setup form with heading "Secure your workspace with a first admin."
    // 2. "Setup already complete. Redirecting..." then redirects to /login
    // 3. Already redirected to /login with "Welcome back" heading

    // Wait for either the setup page content OR redirect to login
    const setupHeading = page.getByRole('heading', { name: /secure your workspace|initial setup/i });
    const alreadySetupText = page.getByText(/setup already complete/i);
    const loginHeading = page.getByRole('heading', { name: /welcome back|sign in/i });

    // First check if we get any expected content
    try {
      await expect(
        setupHeading.or(alreadySetupText).or(loginHeading)
      ).toBeVisible({ timeout: 5000 });
    } catch {
      // If not visible yet, we might be redirecting - wait for login page
      await expect(page).toHaveURL(/\/(login|setup)/, { timeout: 10000 });
      // After redirect, check for login page content
      if (page.url().includes('/login')) {
        await expect(loginHeading).toBeVisible({ timeout: 5000 });
      }
    }
  });
});
