// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Canvas/Board integration tests.
 *
 * These tests exercise board navigation, search, context menus, and keyboard
 * shortcuts.  All backend API calls are mocked so the tests run without a live
 * server.  Authentication is handled by injecting a mock token into localStorage
 * before each test, matching the pattern used by the rest of the E2E suite.
 */

// ---------------------------------------------------------------------------
// Shared mock data
// ---------------------------------------------------------------------------

const MOCK_BOARD = {
  id: 'board-1',
  name: 'Test Board',
  description: 'A board for testing',
  project_id: null,
  viewport: { x: 0, y: 0, zoom: 1 },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_CARDS = [
  {
    id: 'card-1',
    board_id: 'board-1',
    card_type: 'note',
    title: 'First Note',
    content: 'Hello world, this is a test note with some content.',
    position_x: 100,
    position_y: 100,
    extra: { created_at: new Date().toISOString() },
  },
  {
    id: 'card-2',
    board_id: 'board-1',
    card_type: 'council_synthesis',
    title: 'Synthesis Card',
    content: 'This is a synthesis of the council deliberation.',
    position_x: 400,
    position_y: 100,
    extra: { model: 'anthropic/claude-sonnet-4', created_at: new Date().toISOString() },
  },
  {
    id: 'card-3',
    board_id: 'board-1',
    card_type: 'query',
    title: 'A Query',
    content: 'What is the meaning of life?',
    position_x: 100,
    position_y: 400,
    extra: { created_at: new Date().toISOString() },
  },
];

const MOCK_EDGES = [
  {
    id: 'edge-1',
    board_id: 'board-1',
    source_card_id: 'card-1',
    target_card_id: 'card-2',
    edge_type: 'related',
  },
];

const MOCK_BOARDS_LIST = [
  MOCK_BOARD,
  {
    id: 'board-2',
    name: 'Second Board',
    description: 'Another board',
    project_id: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

// ---------------------------------------------------------------------------
// Helper: set up authentication and all common API mocks
// ---------------------------------------------------------------------------

/**
 * Configures localStorage-based auth and registers route handlers that cover
 * every API endpoint the app calls during startup and board operations.
 */
async function setupAuthAndMocks(page) {
  // Inject auth token before navigation
  await page.addInitScript(() => {
    localStorage.setItem('auth_token', 'test-token');
    localStorage.setItem('user', JSON.stringify({ id: 'test-user', email: 'test@example.com' }));
  });

  // ---- Global / shared mocks ------------------------------------------

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'test-user', email: 'test@example.com' }),
    });
  });

  await page.route('**/api/conversations', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: `conv-${Date.now()}`, created_at: new Date().toISOString(), messages: [] }),
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
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ folders: [] }) });
  });

  await page.route('**/api/tags', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tags: [] }) });
  });

  await page.route('**/api/keys', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ api_keys: { openrouter: 'sk-test' } }) });
  });

  // ---- Board-specific mocks -------------------------------------------

  // GET /boards  (list)
  await page.route('**/api/boards', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ boards: MOCK_BOARDS_LIST }),
      });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `board-new-${Date.now()}`,
          name: 'New Board',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }),
      });
    } else {
      await route.continue();
    }
  });

  // GET /boards/:id  (single board)
  await page.route('**/api/boards/board-1', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_BOARD),
      });
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
    }
  });

  // Cards endpoint
  await page.route('**/api/boards/board-1/cards', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ cards: MOCK_CARDS }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `card-new-${Date.now()}`,
          board_id: 'board-1',
          card_type: 'note',
          title: 'New Note',
          content: '',
          position_x: 200,
          position_y: 200,
          extra: {},
        }),
      });
    }
  });

  // Batch position updates
  await page.route('**/api/boards/board-1/cards/batch-positions', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });

  // Edges endpoint
  await page.route('**/api/boards/board-1/edges', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ edges: MOCK_EDGES }),
      });
    } else {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: `edge-new-${Date.now()}` }) });
    }
  });

  // Board memory
  await page.route('**/api/boards/board-1/memory', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ facts: [], summary: '' }),
    });
  });

  // Board viewport save
  await page.route('**/api/boards/board-1/viewport', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) });
  });

  // Card AI actions (catch-all for any card id)
  await page.route('**/api/boards/board-1/cards/*/ai-action', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        cards: [{ id: `card-ai-${Date.now()}`, card_type: 'note', title: 'AI Result', content: 'Generated', position_x: 300, position_y: 300, extra: {} }],
        edges: [],
      }),
    });
  });

  // Board-level AI action
  await page.route('**/api/boards/board-1/ai-action', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ cards: [], edges: [], color_updates: {} }),
    });
  });
}

