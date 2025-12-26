import { chromium, FullConfig } from '@playwright/test';

/**
 * Global setup for E2E tests.
 * This runs once before all tests.
 */
async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:3000';

  console.log(`[E2E Setup] Starting global setup...`);
  console.log(`[E2E Setup] Base URL: ${baseURL}`);

  // Wait for the server to be ready
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  let retries = 30;
  while (retries > 0) {
    try {
      const response = await page.goto(baseURL, { timeout: 5000 });
      if (response && response.ok()) {
        console.log(`[E2E Setup] Server is ready`);
        break;
      }
    } catch {
      console.log(`[E2E Setup] Waiting for server... (${retries} retries left)`);
      retries--;
      await page.waitForTimeout(1000);
    }
  }

  if (retries === 0) {
    console.error(`[E2E Setup] Server did not start in time`);
  }

  await browser.close();
  console.log(`[E2E Setup] Global setup complete`);
}

export default globalSetup;
