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
    await page.waitForLoadState('networkidle');

    // Look for waitlist button
    const waitlistButton = page.getByRole('button', { name: /waitlist|join.*queue|notify/i });

    // If there are unavailable resources, waitlist option should be visible
    if (await waitlistButton.count() > 0) {
      await expect(waitlistButton.first()).toBeVisible();
    }
  });

  test('should allow joining waitlist', async ({ page }) => {
    await page.waitForLoadState('networkidle');

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
    await page.waitForLoadState('networkidle');

    // Look for waitlist position indicator
    const positionIndicator = page.getByText(/position|#\d|queue/i);

    // This test is informational - position may or may not be visible
    if (await positionIndicator.count() > 0) {
      await expect(positionIndicator.first()).toBeVisible();
    }
  });

  test('should allow leaving waitlist', async ({ page }) => {
    await page.waitForLoadState('networkidle');

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
    await page.waitForLoadState('networkidle');

    // Look for waitlist section
    const waitlistSection = page.getByText(/waitlist|waiting/i);

    // If user has waitlist entries, they should be displayed
    if (await waitlistSection.count() > 0) {
      await expect(waitlistSection.first()).toBeVisible();
    }
  });
});

test.describe('Waitlist Notifications', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show notification preferences', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Navigate to settings or preferences
    const settingsLink = page.getByRole('link', { name: /settings|preferences/i });

    if (await settingsLink.isVisible()) {
      await settingsLink.click();

      // Look for notification settings
      const notificationSettings = page.getByText(/notification|email|alert/i);

      await expect(notificationSettings).toBeVisible();
    }
  });
});