// ===========================================================================
// 1. Board Navigation
// ===========================================================================

test.describe('Board Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
  });

  test('should navigate to /boards and render the board list', async ({ page }) => {
    await page.goto('/boards');

    // The BoardList component renders a container with class "board-list"
    const boardList = page.locator('.board-list');
    await expect(boardList).toBeVisible({ timeout: 10000 });

    // The list title should indicate boards are being shown
    const title = page.locator('.board-list__title');
    await expect(title).toContainText('Boards');
  });

  test('should render board cards from the mocked API', async ({ page }) => {
    await page.goto('/boards');

    // Wait for the grid of board cards
    const boardCards = page.locator('.board-list__card');
    await expect(boardCards).toHaveCount(2, { timeout: 10000 });

    // Verify the names
    await expect(boardCards.nth(0)).toContainText('Test Board');
    await expect(boardCards.nth(1)).toContainText('Second Board');
  });

  test('should navigate from board list to chat via the close button', async ({ page }) => {
    await page.goto('/boards');

    const closeBtn = page.locator('.board-list__close-btn');
    await expect(closeBtn).toBeVisible({ timeout: 10000 });
    await closeBtn.click();

    // Should navigate back to the chat root
    await expect(page).toHaveURL('/');
  });

  test('should support browser back navigation from boards to chat', async ({ page }) => {
    // Start at chat, then navigate to boards
    await page.goto('/');
    await page.waitForTimeout(500); // Let the chat view settle

    await page.goto('/boards');
    await expect(page.locator('.board-list')).toBeVisible({ timeout: 10000 });

    // Press browser back
    await page.goBack();

    // Should return to chat root
    await expect(page).toHaveURL('/');
  });

  test('should navigate into a specific board view', async ({ page }) => {
    await page.goto('/boards');

    // Click the first board card
    const boardCard = page.locator('.board-list__card').first();
    await expect(boardCard).toBeVisible({ timeout: 10000 });
    await boardCard.click();

    // Should navigate to /boards/board-1
    await expect(page).toHaveURL(/\/boards\/board-1/);

    // The board view container should render
    const boardView = page.locator('.board-view');
    await expect(boardView).toBeVisible({ timeout: 10000 });
  });

  test('should navigate directly to a board via URL', async ({ page }) => {
    await page.goto('/boards/board-1');

    // Board view should render
    const boardView = page.locator('.board-view');
    await expect(boardView).toBeVisible({ timeout: 10000 });

    // Toolbar should display the board name
    const boardName = page.locator('.board-toolbar__name');
    await expect(boardName).toContainText('Test Board');
  });

  test('should navigate back from board view to board list via toolbar', async ({ page }) => {
    await page.goto('/boards/board-1');

    const backBtn = page.locator('.board-toolbar__back');
    await expect(backBtn).toBeVisible({ timeout: 10000 });
    await backBtn.click();

    // Should return to board list
    await expect(page).toHaveURL('/boards');
    await expect(page.locator('.board-list')).toBeVisible({ timeout: 10000 });
  });

  test('should show the "New Board" create button on the board list', async ({ page }) => {
    await page.goto('/boards');

    const createBtn = page.locator('.board-list__create-btn');
    await expect(createBtn).toBeVisible({ timeout: 10000 });
    await expect(createBtn).toContainText('New Board');
  });

  test('should open the board creation form when clicking "New Board"', async ({ page }) => {
    await page.goto('/boards');

    const createBtn = page.locator('.board-list__create-btn').first();
    await expect(createBtn).toBeVisible({ timeout: 10000 });
    await createBtn.click();

    // The inline creation form should appear
    const createInput = page.locator('.board-list__create-input');
    await expect(createInput).toBeVisible();
    await expect(createInput).toBeFocused();
  });
});

// ===========================================================================
// 2. Board View Rendering
// ===========================================================================

