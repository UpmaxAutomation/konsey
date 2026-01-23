// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Conversation flow tests - create, interact with, and delete conversations
 */

test.describe('Conversation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
    });

    // Track conversation state for mocking
    let conversations = [];

    // Mock API responses
    await page.route('**/api/conversations', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(conversations),
        });
      } else if (route.request().method() === 'POST') {
        const newConv = {
          id: `conv-${Date.now()}`,
          created_at: new Date().toISOString(),
          message_count: 0,
          title: 'New Conversation',
          messages: [],
        };
        conversations.push(newConv);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(newConv),
        });
      } else {
        await route.continue();
      }
    });

    await page.route('**/api/conversations/*', async (route) => {
      const url = route.request().url();
      const convIdMatch = url.match(/\/conversations\/([^/]+)$/);

      if (route.request().method() === 'GET' && convIdMatch) {
        const convId = convIdMatch[1];
        const conv = conversations.find(c => c.id === convId);
        if (conv) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(conv),
          });
        } else {
          await route.fulfill({
            status: 404,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Not found' }),
          });
        }
      } else if (route.request().method() === 'DELETE' && convIdMatch) {
        const convId = convIdMatch[1];
        conversations = conversations.filter(c => c.id !== convId);
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
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
          council_models: ['anthropic/claude-sonnet-4'],
          chairman_model: 'anthropic/claude-sonnet-4',
          available_models: {
            'anthropic/claude-sonnet-4': { name: 'Claude Sonnet 4', input_cost: 0.003, output_cost: 0.015 },
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

  test('should create new conversation', async ({ page }) => {
    const newChatBtn = page.locator('.new-conversation-btn');
    await newChatBtn.click();

    // Should show conversation in sidebar after creation
    await expect(page.locator('.conversation-item')).toBeVisible();
  });

  test('should show message input when conversation is active', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Wait for chat interface
    const textarea = page.locator('.chat-input textarea');
    await expect(textarea).toBeVisible();
  });

  test('should type message in input', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Type message
    const textarea = page.locator('.chat-input textarea');
    await textarea.fill('Hello, this is a test message');

    await expect(textarea).toHaveValue('Hello, this is a test message');
  });

  test('should show send button', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    const sendBtn = page.locator('.chat-input .send-btn');
    await expect(sendBtn).toBeVisible();
  });

  test('should send message when clicking send button', async ({ page }) => {
    // Create conversation first
    await page.locator('.new-conversation-btn').click();

    // Wait for textarea
    const textarea = page.locator('.chat-input textarea');
    await expect(textarea).toBeVisible();

    // Mock the message endpoint for quick mode
    await page.route('**/api/conversations/*/quick**', async (route) => {
      // Return a streaming response simulation
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data: {"type":"chunk","data":"Hello"}\n\ndata: {"type":"complete"}\n\n`,
      });
    });

    // Type and send message
    await textarea.fill('Test message');

    const sendBtn = page.locator('.chat-input .send-btn');
    await sendBtn.click();

    // Message should appear in conversation (user message shows immediately)
    await expect(page.locator('.message.user')).toBeVisible();
  });

  test('should send message on Enter key', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    const textarea = page.locator('.chat-input textarea');
    await textarea.fill('Test message');

    // Mock message endpoint
    await page.route('**/api/conversations/*/quick**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `data: {"type":"chunk","data":"Response"}\n\ndata: {"type":"complete"}\n\n`,
      });
    });

    // Press Enter to send
    await textarea.press('Enter');

    // Should show user message
    await expect(page.locator('.message.user')).toBeVisible();
  });

  test('should not send on Shift+Enter (new line)', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    const textarea = page.locator('.chat-input textarea');
    await textarea.fill('Line 1');

    // Press Shift+Enter for new line
    await textarea.press('Shift+Enter');
    await textarea.type('Line 2');

    // Message should not be sent, textarea should have both lines
    const value = await textarea.inputValue();
    expect(value).toContain('Line 1');
    expect(value).toContain('Line 2');
  });

  test('should show conversation in sidebar', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Should appear in sidebar
    const conversationItem = page.locator('.conversation-item');
    await expect(conversationItem).toBeVisible();
  });

  test('should select conversation from sidebar', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Click on conversation in sidebar
    const conversationItem = page.locator('.conversation-item').first();
    await conversationItem.click();

    // Should be selected (active)
    await expect(conversationItem).toHaveClass(/active/);
  });

  test('should delete conversation', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    const conversationItem = page.locator('.conversation-item').first();
    await expect(conversationItem).toBeVisible();

    // Accept the confirmation dialog
    page.on('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Click delete button
    const deleteBtn = conversationItem.locator('.delete-conversation-btn');
    await deleteBtn.click();

    // Conversation should be removed
    await expect(page.locator('.conversation-item')).toHaveCount(0);
  });

  test('should show delete confirmation', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    const conversationItem = page.locator('.conversation-item').first();

    // Track if dialog appears
    let dialogShown = false;
    page.on('dialog', async (dialog) => {
      dialogShown = true;
      expect(dialog.message()).toContain('Delete');
      await dialog.dismiss(); // Cancel deletion
    });

    // Click delete button
    const deleteBtn = conversationItem.locator('.delete-conversation-btn');
    await deleteBtn.click();

    expect(dialogShown).toBe(true);
  });

  test('should switch between modes', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Wait for mode tabs
    const councilTab = page.locator('.mode-tab:has-text("Council")');
    await expect(councilTab).toBeVisible();

    // Click Council mode
    await councilTab.click();

    // Council tab should be active
    await expect(councilTab).toHaveClass(/active/);

    // Click Compare mode
    const compareTab = page.locator('.mode-tab:has-text("Compare")');
    await compareTab.click();
    await expect(compareTab).toHaveClass(/active/);

    // Click Quick mode
    const quickTab = page.locator('.mode-tab:has-text("Quick")');
    await quickTab.click();
    await expect(quickTab).toHaveClass(/active/);
  });

  test('should show example prompts in empty conversation', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Should show welcome with example prompts
    const promptsGrid = page.locator('.prompts-grid');
    await expect(promptsGrid).toBeVisible();

    // Should have prompt buttons
    const promptBtns = page.locator('.prompt-btn');
    const count = await promptBtns.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should fill input when clicking example prompt', async ({ page }) => {
    // Create conversation
    await page.locator('.new-conversation-btn').click();

    // Click an example prompt
    const promptBtn = page.locator('.prompt-btn').first();
    const promptText = await promptBtn.textContent();

    await promptBtn.click();

    // Input should be filled with prompt text (minus the icon)
    const textarea = page.locator('.chat-input textarea');
    const inputValue = await textarea.inputValue();
    expect(promptText?.trim()).toContain(inputValue.trim());
  });
});

test.describe('Conversation with Messages', () => {
  test('should display existing messages', async ({ page }) => {
    // Mock authentication
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
    });

    const existingConversation = {
      id: 'existing-conv-1',
      created_at: new Date().toISOString(),
      message_count: 2,
      title: 'Test Conversation',
      messages: [
        { role: 'user', content: 'Hello, how are you?' },
        { role: 'assistant', content: 'I am doing well, thank you for asking!' },
      ],
    };

    // Mock APIs
    await page.route('**/api/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: existingConversation.id, created_at: existingConversation.created_at, message_count: 2, title: 'Test Conversation' },
        ]),
      });
    });

    await page.route('**/api/conversations/existing-conv-1', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(existingConversation),
      });
    });

    await page.route('**/api/budget/alerts', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ alerts: [] }) });
    });

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'test-user' }) });
    });

    await page.route('**/api/config', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ council_models: [], chairman_model: '', available_models: {} }),
      });
    });

    await page.route('**/api/features', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ memory: true }) });
    });

    await page.route('**/api/folders', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ folders: [] }) });
    });

    await page.route('**/api/tags', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tags: [] }) });
    });

    await page.goto('/');

    // Click on existing conversation
    const conversationItem = page.locator('.conversation-item').first();
    await conversationItem.click();

    // Should show messages
    await expect(page.locator('.message.user')).toBeVisible();
    await expect(page.locator('.message.assistant')).toBeVisible();

    // Check content
    await expect(page.locator('.message.user')).toContainText('Hello, how are you?');
    await expect(page.locator('.message.assistant')).toContainText('I am doing well');
  });
});

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('auth_token', 'test-token');
      localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
    });

    await page.route('**/api/**', async (route) => {
      const url = route.request().url();
      if (url.includes('/conversations') && route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ id: `conv-${Date.now()}`, created_at: new Date().toISOString(), messages: [] }),
        });
      } else if (url.includes('/conversations')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      } else if (url.includes('/budget')) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ alerts: [] }) });
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

  test('should open search modal with Cmd+K', async ({ page }) => {
    // Press Cmd+K (Mac) or Ctrl+K (Windows)
    await page.keyboard.press('Control+k');

    // Search modal should appear
    const searchModal = page.locator('.search-modal');
    await expect(searchModal).toBeVisible();
  });

  test('should create new conversation with Cmd+N', async ({ page }) => {
    // Press Cmd+N (Mac) or Ctrl+N (Windows)
    await page.keyboard.press('Control+n');

    // New conversation should be created
    await expect(page.locator('.conversation-item')).toBeVisible();
  });
});
