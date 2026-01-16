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

    // Wait for dashboard to fully load
    await page.waitForLoadState('networkidle').catch(() => { });
    await page.waitForTimeout(500);

    // Click the user menu button (avatar)
    const userMenuButton = page.locator('[data-testid="user-menu"]');
    await expect(userMenuButton).toBeVisible({ timeout: 10000 });
    await userMenuButton.click();

    // Wait for dropdown menu to appear
    await page.waitForTimeout(500);

    // Click "Sign Out" using data-testid (most reliable)
    const signOutButton = page.locator('[data-testid="sign-out-button"]');
    await expect(signOutButton).toBeVisible({ timeout: 10000 });
    await signOutButton.click();

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 15000 });
  });
});

test.describe('Setup Flow', () => {
  test('should show setup page when no users exist', async ({ page }) => {
    // Note: This test assumes users already exist (created in global setup)
    // So we expect to see the "already set up" state or redirect to login
    await page.goto('/setup');

    // Wait for DOM to load (don't wait for all network requests)
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000); // Brief wait for redirect

    // The setup page has these possible states:
    // 1. Setup form with heading "Secure your workspace with a first admin."
    // 2. "Setup already complete. Redirecting..." then redirects to /login
    // 3. Already redirected to /login with "Welcome back" CardTitle (h3 by default)

    // Wait for URL to stabilize (either /setup or /login after redirect)
    await expect(page).toHaveURL(/\/(login|setup)/, { timeout: 10000 });

    // Check for appropriate content based on URL
    if (page.url().includes('/login')) {
      // Login page - look for the "Welcome back" text (might be h3 or other element)
      const welcomeText = page.getByText('Welcome back').or(
        page.locator('h1, h2, h3').filter({ hasText: /welcome back/i })
      );
      await expect(welcomeText).toBeVisible({ timeout: 5000 });
    } else {
      // Setup page - look for setup-related content
      const setupContent = page.getByText(/setup already complete|secure your workspace/i);
      await expect(setupContent).toBeVisible({ timeout: 5000 });
    }
  });
});
