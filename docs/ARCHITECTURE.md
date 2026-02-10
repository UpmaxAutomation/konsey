# Architecture Overview

This document describes the high-level architecture of the LLM Council application, covering module structure, dependency rules, data flow, and key implementation patterns.

---

## Module Structure

The frontend uses a feature-based module system. Each module is self-contained with its own components, hooks, styles, and barrel exports.

```
frontend/src/
|
+-- modules/
|   +-- canvas/                    # Board/canvas feature
|   |   +-- components/            # 12 React components
|   |   |   +-- BoardView.jsx      # Root orchestrator
|   |   |   +-- BoardList.jsx      # Board listing page
|   |   |   +-- CanvasCard.jsx     # Custom ReactFlow node
|   |   |   +-- AnimatedEdge.jsx   # Custom ReactFlow edge
|   |   |   +-- BoardToolbar.jsx   # Top toolbar
|   |   |   +-- CardContextMenu.jsx# Right-click menu
|   |   |   +-- BoardQueryInput.jsx# Council modal
|   |   |   +-- BoardSearch.jsx    # Search bar
|   |   |   +-- BoardMemoryPanel.jsx# Memory side panel
|   |   |   +-- BoardPicker.jsx    # Board selector dropdown
|   |   |   +-- CardEditor.jsx     # Inline card editor
|   |   |   +-- SynthesisExpander.jsx# Stage drill-down
|   |   +-- hooks/                 # 7 custom hooks
|   |   |   +-- useBoardState.js
|   |   |   +-- useCardActions.js
|   |   |   +-- useEdgeActions.js
|   |   |   +-- useDebouncedPositions.js
|   |   |   +-- useKeyboardShortcuts.js
|   |   |   +-- useBoardSearch.js
|   |   |   +-- useBacklinks.js
|   |   +-- styles/                # 9 CSS files (one per component)
|   |   +-- utils.js               # cardToNode, edgeToFlow, EDGE_STYLES
|   |   +-- index.js               # Barrel exports
|   |
|   +-- chat/                      # Chat/conversation feature
|       +-- components/            # ChatInterface, Stage1, Stage2, Stage3,
|       |                          # ProgressIndicator, CompareView, VoicePanel,
|       |                          # FileUpload, Artifacts, CostEstimate
|       +-- index.js               # Barrel exports
|
+-- shared/                        # Cross-module shared code
|   +-- components/                # SafeMarkdown, ChartRenderer, Toast,
|   |                              # CopyButton, ShareButton, ThemeToggle,
|   |                              # ErrorBoundary, ProtectedRoute, SearchModal
|   +-- styles/
|   +-- index.js                   # Barrel exports
|
+-- api/                           # API client layer
|   +-- client.js                  # Base URL, authFetch wrapper
|   +-- boards.js                  # Board/card/edge/AI action endpoints
|   +-- conversations.js           # Conversation endpoints
|   +-- ...
|
+-- App.jsx                        # Top-level routing and layout
```

The backend follows a layered architecture with routers, business logic, and data access separated:

```
backend/
|
+-- routes/                        # FastAPI routers
|   +-- boards.py                  # Board/card/edge/AI/memory/council endpoints
|   +-- conversations.py           # Conversation CRUD and council execution
|   +-- auth.py                    # Authentication routes
|   +-- config.py                  # Model configuration routes
|   +-- projects.py                # Project management
|   +-- ...
|
+-- council/                       # Council deliberation engine
|   +-- orchestration.py           # run_full_council, run_full_council_stream
|   +-- stage1.py                  # Collect individual responses
|   +-- stage2.py                  # Anonymized peer ranking
|   +-- stage3.py                  # Chairman synthesis
|   +-- card_prompts.py            # AI action prompt templates
|   +-- parsing.py                 # Ranking text parser
|   +-- aggregation.py             # Aggregate ranking calculator
|   +-- context.py                 # Context gathering (web, project)
|   +-- utils.py                   # Title generation, helpers
|
+-- database/
|   +-- models.py                  # SQLAlchemy models (Board, Card, Edge, ...)
|   +-- connection.py              # Async DB session
|   +-- crud/                      # Data access functions
|       +-- boards.py              # Board/card/edge CRUD
|       +-- conversations.py
|       +-- projects.py
|       +-- ...
|
+-- llm/                           # LLM provider abstraction
+-- config.py                      # Model lists, presets, chairman
+-- main.py                        # FastAPI app entry point
```