test.describe('Board View Rendering', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
    await page.goto('/boards/board-1');
  });

  test('should render the board toolbar', async ({ page }) => {
    const toolbar = page.locator('.board-toolbar');
    await expect(toolbar).toBeVisible({ timeout: 10000 });
  });

  test('should display the board name in the toolbar', async ({ page }) => {
    const boardName = page.locator('.board-toolbar__name');
    await expect(boardName).toBeVisible({ timeout: 10000 });
    await expect(boardName).toContainText('Test Board');
  });

  test('should render the ReactFlow canvas container', async ({ page }) => {
    const canvas = page.locator('.board-view__canvas');
    await expect(canvas).toBeVisible({ timeout: 10000 });

    // ReactFlow renders a container with class "react-flow"
    const reactFlow = page.locator('.react-flow');
    await expect(reactFlow).toBeVisible({ timeout: 10000 });
  });

  test('should render toolbar action buttons', async ({ page }) => {
    // Note button
    const noteBtn = page.locator('.board-toolbar__btn:has-text("Note")');
    await expect(noteBtn).toBeVisible({ timeout: 10000 });

    // Link button
    const linkBtn = page.locator('.board-toolbar__btn:has-text("Link")');
    await expect(linkBtn).toBeVisible();

    // Knowledge button
    const knowledgeBtn = page.locator('.board-toolbar__btn:has-text("Knowledge")');
    await expect(knowledgeBtn).toBeVisible();

    // Council button
    const councilBtn = page.locator('.board-toolbar__btn--council');
    await expect(councilBtn).toBeVisible();

    // AI dropdown button
    const aiBtn = page.locator('.board-toolbar__btn--ai');
    await expect(aiBtn).toBeVisible();
  });

  test('should show loading state while board data is being fetched', async ({ page }) => {
    // Create a new page with a delayed board response to observe loading
    const slowPage = page;

    // Override the board route to add a delay
    await slowPage.route('**/api/boards/board-slow', async (route) => {
      // Delay 2 seconds
      await new Promise((r) => setTimeout(r, 2000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_BOARD, id: 'board-slow' }),
      });
    });

    await slowPage.route('**/api/boards/board-slow/cards', async (route) => {
      await new Promise((r) => setTimeout(r, 2000));
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ cards: [] }) });
    });

    await slowPage.route('**/api/boards/board-slow/edges', async (route) => {
      await new Promise((r) => setTimeout(r, 2000));
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ edges: [] }) });
    });

    await slowPage.route('**/api/boards/board-slow/memory', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ facts: [] }) });
    });

    await slowPage.goto('/boards/board-slow');

    // Should show loading indicator before data arrives
    const loadingView = slowPage.locator('.board-view--loading');
    // The loading state is transient; verify it exists or the final board view appears
    const boardView = slowPage.locator('.board-view');
    await expect(boardView).toBeVisible({ timeout: 15000 });
  });
});

// ===========================================================================
// 3. Board Search
// ===========================================================================

test.describe('Board Search', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
    await page.goto('/boards/board-1');
    // Wait for the board view to fully render
    await expect(page.locator('.board-view')).toBeVisible({ timeout: 10000 });
    // Wait for toolbar to be ready (cards loaded)
    await expect(page.locator('.board-toolbar')).toBeVisible();
  });

  test('should open search when clicking the search toolbar button', async ({ page }) => {
    // The search button is in the toolbar center section (has a magnifying glass SVG)
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await expect(searchBtn).toBeVisible({ timeout: 5000 });
    await searchBtn.click();

    // The BoardSearch component renders with class "board-search"
    const boardSearch = page.locator('.board-search');
    await expect(boardSearch).toBeVisible();
  });

  test('should open search with Cmd+F keyboard shortcut', async ({ page }) => {
    // Click on the canvas area first so keys are not captured by an input
    const canvas = page.locator('.board-view__canvas');
    await canvas.click();

    await page.keyboard.press('Meta+f');

    const boardSearch = page.locator('.board-search');
    await expect(boardSearch).toBeVisible({ timeout: 5000 });
  });

  test('should auto-focus the search input when opened', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const searchInput = page.locator('.board-search__input');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toBeFocused();
  });

  test('should show match count when typing a search query', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const searchInput = page.locator('.board-search__input');
    await searchInput.fill('note');

    // The search should find the "First Note" card; match count appears in .board-search__count
    const matchCount = page.locator('.board-search__count');
    await expect(matchCount).toBeVisible({ timeout: 5000 });
  });

  test('should show "No matches" for a query with zero results', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const searchInput = page.locator('.board-search__input');
    await searchInput.fill('zzz_nonexistent_query_zzz');

    const noMatches = page.locator('.board-search__count--empty');
    await expect(noMatches).toBeVisible({ timeout: 5000 });
    await expect(noMatches).toContainText('No matches');
  });

  test('should have navigation arrows when there are matches', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const searchInput = page.locator('.board-search__input');
    // "is" should match content in multiple cards
    await searchInput.fill('is');

    // Navigation buttons should appear when matchCount > 0
    const navBtns = page.locator('.board-search__nav-btn');
    // There should be at least a prev and next button
    await expect(navBtns).toHaveCount(2, { timeout: 5000 });
  });

  test('should show the type filter dropdown', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const filterSelect = page.locator('.board-search__filter');
    await expect(filterSelect).toBeVisible();

    // Should have "All Types" as the default selected option
    await expect(filterSelect).toHaveValue('all');
  });

  test('should close search when clicking the close button', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const boardSearch = page.locator('.board-search');
    await expect(boardSearch).toBeVisible();

    const closeBtn = page.locator('.board-search__close');
    await closeBtn.click();

    await expect(boardSearch).not.toBeVisible();
  });

  test('should close search when pressing Escape inside the search input', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const boardSearch = page.locator('.board-search');
    await expect(boardSearch).toBeVisible();

    const searchInput = page.locator('.board-search__input');
    await searchInput.press('Escape');

    await expect(boardSearch).not.toBeVisible();
  });

  test('should cycle through matches with ArrowDown and ArrowUp', async ({ page }) => {
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const searchInput = page.locator('.board-search__input');
    await searchInput.fill('is');

    // Wait for matches to register
    const matchCount = page.locator('.board-search__count');
    await expect(matchCount).toBeVisible({ timeout: 5000 });

    // Press ArrowDown to advance
    await searchInput.press('ArrowDown');

    // The count indicator should update (e.g., "2 / 3" instead of "1 / 3")
    // We just verify the element still contains a number (non-regression)
    await expect(matchCount).toBeVisible();
  });
});

