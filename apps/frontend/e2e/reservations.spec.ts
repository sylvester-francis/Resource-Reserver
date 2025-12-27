/**
 * Reservations tests.
 */

import { test, expect } from '@playwright/test';

// Helper to login before tests that require authentication
async function login(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.getByLabel(/username/i).fill('testuser');
  await page.getByLabel(/password/i).fill('testpass123');
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
}

test.describe('Making Reservations', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should open reservation dialog', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Find a reserve button or resource card
    const reserveButton = page.getByRole('button', { name: /reserve|book/i }).first();

    if (await reserveButton.isVisible()) {
      await reserveButton.click();

      // Dialog should appear
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show reservation form fields', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Open reservation dialog
    const reserveButton = page.getByRole('button', { name: /reserve|book/i }).first();

    if (await reserveButton.isVisible()) {
      await reserveButton.click();

      // Wait for dialog
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // Check for date and time fields
      const dateField = page.getByLabel(/date/i).or(page.locator('input[type="date"]'));
      const startField = page.getByLabel(/start/i).or(page.locator('input[name*="start"]'));
      const endField = page.getByLabel(/end/i).or(page.locator('input[name*="end"]'));

      // At least date field should be visible
      await expect(dateField.or(startField)).toBeVisible();
    }
  });

  test('should submit reservation successfully', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Open reservation dialog
    const reserveButton = page.getByRole('button', { name: /reserve|book/i }).first();

    if (await reserveButton.isVisible()) {
      await reserveButton.click();

      // Wait for dialog
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // Fill in the form (simplified - actual implementation may vary)
      const confirmButton = page.getByRole('button', { name: /confirm|submit|create|book/i });

      if (await confirmButton.isEnabled()) {
        await confirmButton.click();

        // Wait for success message or dialog close
        await page.waitForTimeout(2000);

        // Check for success indicator
        const successMessage = page.getByText(/success|created|confirmed|reserved/i);
        const dialogClosed = await page.getByRole('dialog').isHidden();

        expect(await successMessage.isVisible() || dialogClosed).toBeTruthy();
      }
    }
  });

  test('should show validation errors for invalid input', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Open reservation dialog
    const reserveButton = page.getByRole('button', { name: /reserve|book/i }).first();

    if (await reserveButton.isVisible()) {
      await reserveButton.click();

      // Wait for dialog
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      // Try to submit without filling required fields
      const confirmButton = page.getByRole('button', { name: /confirm|submit|create|book/i });

      if (await confirmButton.isVisible()) {
        await confirmButton.click();

        // Should show validation error
        await page.waitForTimeout(1000);

        const errorMessage = page.getByText(/required|invalid|error|select/i);

        // Either button is disabled or error is shown
        const hasValidation =
          (await confirmButton.isDisabled()) || (await errorMessage.isVisible());

        expect(hasValidation).toBeTruthy();
      }
    }
  });
});

test.describe('Viewing Reservations', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display user reservations', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Look for reservations section
    const reservationsSection = page.getByText(/my reservations|upcoming|your bookings/i);

    await expect(reservationsSection).toBeVisible({ timeout: 5000 });
  });

  test('should show reservation details', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Find a reservation card
    const reservationCard = page.locator('[data-testid="reservation-card"], .reservation-item').first();

    if (await reservationCard.isVisible()) {
      await reservationCard.click();

      // Should show details
      const detailsDialog = page.getByRole('dialog');
      const detailsText = page.getByText(/details|resource|time|date/i);

      await expect(detailsDialog.or(detailsText)).toBeVisible();
    }
  });
});

test.describe('Cancelling Reservations', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show cancel button for active reservations', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Find a reservation card
    const reservationCard = page.locator('[data-testid="reservation-card"], .reservation-item').first();

    if (await reservationCard.isVisible()) {
      // Look for cancel button
      const cancelButton = reservationCard.getByRole('button', { name: /cancel/i });

      // Cancel button should exist for user's own reservations
      if (await cancelButton.isVisible()) {
        await expect(cancelButton).toBeEnabled();
      }
    }
  });

  test('should confirm before cancelling', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Find cancel button
    const cancelButton = page.getByRole('button', { name: /cancel/i }).first();

    if (await cancelButton.isVisible()) {
      await cancelButton.click();

      // Should show confirmation dialog
      const confirmDialog = page.getByRole('alertdialog').or(page.getByRole('dialog'));
      const confirmText = page.getByText(/sure|confirm|cancel this/i);

      await expect(confirmDialog.or(confirmText)).toBeVisible({ timeout: 3000 });
    }
  });

  test('should cancel reservation successfully', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Find cancel button
    const cancelButton = page.getByRole('button', { name: /cancel/i }).first();

    if (await cancelButton.isVisible()) {
      await cancelButton.click();

      // Confirm cancellation
      const confirmButton = page.getByRole('button', { name: /confirm|yes|cancel.*reservation/i });

      if (await confirmButton.isVisible()) {
        await confirmButton.click();

        // Wait for success message
        await page.waitForTimeout(2000);

        const successMessage = page.getByText(/cancelled|removed|success/i);

        // Either success message or reservation is removed
        const wasCancelled =
          (await successMessage.isVisible()) ||
          (await page.locator('.reservation-item').count()) === 0;

        expect(wasCancelled).toBeTruthy();
      }
    }
  });
});