---

## Dependency Rules

### Frontend

Imports follow a strict downward direction. Violations will create circular dependencies and should be avoided.

```
App.jsx
  |
  +-- modules/canvas/    (imports from shared/ and api/)
  |
  +-- modules/chat/      (imports from shared/ and api/)
  |
  +-- shared/            (imports from api/ only)
  |
  +-- api/               (imports nothing from modules/ or shared/)
```

Concrete rules:

1. **Modules do not import from each other.** `canvas/` never imports from `chat/` and vice versa. Cross-module communication uses browser `CustomEvent` (e.g., `discussCardInChat` dispatched from `CardContextMenu`).
2. **Modules import from `shared/`.** Components like `SafeMarkdown` are used by both canvas and chat modules.
3. **Modules import from `api/`.** Each module calls the API client directly. There is no intermediate service layer.
4. **`shared/` does not import from modules.** Shared components are generic and module-agnostic.
5. **`api/` imports nothing from components.** It is a pure HTTP client layer.

### Backend

```
routes/
  |
  +-- council/           (business logic, prompt templates)
  |
  +-- llm/               (LLM provider abstraction)
  |
  +-- database/crud/     (data access)
  |
  +-- database/models    (SQLAlchemy models)
```

Routes import from council, llm, and database. Council imports from llm and database. Database modules import only from models and SQLAlchemy.

---

## Data Flow

### User Creates a Card

```
User clicks "Note" in toolbar
  --> BoardToolbar calls onAddCard('note')
  --> useCardActions.handleAddCard('note')
    --> POST /api/boards/{id}/cards  (API call)
    --> Backend creates Card row in database
    --> Returns serialized card JSON
  --> cardToNode(card) converts to ReactFlow node
  --> setNodes appends the new node
  --> ReactFlow renders the card on canvas
```

### User Runs an AI Action on a Card

```
User right-clicks card --> selects "Summarize"
  --> CardContextMenu calls onAction(nodeId, 'summarize')
  --> useCardActions.handleCardAIAction(nodeId, 'summarize')
    --> Card added to processingCards set (triggers spinner CSS)
    --> POST /api/boards/{id}/cards/{cardId}/ai-action
    --> Backend:
        1. Loads card content
        2. Builds prompt from CARD_AI_PROMPTS['summarize']
        3. Prepends board context (knowledge cards, memory, project)
        4. Calls LLM via query_model()
        5. Creates result card + derived_from edge
        6. Returns { cards: [...], edges: [...] }
    --> Frontend appends new nodes and edges to canvas
    --> Card removed from processingCards set
```

### User Runs Council from Board

```
User selects cards --> clicks "Council" --> types query --> Cmd+Enter
  --> BoardQueryInput calls onRun({ query, webSearch, fastMode })
  --> BoardView.handleRunCouncil()
    --> POST /api/boards/{id}/council  (SSE stream)
    --> Backend streams stage1_complete, stage2_complete, stage3_complete events
    --> On completion, backend auto-creates:
        - query card
        - council_response cards (one per model)
        - council_synthesis card
        - derived_from and synthesizes edges
        - Saves decision to board memory
    --> Emits board_update SSE event with new cards/edges
    --> Frontend reads board_update event
    --> Appends new nodes and edges to canvas
```

### Card Position Persistence