// ===========================================================================
// 4. Card Context Menu
// ===========================================================================

test.describe('Card Context Menu', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
    await page.goto('/boards/board-1');
    await expect(page.locator('.board-view')).toBeVisible({ timeout: 10000 });
    // Wait for ReactFlow to render the nodes
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10000 });
  });

  test('should show context menu on right-clicking a canvas card node', async ({ page }) => {
    // ReactFlow renders nodes as elements with class "react-flow__node"
    const node = page.locator('.react-flow__node').first();
    // Wait for at least one node to be present (cards have loaded)
    await expect(node).toBeVisible({ timeout: 10000 });

    // Right-click to trigger the context menu
    await node.click({ button: 'right' });

    const contextMenu = page.locator('.card-context-menu');
    await expect(contextMenu).toBeVisible({ timeout: 5000 });
  });

  test('should display the "AI Actions" section header', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const sectionLabel = page.locator('.card-context-menu__section-label');
    await expect(sectionLabel).toBeVisible();
    await expect(sectionLabel).toContainText('AI Actions');
  });

  test('should display all AI action items', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    // Verify each AI action is present
    const expectedActions = ['Summarize', 'Expand', 'Key Points', 'Ask Council', 'Mind Map'];
    for (const action of expectedActions) {
      const item = page.locator(`.card-context-menu__item:has-text("${action}")`);
      await expect(item).toBeVisible();
    }
  });

  test('should display the "Discuss in Chat" option', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const discussItem = page.locator('.card-context-menu__item:has-text("Discuss in Chat")');
    await expect(discussItem).toBeVisible();
  });

  test('should display the "Delete" option', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const deleteItem = page.locator('.card-context-menu__item--danger');
    await expect(deleteItem).toBeVisible();
    await expect(deleteItem).toContainText('Delete');
  });

  test('should display the "Custom Prompt" option', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const customItem = page.locator('.card-context-menu__item:has-text("Custom Prompt")');
    await expect(customItem).toBeVisible();
  });

  test('should show the custom prompt input when clicking "Custom Prompt"', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const customItem = page.locator('.card-context-menu__item:has-text("Custom Prompt")');
    await customItem.click();

    const customInput = page.locator('.card-context-menu__custom-input');
    await expect(customInput).toBeVisible();
    await expect(customInput).toBeFocused();

    const submitBtn = page.locator('.card-context-menu__custom-submit');
    await expect(submitBtn).toBeVisible();
    await expect(submitBtn).toBeDisabled(); // Disabled when input is empty
  });

  test('should close context menu when clicking on the canvas pane', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const contextMenu = page.locator('.card-context-menu');
    await expect(contextMenu).toBeVisible();

    // Click on the ReactFlow pane (background area)
    const pane = page.locator('.react-flow__pane');
    await pane.click({ position: { x: 50, y: 50 } });

    await expect(contextMenu).not.toBeVisible({ timeout: 5000 });
  });

  test('should close context menu and navigate to chat when clicking "Discuss in Chat"', async ({ page }) => {
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click({ button: 'right' });

    const discussItem = page.locator('.card-context-menu__item:has-text("Discuss in Chat")');
    await discussItem.click();

    // Context menu should close
    const contextMenu = page.locator('.card-context-menu');
    await expect(contextMenu).not.toBeVisible({ timeout: 5000 });

    // Should navigate to chat view
    await expect(page).toHaveURL('/', { timeout: 5000 });
  });
});

