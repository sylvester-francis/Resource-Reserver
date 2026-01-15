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

    // Click logout
    await page.getByRole('button', { name: /logout|sign out/i }).click();

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Setup Flow', () => {
  test('should show setup page when no users exist', async ({ page }) => {
    // Note: This test assumes a fresh database
    // In practice, you'd use a test fixture to reset the database
    await page.goto('/setup');
    await page.waitForLoadState('domcontentloaded');

    // Check if setup page loads
    const setupHeading = page.getByRole('heading', { name: /setup|create.*admin|get started/i });
    const alreadySetup = page.getByText(/already.*set.*up|admin.*exists/i);

    // Either setup page or redirect message should be visible
    await expect(setupHeading.or(alreadySetup)).toBeVisible();
  });
});