```
User drags a card and releases
  --> ReactFlow fires onNodesChange with position change (dragging: false)
  --> useDebouncedPositions.handleNodesChange()
    --> Accumulates position in pendingPositions ref
    --> After 500ms debounce, flushes all pending positions
    --> PATCH /api/boards/{id}/cards/batch-positions
    --> Backend batch-updates position_x/position_y in database
```

### Chat-to-Canvas Bridge

```
User clicks "Add to Board" on a council turn in chat
  --> BoardPicker appears, user selects a board
  --> POST /api/boards/{id}/cards/from-council-turn
  --> Backend creates query, response, and synthesis cards
     with derived_from and synthesizes edges
  --> Returns { cards: [...], edges: [...] }
```

---

## Key Patterns

### Memoization and Stable References

`CanvasCard` and `AnimatedEdge` are wrapped in `React.memo` to prevent unnecessary re-renders when other nodes change. To support this:

- **`stableUpdateCard`**: Uses a `useRef` wrapper so the function reference never changes, even when `boardId` or `setNodes` change. This prevents re-rendering every card when the board reloads.
- **`stableFocusCard`**: Same pattern. The actual implementation is stored in a ref and the exposed callback delegates to `ref.current`.
- **`useBacklinks`**: Stores `nodes` in a ref so that the memo only recomputes when `edges` change, not when node titles update.

### Event-Based Cross-Module Communication

Modules do not import from each other. The `CardContextMenu` "Discuss in Chat" action dispatches a `CustomEvent`:

```js
window.dispatchEvent(new CustomEvent('discussCardInChat', {
  detail: { nodeId, cardType }
}));
```

The chat module listens for this event and opens the relevant card content in the chat interface. This keeps the modules decoupled.

### Debounced Persistence

Two operations use debounced saves to avoid flooding the API:

| Operation | Debounce | API Call |
|-----------|----------|----------|
| Card position (drag end) | 500ms | `PATCH .../batch-positions` |
| Viewport (pan/zoom end) | 800ms | `PATCH .../viewport` |

Positions accumulate in a ref object keyed by card ID, so rapid multi-card drags are coalesced into a single batch request.

### Node Data Injection

`BoardView` runs a `useEffect` that injects dynamic properties into every node's `data` object whenever dependencies change:

```js
useEffect(() => {
  setNodes(nds => nds.map(n => ({
    ...n,
    data: {
      ...n.data,
      backlinks: backlinksMap[n.id] || [],
      onFocusCard: stableFocusCard,
      onUpdateCard: stableUpdateCard,
      isDimmed: highlightedCards != null && !highlightedCards.has(n.id),
      isProcessing: processingCards.has(n.id),
    },
  })));
}, [backlinksMap, stableFocusCard, stableUpdateCard, highlightedCards, processingCards]);
```

This approach keeps `CanvasCard` a pure presentational component that receives everything it needs through `data` props, with no direct hook calls or API imports.

### Board Context Enrichment

When an AI action runs (card-level or board-level), the backend automatically prepends context from three sources:

1. **Project context**: System prompt, knowledge base, and memory from the board's linked project.
2. **Board memory**: Facts and decisions stored in the board's memory.
3. **Knowledge cards**: Up to 10 cards with `extra.is_knowledge = true`, capped at 2000 characters each.

This context enrichment happens transparently in `_get_board_context()` in `backend/routes/boards.py`.

### Search-Driven Dimming

Search does not filter nodes from the canvas. Instead, it sets `isDimmed: true` on non-matching nodes:

```
Search query changes
  --> useBoardSearch computes matchIds
  --> BoardView derives highlightedCards = new Set(matchIds)
  --> useEffect injects isDimmed into node data
  --> CanvasCard applies canvas-card--dimmed class (reduced opacity)
```

The active match can be navigated with arrow keys or Enter. Navigation calls `stableFocusCard` to pan and zoom the viewport to the active match.

### Snap Grid

The ReactFlow canvas uses a 16x16 snap grid for consistent card alignment:

```jsx
<ReactFlow snapToGrid snapGrid={[16, 16]} />
<Background gap={16} size={1} />
```
