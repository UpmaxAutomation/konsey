// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Settings panel tests - verify settings modal functionality
 */

test.describe('Settings Panel', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
      localStorage.setItem('theme', 'light');
    });

    // Mock API responses
    await page.route('**/api/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.route('**/api/budget/alerts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ alerts: [], exceeded: false, exceeded_periods: [] }),
      });
    });

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'test-user', email: 'test@example.com' }),
      });
    });

    await page.route('**/api/config', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            council_models: ['anthropic/claude-sonnet-4', 'openai/gpt-4o'],
            chairman_model: 'anthropic/claude-sonnet-4',
            available_models: {
              'anthropic/claude-sonnet-4': { name: 'Claude Sonnet 4', input_cost: 0.003, output_cost: 0.015 },
              'openai/gpt-4o': { name: 'GPT-4o', input_cost: 0.005, output_cost: 0.015 },
              'google/gemini-2.5-pro': { name: 'Gemini 2.5 Pro', input_cost: 0.002, output_cost: 0.010 },
              'deepseek/deepseek-r1:free': { name: 'DeepSeek R1', input_cost: 0, output_cost: 0 },
            },
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/features', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ memory: true, web_search: true, code_execution: true }),
      });
    });

    await page.route('**/api/folders', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ folders: [] }),
      });
    });

    await page.route('**/api/tags', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tags: [] }),
      });
    });

    await page.route('**/api/keys', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ api_keys: {} }),
      });
    });

    await page.route('**/api/presets', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          presets: [
            { id: 'code_review', name: 'Code Review', description: 'Expert code reviewers' },
            { id: 'research', name: 'Research', description: 'Deep research and analysis' },
            { id: 'creative', name: 'Creative', description: 'Creative writing and brainstorming' },
          ],
        }),
      });
    });

    await page.goto('/');
  });

  test('should open settings modal when clicking settings button', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    const settingsModal = page.locator('.settings-modal');
    await expect(settingsModal).toBeVisible();
  });

  test('should display settings tabs', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    const settingsModal = page.locator('.settings-modal');
    await expect(settingsModal).toBeVisible();

    // Check for tabs
    await expect(page.locator('.settings-tab:has-text("API Routing")')).toBeVisible();
    await expect(page.locator('.settings-tab:has-text("Council Models")')).toBeVisible();
    await expect(page.locator('.settings-tab:has-text("Teams")')).toBeVisible();
    await expect(page.locator('.settings-tab:has-text("API Keys")')).toBeVisible();
    await expect(page.locator('.settings-tab:has-text("Analytics")')).toBeVisible();
    await expect(page.locator('.settings-tab:has-text("Theme")')).toBeVisible();
  });

  test('should switch between tabs', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    // Click on Council Models tab
    await page.locator('.settings-tab:has-text("Council Models")').click();

    // Should show model list
    await expect(page.locator('.models-list')).toBeVisible();
  });

  test('should show model list in Council Models tab', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    await page.locator('.settings-tab:has-text("Council Models")').click();

    // Should show available models
    const modelsList = page.locator('.models-list');
    await expect(modelsList).toBeVisible();

    // Check for model cards
    await expect(page.locator('.model-card')).toHaveCount(4); // Based on mocked data
  });

  test('should show presets dropdown in Council Models tab', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    await page.locator('.settings-tab:has-text("Council Models")').click();

    // Should show presets section
    const presetsSelect = page.locator('.preset-select');
    await expect(presetsSelect).toBeVisible();
  });

  test('should show theme toggle in Appearance tab', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    await page.locator('.settings-tab:has-text("Theme")').click();

    // Should show theme preview cards
    await expect(page.locator('.theme-preview')).toBeVisible();
    await expect(page.locator('.preview-card')).toHaveCount(2); // Light and Dark
  });

  test('should close settings when clicking close button', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    const settingsModal = page.locator('.settings-modal');
    await expect(settingsModal).toBeVisible();

    // Click close button
    const closeBtn = page.locator('.settings-modal .close-btn');
    await closeBtn.click();

    await expect(settingsModal).not.toBeVisible();
  });

  test('should close settings when clicking cancel button', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    const settingsModal = page.locator('.settings-modal');
    await expect(settingsModal).toBeVisible();

    // Click cancel button
    const cancelBtn = page.locator('.settings-footer .cancel-btn');
    await cancelBtn.click();

    await expect(settingsModal).not.toBeVisible();
  });

  test('should close settings when clicking overlay', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    const settingsModal = page.locator('.settings-modal');
    await expect(settingsModal).toBeVisible();

    // Click on overlay (outside the modal)
    await page.locator('.settings-overlay').click({ position: { x: 10, y: 10 } });

    await expect(settingsModal).not.toBeVisible();
  });

  test('should filter models by search', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    await page.locator('.settings-tab:has-text("Council Models")').click();

    // Type in search
    const searchInput = page.locator('.models-search input');
    await searchInput.fill('claude');

    // Should filter to only Claude models
    const modelCards = page.locator('.model-card');
    await expect(modelCards).toHaveCount(1);
    await expect(modelCards.first()).toContainText('Claude');
  });

  test('should filter models by provider', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    await page.locator('.settings-tab:has-text("Council Models")').click();

    // Click on Free filter
    await page.locator('.filter-chip:has-text("Free")').click();

    // Should show only free models
    const modelCards = page.locator('.model-card');
    await expect(modelCards).toHaveCount(1);
  });

  test('should select and deselect models', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    await page.locator('.settings-tab:has-text("Council Models")').click();

    // Click on a model card to toggle selection
    const modelCard = page.locator('.model-card').first();
    const wasSelected = await modelCard.evaluate(el => el.classList.contains('selected'));

    await modelCard.click();

    // Selection state should change
    const isNowSelected = await modelCard.evaluate(el => el.classList.contains('selected'));
    expect(isNowSelected).not.toBe(wasSelected);
  });

  test('should show save button in footer', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await settingsBtn.click();

    const saveBtn = page.locator('.settings-footer .save-btn');
    await expect(saveBtn).toBeVisible();
    await expect(saveBtn).toContainText('Save');
  });
});

test.describe('Theme Toggle via More Menu', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
      localStorage.setItem('theme', 'light');
    });

    // Basic API mocks
    await page.route('**/api/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/conversations')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      } else if (url.includes('/budget')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ alerts: [], exceeded: false }) });
      } else if (url.includes('/auth')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'test-user' }) });
      } else if (url.includes('/config')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ council_models: [], chairman_model: '', available_models: {} }) });
      } else if (url.includes('/features')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ memory: true }) });
      } else if (url.includes('/folders')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ folders: [] }) });
      } else if (url.includes('/tags')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tags: [] }) });
      } else {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) });
      }
    });

    await page.goto('/');
  });

  test('should toggle theme via more menu', async ({ page }) => {
    // Open more menu
    const moreMenuBtn = page.locator('.more-menu-container .header-btn');
    await moreMenuBtn.click();

    // Check initial theme (light)
    const themeBtn = page.locator('.more-menu button:has-text("Dark Mode")');
    await expect(themeBtn).toBeVisible();

    // Click to switch to dark mode
    await themeBtn.click();

    // Verify theme changed
    const htmlTheme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    expect(htmlTheme).toBe('dark');
  });
});
