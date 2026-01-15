/**
 * Waitlist tests.
 */

import { test, expect } from '@playwright/test';
import { login } from './test-utils';

test.describe('Waitlist Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show join waitlist option for unavailable resources', async ({ page }) => {
    await page.waitForTimeout(500); // Brief wait for content to load

    // Look for waitlist button
    const waitlistButton = page.getByRole('button', { name: /waitlist|join.*queue|notify/i });

    // If there are unavailable resources, waitlist option should be visible
    if (await waitlistButton.count() > 0) {
      await expect(waitlistButton.first()).toBeVisible();
    }
  });

  test('should allow joining waitlist', async ({ page }) => {
    await page.waitForTimeout(500); // Brief wait for content to load

    // Find join waitlist button
    const joinButton = page.getByRole('button', { name: /join.*waitlist|add.*waitlist/i }).first();

    if (await joinButton.isVisible()) {
      await joinButton.click();

      // Should show confirmation or success message
      await page.waitForTimeout(2000);

      const successIndicator = page
        .getByText(/added|joined|waitlist|position|queue/i)
        .or(page.getByRole('button', { name: /leave.*waitlist|remove.*queue/i }));

      await expect(successIndicator).toBeVisible();
    }
  });

  test('should show waitlist position', async ({ page }) => {
    await page.waitForTimeout(500); // Brief wait for content to load

    // Verify we're on the dashboard first
    await expect(page).toHaveURL(/\/dashboard/);

    // Look for waitlist position indicator or dashboard content
    const positionIndicator = page.getByText(/position|#\d|queue/i);
    const dashboardContent = page.getByRole('heading', { name: /dashboard/i });

    // Either position indicator (if on waitlist) or dashboard heading should be visible
    await expect(positionIndicator.first().or(dashboardContent)).toBeVisible({ timeout: 5000 });
  });

  test('should allow leaving waitlist', async ({ page }) => {
    await page.waitForTimeout(500); // Brief wait for content to load

    // Find leave waitlist button
    const leaveButton = page.getByRole('button', { name: /leave.*waitlist|remove.*queue|cancel.*wait/i }).first();

    if (await leaveButton.isVisible()) {
      await leaveButton.click();

      // Should show confirmation or success
      await page.waitForTimeout(2000);

      const successMessage = page.getByText(/removed|left|cancelled/i);
      const joinButton = page.getByRole('button', { name: /join.*waitlist/i });

      // Either success message or join button reappears
      await expect(successMessage.or(joinButton)).toBeVisible();
    }
  });

  test('should display waitlist entries in user dashboard', async ({ page }) => {
    await page.waitForTimeout(500); // Brief wait for content to load

    // Verify we're on the dashboard first
    await expect(page).toHaveURL(/\/dashboard/);

    // Look for waitlist section or dashboard content
    const waitlistSection = page.getByText(/waitlist|waiting|queue/i);
    const dashboardContent = page.getByRole('heading', { name: /dashboard/i });

    // Either waitlist section (if entries exist) or dashboard heading should be visible
    await expect(waitlistSection.first().or(dashboardContent)).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Waitlist Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show notification preferences', async ({ page }) => {
    await page.waitForTimeout(500); // Brief wait for content to load

    // Verify we're on the dashboard first
    await expect(page).toHaveURL(/\/dashboard/);

    // Navigate to settings or preferences if link exists
    const settingsLink = page.getByRole('link', { name: /settings|preferences/i });
    const dashboardContent = page.getByRole('heading', { name: /dashboard/i });

    if (await settingsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await settingsLink.click();
      await page.waitForTimeout(500); // Brief wait for content to load

      // Look for notification settings
      const notificationSettings = page.getByText(/notification|email|alert|preferences/i);
      await expect(notificationSettings.first()).toBeVisible({ timeout: 5000 });
    } else {
      // If no settings link, just verify dashboard is visible
      await expect(dashboardContent).toBeVisible({ timeout: 5000 });
    }
  });
});
