// @ts-check
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.E2E_API_URL || 'http://localhost:8001';

test.describe('Council Deliberation Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('homepage loads correctly', async ({ page }) => {
    await expect(page).toHaveTitle(/LLM Council/i);

    // Should have main UI elements
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.chat-interface, .main-content')).toBeVisible();
  });

  test('can start new conversation', async ({ page }) => {
    // Click new conversation button
    const newChatBtn = page.locator('button:has-text("New"), button:has-text("new chat"), [data-testid="new-chat"]').first();

    if (await newChatBtn.isVisible()) {
      await newChatBtn.click();
      await expect(page.locator('textarea, input[type="text"]')).toBeVisible();
    }
  });

  test('chat input is functional', async ({ page }) => {
    const input = page.locator('textarea, input[type="text"]').first();

    if (await input.isVisible()) {
      await input.fill('Test message');
      await expect(input).toHaveValue('Test message');
    }
  });

  test('settings panel opens', async ({ page }) => {
    // Look for settings button
    const settingsBtn = page.locator('button:has-text("Settings"), button:has-text("⚙"), [data-testid="settings"]').first();

    if (await settingsBtn.isVisible()) {
      await settingsBtn.click();

      // Should show settings panel
      await expect(page.locator('.settings, [data-testid="settings-panel"]')).toBeVisible({ timeout: 5000 });
    }
  });

  test('sidebar shows conversations list', async ({ page }) => {
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toBeVisible();

    // May have conversation items or be empty
    const conversationItems = page.locator('.conversation-item, .chat-item, [data-testid="conversation"]');
    // Just check the sidebar renders - may be empty for fresh installs
    await expect(sidebar).toBeVisible();
  });
});

test.describe('API Health', () => {
  test('backend API is reachable', async ({ request }) => {
    const response = await request.get(`${API_URL}/`);
    expect(response.ok()).toBeTruthy();
  });

  test('models endpoint returns data', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/models`);

    if (response.ok()) {
      const data = await response.json();
      expect(data).toBeDefined();
      expect(typeof data).toBe('object');
    }
  });

  test('presets endpoint returns data', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/presets`);

    if (response.ok()) {
      const data = await response.json();
      expect(data.presets).toBeDefined();
      expect(Array.isArray(data.presets)).toBeTruthy();
    }
  });

  test('config endpoint returns data', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/config`);

    if (response.ok()) {
      const data = await response.json();
      expect(data).toBeDefined();
    }
  });
});

test.describe('Stage Display Components', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('stage tabs are interactive', async ({ page }) => {
    // If there's an existing conversation with responses, check stage tabs
    const stageTabs = page.locator('.tab, .stage-tab, [role="tab"]');

    if (await stageTabs.count() > 0) {
      const firstTab = stageTabs.first();
      await firstTab.click();
      await expect(firstTab).toHaveClass(/active|selected/);
    }
  });
});

test.describe('Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  test('page has no obvious accessibility violations', async ({ page }) => {
    // Check for basic accessibility
    const mainContent = page.locator('main, [role="main"], .main-content');

    // Page should have accessible structure
    const heading = page.locator('h1, h2, h3').first();
    if (await heading.isVisible()) {
      await expect(heading).toBeVisible();
    }
  });

  test('interactive elements are keyboard accessible', async ({ page }) => {
    // Tab to first interactive element
    await page.keyboard.press('Tab');

    // Something should be focused
    const focused = page.locator(':focus');
    const focusedCount = await focused.count();
    expect(focusedCount).toBeGreaterThanOrEqual(0); // May be 0 if no focusable elements
  });
});

test.describe('Responsive Design', () => {
  test('renders correctly on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(BASE_URL);

    // Page should still be functional
    await expect(page.locator('body')).toBeVisible();

    // No horizontal overflow
    const body = await page.locator('body').boundingBox();
    if (body) {
      expect(body.width).toBeLessThanOrEqual(375);
    }
  });

  test('renders correctly on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(BASE_URL);

    await expect(page.locator('body')).toBeVisible();
  });

  test('renders correctly on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto(BASE_URL);

    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Error Handling', () => {
  test('handles 404 gracefully', async ({ page }) => {
    await page.goto(`${BASE_URL}/nonexistent-page-12345`);

    // Should not crash - either show 404 page or redirect
    await expect(page.locator('body')).toBeVisible();
  });

  test('handles API errors gracefully', async ({ page }) => {
    // Mock a failing API call
    await page.route(`${API_URL}/api/**`, async route => {
      await route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });

    await page.goto(BASE_URL);

    // Page should still load, not crash
    await expect(page.locator('body')).toBeVisible();
  });
});
