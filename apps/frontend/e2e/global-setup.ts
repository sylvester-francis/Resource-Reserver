/**
 * Global setup end-to-end tests.
 */

import { chromium, FullConfig } from '@playwright/test';

// Passwords must have uppercase letter, special character, and NOT contain username
const DEFAULT_ADMIN = { username: 'admin', password: 'Secure@Pass123!' };
const DEFAULT_USER = { username: 'testuser', password: 'Secure@Pass456!' };

function getApiBaseUrl(baseURL: string): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_BASE_URL;
  if (envUrl) {
    return envUrl;
  }

  try {
    const url = new URL(baseURL);
    if (url.port === '3000') {
      url.port = '8000';
    } else if (!url.port && url.hostname === 'localhost') {
      url.port = '8000';
    }
    return url.origin;
  } catch {
    return 'http://localhost:8000';
  }
}

async function ensureUser(apiBaseUrl: string, username: string, password: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (response.ok) {
    console.log(`[E2E Setup] Created user ${username}`);
    return;
  }

  const detail = await response.text().catch(() => '');

  // Check if user already exists (different possible messages)
  if (response.status === 400 && (detail.includes('already') || detail.includes('exists') || detail.includes('registered'))) {
    console.log(`[E2E Setup] User ${username} already exists`);
    return;
  }

  // Log the actual error for debugging
  console.error(`[E2E Setup] Failed to create user ${username}: ${response.status} ${detail}`);

  // For password validation errors, this is critical - throw to fail the setup
  if (response.status === 422 || (response.status === 400 && detail.includes('password'))) {
    throw new Error(`Password validation failed for user ${username}: ${detail}`);
  }
}

async function ensureSeedUsers(apiBaseUrl: string): Promise<void> {
  const statusResponse = await fetch(`${apiBaseUrl}/api/v1/setup/status`);
  if (statusResponse.ok) {
    const status = await statusResponse.json();
    if (status.user_count === 0) {
      const initResponse = await fetch(`${apiBaseUrl}/api/v1/setup/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: DEFAULT_ADMIN.username,
          password: DEFAULT_ADMIN.password,
        }),
      });

      if (initResponse.ok) {
        console.log('[E2E Setup] Initialized setup with admin user');
      } else {
        const detail = await initResponse.text().catch(() => '');
        console.error(`[E2E Setup] Setup init failed: ${initResponse.status} ${detail}`);
        throw new Error(`Setup initialization failed: ${detail}`);
      }
    }
  }

  await ensureUser(apiBaseUrl, DEFAULT_ADMIN.username, DEFAULT_ADMIN.password);
  await ensureUser(apiBaseUrl, DEFAULT_USER.username, DEFAULT_USER.password);

  // Verify users can login
  await verifyUserLogin(apiBaseUrl, DEFAULT_USER.username, DEFAULT_USER.password);
  await verifyUserLogin(apiBaseUrl, DEFAULT_ADMIN.username, DEFAULT_ADMIN.password);
}

async function verifyUserLogin(apiBaseUrl: string, username: string, password: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/v1/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }).toString(),
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`[E2E Setup] Login verification failed for ${username}: ${response.status} ${detail}`);
  }

  console.log(`[E2E Setup] Verified login works for ${username}`);
}

async function waitForApi(apiBaseUrl: string): Promise<void> {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(`${apiBaseUrl}/health`);
      if (response.ok) {
        console.log('[E2E Setup] API is ready');
        return;
      }
    } catch {
      // Intentionally ignore and retry.
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  console.warn('[E2E Setup] API did not become ready in time');
}

/**
 * Global setup for E2E tests.
 * This runs once before all tests.
 */
async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:3000';
  const apiBaseUrl = getApiBaseUrl(baseURL);

  console.log(`[E2E Setup] Starting global setup...`);
  console.log(`[E2E Setup] Base URL: ${baseURL}`);
  console.log(`[E2E Setup] API Base URL: ${apiBaseUrl}`);

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

  await waitForApi(apiBaseUrl);
  await ensureSeedUsers(apiBaseUrl);

  await browser.close();
  console.log(`[E2E Setup] Global setup complete`);
}

export default globalSetup;