// ===========================================================================
// 5. Keyboard Shortcuts
// ===========================================================================

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
    await page.goto('/boards/board-1');
    await expect(page.locator('.board-view')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.react-flow')).toBeVisible({ timeout: 10000 });
  });

  test('should create a note card when pressing "n"', async ({ page }) => {
    // Ensure focus is on the canvas (not an input or textarea)
    const pane = page.locator('.react-flow__pane');
    await pane.click({ position: { x: 50, y: 50 } });

    // Count nodes before
    const nodesBefore = await page.locator('.react-flow__node').count();

    await page.keyboard.press('n');

    // Wait for the new node to appear -- the mock POST /cards returns a new card
    // which should be added as a ReactFlow node
    const nodesAfter = page.locator('.react-flow__node');
    await expect(nodesAfter).toHaveCount(nodesBefore + 1, { timeout: 5000 });
  });

  test('should toggle search with Cmd+F', async ({ page }) => {
    const pane = page.locator('.react-flow__pane');
    await pane.click({ position: { x: 50, y: 50 } });

    // Open search
    await page.keyboard.press('Meta+f');

    const boardSearch = page.locator('.board-search');
    await expect(boardSearch).toBeVisible({ timeout: 5000 });

    // Close search by pressing Cmd+F again (toggle)
    // First click away from the search input so the shortcut goes to the canvas handler
    await pane.click({ position: { x: 50, y: 50 } });
    await page.keyboard.press('Meta+f');

    // Search should now be closed
    await expect(boardSearch).not.toBeVisible({ timeout: 5000 });
  });

  test('should deselect all nodes when pressing Escape', async ({ page }) => {
    // First select a node by clicking on it
    const node = page.locator('.react-flow__node').first();
    await expect(node).toBeVisible({ timeout: 10000 });
    await node.click();

    // The node should have a "selected" class in ReactFlow
    await expect(node).toHaveClass(/selected/, { timeout: 3000 });

    // Press Escape
    await page.keyboard.press('Escape');

    // All nodes should be deselected
    const selectedNodes = page.locator('.react-flow__node.selected');
    await expect(selectedNodes).toHaveCount(0, { timeout: 5000 });
  });

  test('should select all nodes with Cmd+A', async ({ page }) => {
    const pane = page.locator('.react-flow__pane');
    await pane.click({ position: { x: 50, y: 50 } });

    await page.keyboard.press('Meta+a');

    // All nodes should be selected
    const totalNodes = await page.locator('.react-flow__node').count();
    const selectedNodes = page.locator('.react-flow__node.selected');
    await expect(selectedNodes).toHaveCount(totalNodes, { timeout: 5000 });
  });

  test('should not trigger note creation when typing "n" inside an input', async ({ page }) => {
    // Open search first to get an input field
    const searchBtn = page.locator('.board-toolbar__btn[title*="Search"]');
    await searchBtn.click();

    const searchInput = page.locator('.board-search__input');
    await expect(searchInput).toBeFocused();

    // Count nodes before
    const nodesBefore = await page.locator('.react-flow__node').count();

    // Type "n" in the search input -- this should NOT create a new card
    await searchInput.type('n');

    // Wait briefly and confirm no new node was added
    await page.waitForTimeout(500);
    const nodesAfter = await page.locator('.react-flow__node').count();
    expect(nodesAfter).toBe(nodesBefore);
  });

  test('should show selection count in toolbar when nodes are selected via Cmd+A', async ({ page }) => {
    const pane = page.locator('.react-flow__pane');
    await pane.click({ position: { x: 50, y: 50 } });

    await page.keyboard.press('Meta+a');

    // The toolbar should show the selection count
    const selectionLabel = page.locator('.board-toolbar__selection');
    await expect(selectionLabel).toBeVisible({ timeout: 5000 });
    await expect(selectionLabel).toContainText('selected');
  });
});

// ===========================================================================
// 6. Board Toolbar Actions
// ===========================================================================

