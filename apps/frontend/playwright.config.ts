/**
 * Playwright configuration.
 */

import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E test configuration.
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: false, // Run tests serially to avoid login conflicts
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1, // Single worker to prevent concurrent login issues
  timeout: 30000, // 30 second timeout per test
  expect: {
    timeout: 10000, // 10 second timeout for expects
  },
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000, // 15 second timeout for actions
    navigationTimeout: 30000, // 30 second timeout for navigation
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
    env: {
      ...process.env,
      // Ensure Next.js rewrites proxy to the correct backend URL
      INTERNAL_API_URL: process.env.INTERNAL_API_URL || 'http://localhost:8000',
    },
  },
});
