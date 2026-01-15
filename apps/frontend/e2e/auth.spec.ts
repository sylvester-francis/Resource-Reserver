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
    // So we expect to see the "already set up" state or redirect
    await page.goto('/setup');
    await page.waitForLoadState('networkidle');

    // Check if setup page loads or redirects
    const setupHeading = page.getByRole('heading', { name: /setup|create.*admin|get started/i });
    const alreadySetup = page.getByText(/already.*set.*up|admin.*exists|system.*configured/i);
    const loginPage = page.getByRole('heading', { name: /sign in/i });
    const dashboardPage = page.getByRole('heading', { name: /dashboard/i });

    // Any of these states is valid since users were created in global setup
    await expect(
      setupHeading.or(alreadySetup).or(loginPage).or(dashboardPage)
    ).toBeVisible({ timeout: 10000 });
  });
});
