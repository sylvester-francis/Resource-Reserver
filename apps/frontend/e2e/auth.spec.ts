/**
 * Auth tests.
 */

import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should show login page for unauthenticated users', async ({ page }) => {
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
  });

  test('should display login form elements', async ({ page }) => {
    await page.goto('/login');

    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel(/username/i).fill('invaliduser');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for error message
    await expect(page.getByText(/invalid|incorrect|failed/i)).toBeVisible({ timeout: 5000 });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');

    // Use test credentials
    await page.getByLabel(/username/i).fill('testuser');
    await page.getByLabel(/password/i).fill('testpass123');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should persist session after login', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel(/username/i).fill('testuser');
    await page.getByLabel(/password/i).fill('testpass123');
    await page.getByRole('button', { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Navigate away and back
    await page.reload();

    // Should still be on dashboard (session persisted)
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should logout successfully', async ({ page }) => {
    // First login
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('testuser');
    await page.getByLabel(/password/i).fill('testpass123');
    await page.getByRole('button', { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

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

    // Check if setup page loads
    const setupHeading = page.getByRole('heading', { name: /setup|create.*admin|get started/i });
    const alreadySetup = page.getByText(/already.*set.*up|admin.*exists/i);

    // Either setup page or redirect message should be visible
    await expect(setupHeading.or(alreadySetup)).toBeVisible();
  });
});
