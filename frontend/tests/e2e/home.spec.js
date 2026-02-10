// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Home page tests - verify the app loads and shows main UI elements
 */

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication by setting up localStorage before navigating
    await page.addInitScript(() => {
      // Mock auth state to bypass login
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
    });

    // Mock API responses
    await page.route('**/api/conversations', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        });
      } else if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-conv-123',
            created_at: new Date().toISOString(),
            messages: [],
          }),
        });
      } else {
        await route.continue();
      }
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          council_models: ['anthropic/claude-sonnet-4', 'openai/gpt-4o'],
          chairman_model: 'anthropic/claude-sonnet-4',
          available_models: {
            'anthropic/claude-sonnet-4': { name: 'Claude Sonnet 4', input_cost: 0.003, output_cost: 0.015 },
            'openai/gpt-4o': { name: 'GPT-4o', input_cost: 0.005, output_cost: 0.015 },
          },
        }),
      });
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

    await page.goto('/');
  });

  test('should display the app title in sidebar', async ({ page }) => {
    const title = page.locator('.sidebar h1');
    await expect(title).toContainText('LLM Council');
  });

  test('should show sidebar with navigation elements', async ({ page }) => {
    const sidebar = page.locator('.sidebar');
    await expect(sidebar).toBeVisible();

    // Check for new conversation button
    const newChatBtn = page.locator('.new-conversation-btn');
    await expect(newChatBtn).toBeVisible();
    await expect(newChatBtn).toContainText('New Chat');
  });

  test('should show chat interface area', async ({ page }) => {
    const chatArea = page.locator('.chat');
    await expect(chatArea).toBeVisible();
  });

  test('should show empty state when no conversation is selected', async ({ page }) => {
    const emptyState = page.locator('.chat-empty');
    await expect(emptyState).toBeVisible();
    await expect(emptyState).toContainText('LLM Council');
  });

  test('should create new conversation when clicking new chat button', async ({ page }) => {
    const newChatBtn = page.locator('.new-conversation-btn');
    await newChatBtn.click();

    // After creating conversation, should show chat interface
    await expect(page.locator('.chat')).toBeVisible();
  });

  test('should show mode toggle tabs in header', async ({ page }) => {
    // First create a conversation to see the header
    await page.route('**/api/conversations', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-conv-123',
            created_at: new Date().toISOString(),
            messages: [],
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/conversations/new-conv-123', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'new-conv-123',
          created_at: new Date().toISOString(),
          messages: [],
        }),
      });
    });

    const newChatBtn = page.locator('.new-conversation-btn');
    await newChatBtn.click();

    // Wait for chat header to appear
    const chatHeader = page.locator('.chat-header');
    await expect(chatHeader).toBeVisible();

    // Check mode tabs
    const quickTab = page.locator('.mode-tab:has-text("Quick")');
    const councilTab = page.locator('.mode-tab:has-text("Council")');
    const compareTab = page.locator('.mode-tab:has-text("Compare")');

    await expect(quickTab).toBeVisible();
    await expect(councilTab).toBeVisible();
    await expect(compareTab).toBeVisible();
  });

  test('should show search button in sidebar header', async ({ page }) => {
    const searchBtn = page.locator('.sidebar .header-btn[title*="Search"]');
    await expect(searchBtn).toBeVisible();
  });

  test('should show settings button in sidebar header', async ({ page }) => {
    const settingsBtn = page.locator('.sidebar .header-btn[title="Settings"]');
    await expect(settingsBtn).toBeVisible();
  });

  test('should show more menu button in sidebar header', async ({ page }) => {
    const moreMenuBtn = page.locator('.more-menu-container .header-btn');
    await expect(moreMenuBtn).toBeVisible();
  });

  test('should toggle more menu when clicking more button', async ({ page }) => {
    const moreMenuBtn = page.locator('.more-menu-container .header-btn');
    await moreMenuBtn.click();

    const moreMenu = page.locator('.more-menu');
    await expect(moreMenu).toBeVisible();

    // Check menu items
    await expect(moreMenu.locator('text=Projects')).toBeVisible();
    await expect(moreMenu.locator('text=Batch Processing')).toBeVisible();
    await expect(moreMenu.locator('text=Analytics')).toBeVisible();
  });
});