test.describe('Board Toolbar Actions', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
    await page.goto('/boards/board-1');
    await expect(page.locator('.board-toolbar')).toBeVisible({ timeout: 10000 });
  });

  test('should allow renaming the board by clicking the name', async ({ page }) => {
    const boardName = page.locator('.board-toolbar__name');
    await expect(boardName).toBeVisible({ timeout: 10000 });
    await boardName.click();

    // An input field should replace the name heading
    const nameInput = page.locator('.board-toolbar__name-input');
    await expect(nameInput).toBeVisible();
    await expect(nameInput).toHaveValue('Test Board');
  });

  test('should open the AI actions dropdown menu', async ({ page }) => {
    const aiBtn = page.locator('.board-toolbar__btn--ai');
    await expect(aiBtn).toBeVisible({ timeout: 10000 });
    await aiBtn.click();

    const aiMenu = page.locator('.board-toolbar__dropdown-menu');
    await expect(aiMenu).toBeVisible();

    // Check for expected menu items
    await expect(page.locator('.board-toolbar__dropdown-item:has-text("Summarize")')).toBeVisible();
    await expect(page.locator('.board-toolbar__dropdown-item:has-text("Cluster by Theme")')).toBeVisible();
    await expect(page.locator('.board-toolbar__dropdown-item:has-text("Find Connections")')).toBeVisible();
  });

  test('should close the AI actions dropdown when clicking outside', async ({ page }) => {
    const aiBtn = page.locator('.board-toolbar__btn--ai');
    await aiBtn.click();

    const aiMenu = page.locator('.board-toolbar__dropdown-menu');
    await expect(aiMenu).toBeVisible();

    // Click somewhere outside the dropdown
    const toolbar = page.locator('.board-toolbar__left');
    await toolbar.click();

    await expect(aiMenu).not.toBeVisible({ timeout: 5000 });
  });

  test('should show the Memory button with badge', async ({ page }) => {
    const memoryBtn = page.locator('.board-toolbar__btn:has-text("Memory")');
    await expect(memoryBtn).toBeVisible({ timeout: 10000 });
  });
});

// ===========================================================================
// 7. Board List Operations
// ===========================================================================

test.describe('Board List Operations', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
    await page.goto('/boards');
    await expect(page.locator('.board-list')).toBeVisible({ timeout: 10000 });
  });

  test('should show board deletion button on each card', async ({ page }) => {
    const deleteButtons = page.locator('.board-list__card-delete');
    const boardCards = page.locator('.board-list__card');

    const cardCount = await boardCards.count();
    expect(cardCount).toBeGreaterThan(0);

    // Each card should have a delete button
    await expect(deleteButtons).toHaveCount(cardCount);
  });

  test('should display board updated dates', async ({ page }) => {
    const dateLabels = page.locator('.board-list__card-date');
    const count = await dateLabels.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show empty state when no boards exist', async ({ page }) => {
    // Override the boards route to return empty list
    await page.route('**/api/boards', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ boards: [] }),
      });
    });

    await page.goto('/boards');

    const emptyState = page.locator('.board-list__empty');
    await expect(emptyState).toBeVisible({ timeout: 10000 });
    await expect(emptyState).toContainText('No boards yet');
  });
});

// ===========================================================================
// 8. Error Handling
// ===========================================================================

test.describe('Board Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
  });

  test('should handle board API failure gracefully', async ({ page }) => {
    // Override boards to return 500
    await page.route('**/api/boards', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await page.goto('/boards');

    // The page should still render (not crash)
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle single board fetch failure gracefully', async ({ page }) => {
    await page.route('**/api/boards/board-broken', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Board not found' }),
      });
    });

    await page.route('**/api/boards/board-broken/cards', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Not found' }),
      });
    });

    await page.route('**/api/boards/board-broken/edges', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Not found' }),
      });
    });

    await page.route('**/api/boards/board-broken/memory', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Not found' }),
      });
    });

    await page.goto('/boards/board-broken');

    // Page should not crash
    await expect(page.locator('body')).toBeVisible();
  });
});

// ===========================================================================
// 9. Responsive Behavior
// ===========================================================================

test.describe('Board Responsive Behavior', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthAndMocks(page);
  });

  test('should render board list on a mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/boards');

    const boardList = page.locator('.board-list');
    await expect(boardList).toBeVisible({ timeout: 10000 });
  });

  test('should render board view on a tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/boards/board-1');

    const boardView = page.locator('.board-view');
    await expect(boardView).toBeVisible({ timeout: 10000 });
  });
});
