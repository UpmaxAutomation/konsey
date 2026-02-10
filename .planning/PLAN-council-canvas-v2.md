# Council Canvas v2: 10/10 Modular Execution Plan

**Version:** 2.0
**Status:** Ready for execution
**Predecessor:** PLAN-council-canvas.md (rated 7/10 — see appendix for gap analysis)
**North star:** One workspace where boards, cards, and council deliberation compose like LEGO bricks. Any developer can own a module without reading the rest.

---

## 0. What the 7/10 plan missed (and this plan fixes)

| Gap in v1 plan | How v2 addresses it |
|----------------|---------------------|
| No card-level AI actions | Phase 5: Card AI module with summarize, expand, mind-map actions |
| No board-level AI actions | Phase 5: Board AI module with cluster, connect, synthesize-all |
| No memory/context injection | Phase 3: Board memory module (facts, decisions, preferences) |
| No inline editing UX | Phase 2: Edit mode with blur handling, keyboard shortcuts |
| No search | Phase 4: Board search with Cmd+F, type filtering |
| No backlinks | Phase 4: Backlinks module with source tracking |
| No knowledge cards | Phase 3: Knowledge card type with `extra.is_knowledge` flag |
| "React Flow or Tldraw" non-decision | Decision: React Flow (node graph > freeform drawing) |
| No error handling design | Every phase includes error states and degradation rules |
| Time estimates are noise | No time estimates. Work is sized by module count. |

---

## 1. Architecture principles

### 1.1 Module boundaries

Every feature is a **module** — a self-contained directory with its own components, hooks, API functions, types, and CSS. Modules communicate through well-defined interfaces (props, events, context). No module imports from another module's internals.

```
Module = {
  components/   — React components (1 per file, <300 LOC)
  hooks/        — Custom hooks (state + side effects)
  api/          — API client functions
  types/        — TypeScript interfaces (or JSDoc @typedef)
  utils/        — Pure utility functions
  index.js      — Public API (barrel export)
  __tests__/    — Unit + integration tests
}
```

### 1.2 Dependency rules

```
         ┌─────────────────────────────────┐
         │         App shell               │
         │  (routing, layout, providers)    │
         └────┬───────────┬────────────────┘
              │           │
    ┌─────────▼──┐   ┌────▼──────────┐
    │  Chat      │   │  Canvas       │
    │  module    │   │  module       │
    └─────┬──────┘   └────┬──────────┘
          │               │
    ┌─────▼───────────────▼──────────┐
    │       Shared layer             │
    │  (api/client, contexts,        │
    │   SafeMarkdown, ErrorBoundary) │
    └────────────────────────────────┘
```

**Rules:**
1. Chat module never imports from Canvas module (and vice versa).
2. Both import from Shared layer only.
3. Shared layer never imports from Chat or Canvas.
4. New features are new modules, not additions to existing modules.

### 1.3 File size limits

| Entity | Max LOC | Action when exceeded |
|--------|---------|---------------------|
| Component | 300 | Extract sub-components |
| Hook | 150 | Split into focused hooks |
| API module | 200 | Split by resource |
| CSS file | 400 | Split by component |

### 1.4 State management strategy

| Scope | Tool | Example |
|-------|------|---------|
| App-wide (auth, theme) | React Context | `useAuth()`, `useTheme()` |
| Feature-wide (board state) | `useReducer` + Context | `useBoardState()` |
| Component-local | `useState` | Collapsed, hover, editing |
| Server state | API + `useEffect` | Board data, card list |
| Derived state | `useMemo` | Filtered cards, backlink map |

No Redux/Zustand — keep it simple. If ChatInterface grows beyond 89 state vars again, extract to `useReducer`.

---

## 2. Target directory structure

### 2.1 Frontend

```
frontend/src/
├── app/                          # App shell
│   ├── App.jsx                   # Routing + layout (≤200 LOC)
│   ├── AppProviders.jsx          # Context provider tree
│   ├── routes.jsx                # Route definitions
│   └── App.css
│
├── modules/
│   ├── canvas/                   # Canvas module (this plan)
│   │   ├── components/
│   │   │   ├── BoardList.jsx         # Board list grid
│   │   │   ├── BoardView.jsx         # Canvas editor (ReactFlow wrapper)
│   │   │   ├── BoardToolbar.jsx      # Top toolbar
│   │   │   ├── BoardSearch.jsx       # Search + filter overlay
│   │   │   ├── BoardMemoryPanel.jsx  # Memory sidebar
│   │   │   ├── BoardQueryInput.jsx   # Council prompt modal
│   │   │   ├── CanvasCard.jsx        # Card node (ReactFlow custom node)
│   │   │   ├── CardContextMenu.jsx   # Right-click menu
│   │   │   ├── CardEditor.jsx        # Inline edit form (extracted)
│   │   │   ├── BacklinksPanel.jsx    # Backlinks display
│   │   │   └── SynthesisExpander.jsx # Stage 1/2/3 expandable view
│   │   ├── hooks/
│   │   │   ├── useBoardState.js      # Board reducer + dispatch
│   │   │   ├── useCardActions.js     # CRUD operations on cards
│   │   │   ├── useEdgeActions.js     # Edge CRUD
│   │   │   ├── useBoardMemory.js     # Memory state + API
│   │   │   ├── useDebouncePosition.js# Debounced position save
│   │   │   ├── useBoardSearch.js     # Search state + filtering
│   │   │   ├── useBacklinks.js       # Compute backlink map
│   │   │   └── useKeyboardShortcuts.js# Board-specific shortcuts
│   │   ├── api/
│   │   │   ├── boards.js             # Board CRUD
│   │   │   ├── cards.js              # Card CRUD + batch ops
│   │   │   ├── edges.js              # Edge CRUD
│   │   │   ├── boardAI.js            # Board-level AI actions
│   │   │   ├── cardAI.js             # Card-level AI actions
│   │   │   └── memory.js             # Board memory API
│   │   ├── types/
│   │   │   └── canvas.js             # JSDoc @typedef for Board, Card, Edge
│   │   ├── utils/
│   │   │   ├── layout.js             # Auto-layout algorithms
│   │   │   ├── cardToNode.js         # Card → ReactFlow node conversion
│   │   │   └── edgeToConnection.js   # Edge → ReactFlow edge conversion
│   │   ├── canvas.css                # All canvas styles (or split per component)
│   │   └── index.js                  # Public: { BoardList, BoardView }
│   │
│   ├── chat/                     # Chat module (existing, refactored)
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx     # Orchestrator (≤300 LOC after extraction)
│   │   │   ├── MessageList.jsx       # Scrollable message display
│   │   │   ├── InputArea.jsx         # Text input + file attach + voice
│   │   │   ├── ModelSelector.jsx     # Mode + model picker
│   │   │   ├── FeatureToggles.jsx    # Memory, search, code toggles
│   │   │   ├── Stage1.jsx
│   │   │   ├── Stage2.jsx
│   │   │   ├── Stage3.jsx
│   │   │   ├── CompareView.jsx
│   │   │   └── ProgressIndicator.jsx
│   │   ├── hooks/
│   │   │   ├── useChatState.js       # Chat reducer
│   │   │   ├── useStreaming.js        # SSE/stream management
│   │   │   ├── useModelPicker.js     # Model selection logic
│   │   │   └── useFileUpload.js      # File handling
│   │   ├── api/                      # (reuse existing api/ files)
│   │   └── index.js
│   │
│   ├── projects/                 # Project module (existing)
│   │   ├── components/
│   │   ├── hooks/
│   │   └── index.js
│   │
│   ├── settings/                 # Settings module
│   │   ├── components/
│   │   └── index.js
│   │
│   └── admin/                    # Admin module
│       ├── components/
│       └── index.js
│
├── shared/                       # Shared layer
│   ├── components/
│   │   ├── SafeMarkdown.jsx
│   │   ├── ErrorBoundary.jsx
│   │   ├── CopyButton.jsx
│   │   ├── Toast.jsx
│   │   └── ThemeToggle.jsx
│   ├── contexts/
│   │   ├── AuthContext.jsx
│   │   ├── ThemeContext.jsx
│   │   └── ToastContext.jsx
│   ├── api/
│   │   ├── client.js                 # Base HTTP client
│   │   └── errors.js                 # Error classes
│   ├── hooks/
│   │   ├── useDebounce.js
│   │   └── useMediaQuery.js
│   └── utils/
│       ├── retry.js
│       ├── connectionCheck.js
│       └── modelNames.js
│
└── assets/                       # Static assets
```

### 2.2 Backend

```
backend/
├── main.py                       # FastAPI app setup + middleware ONLY (≤200 LOC)
├── config.py                     # Static config (models, presets, personas)
│
├── routes/                       # One router per feature
│   ├── auth.py                   # Auth endpoints
│   ├── boards.py                 # Board/Card/Edge CRUD + AI actions
│   ├── conversations.py          # Conversation CRUD + messaging (extracted from main.py)
│   ├── config_routes.py          # Config endpoints (extracted from main.py)
│   ├── tools_routes.py           # Web search, code exec, memory (extracted)
│   ├── projects.py               # Project endpoints (extracted)
│   ├── files.py                  # File upload/download endpoints (extracted)
│   └── models.py                 # Available models endpoint
│
├── council/                      # Council orchestration (existing, good)
│   ├── orchestration.py
│   ├── stage1.py
│   ├── stage2.py
│   ├── stage3.py
│   ├── context.py
│   └── card_prompts.py
│
├── llm/                          # LLM client (existing, good)
│   ├── client.py
│   ├── cache.py
│   └── usage.py
│
├── services/                     # Business logic (extracted from tools.py, files.py)
│   ├── search.py
│   ├── code_execution.py
│   ├── memory.py
│   ├── file_processing.py
│   ├── image_gen.py
│   └── voice.py
│
├── database/
│   ├── models.py
│   ├── connection.py
│   ├── crud/
│   │   ├── boards.py
│   │   ├── conversations.py
│   │   ├── users.py
│   │   ├── api_keys.py
│   │   ├── memory.py
│   │   ├── projects.py
│   │   ├── settings.py
│   │   └── usage.py
│   └── migrations/
│
├── auth/
│   ├── jwt_handler.py
│   ├── password.py
│   ├── dependencies.py
│   └── oauth.py
│
└── storage/                      # Storage adapters
    ├── adapter.py
    ├── json_storage.py
    └── supabase_storage.py
```

---

## 3. Phase map

```
Phase 1: Refactor into modules          ← Foundation
Phase 2: Canvas core (cards + edges)    ← Usable whiteboard
Phase 3: Council on canvas + memory     ← Core loop
Phase 4: Search + backlinks             ← Navigability
Phase 5: Card AI + Board AI             ← Intelligence
Phase 6: Cross-module integration       ← Chat ↔ Canvas bridge
Phase 7: Polish + developer docs        ← Ship quality
```

Each phase produces a working system. No phase depends on a later phase.

---

## 4. Phase 1: Refactor into modules

### 4.1 Goal
Split the existing codebase into the modular structure defined in section 2. No new features — purely structural.

### 4.2 Backend refactoring

**Extract from main.py (7,539 LOC → ~200 LOC):**

| New file | Endpoints moved | Approx LOC |
|----------|----------------|------------|
| `routes/conversations.py` | `/api/conversations/*` | ~800 |
| `routes/config_routes.py` | `/api/config/*`, `/api/presets/*` | ~300 |
| `routes/tools_routes.py` | `/api/tools/*`, `/api/search/*` | ~400 |
| `routes/projects.py` | `/api/projects/*` | ~500 |
| `routes/files.py` | `/api/files/*` | ~400 |
| `routes/models.py` | `/api/models/*` | ~100 |

**Extract from tools.py (902 LOC):**

| New file | Functions moved |
|----------|----------------|
| `services/search.py` | `web_search()`, `deep_search()` |
| `services/code_execution.py` | `execute_code()` |
| `services/memory.py` | `get_memory_context()`, `remember_fact()`, `set_preference()` |

**Extract from files.py (1,485 LOC):**

| New file | Functions moved |
|----------|----------------|
| `services/file_processing.py` | `process_upload()`, `extract_text()`, `create_embedding()` |

**main.py becomes:**
```python
from fastapi import FastAPI
from .routes import auth, boards, conversations, config_routes, tools_routes, projects, files, models

app = FastAPI(title="LLM Council")

# Middleware
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(RequestLoggingMiddleware)

# Mount routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(boards.router, prefix="/api/boards")
app.include_router(conversations.router, prefix="/api/conversations")
app.include_router(config_routes.router, prefix="/api")
app.include_router(tools_routes.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(files.router, prefix="/api/files")
app.include_router(models.router, prefix="/api")

# Startup/shutdown
@app.on_event("startup")
async def startup(): ...

@app.on_event("shutdown")
async def shutdown(): ...
```

### 4.3 Frontend refactoring

**Move files into module structure:**

| Current location | New location |
|-----------------|--------------|
| `components/BoardView.jsx` | `modules/canvas/components/BoardView.jsx` |
| `components/CanvasCard.jsx` | `modules/canvas/components/CanvasCard.jsx` |
| `components/BoardToolbar.jsx` | `modules/canvas/components/BoardToolbar.jsx` |
| `components/BoardSearch.jsx` | `modules/canvas/components/BoardSearch.jsx` |
| `components/BoardMemoryPanel.jsx` | `modules/canvas/components/BoardMemoryPanel.jsx` |
| `components/BoardQueryInput.jsx` | `modules/canvas/components/BoardQueryInput.jsx` |
| `components/BoardList.jsx` | `modules/canvas/components/BoardList.jsx` |
| `components/CardContextMenu.jsx` | `modules/canvas/components/CardContextMenu.jsx` |
| `api/boards.js` | `modules/canvas/api/boards.js` (split further) |
| `components/ChatInterface.jsx` | `modules/chat/components/ChatInterface.jsx` |
| `components/Stage1.jsx` | `modules/chat/components/Stage1.jsx` |
| `components/Stage2.jsx` | `modules/chat/components/Stage2.jsx` |
| `components/Stage3.jsx` | `modules/chat/components/Stage3.jsx` |

**Extract hooks from BoardView.jsx:**

| Hook | Responsibility |
|------|---------------|
| `useBoardState()` | Board data, loading, error |
| `useCardActions()` | Add, update, delete card |
| `useEdgeActions()` | Add, delete edge |
| `useDebouncePosition()` | Throttled position save |
| `useKeyboardShortcuts()` | Key bindings |

**After extraction, BoardView.jsx becomes:**
```jsx
function BoardView({ boardId, onBack }) {
  const board = useBoardState(boardId);
  const cards = useCardActions(boardId);
  const edges = useEdgeActions(boardId);
  const shortcuts = useKeyboardShortcuts(cards, edges);
  const search = useBoardSearch(board.nodes);

  if (board.loading) return <Loading />;
  if (board.error) return <Error error={board.error} />;

  return (
    <div className="board-view">
      <BoardToolbar board={board} cards={cards} onBack={onBack} />
      <ReactFlow nodes={board.nodes} edges={board.edges} ... />
      {search.isOpen && <BoardSearch ... />}
    </div>
  );
}
```

### 4.4 Done when

- [ ] `main.py` is ≤200 LOC (imports + middleware + router mounting)
- [ ] Each route file has ≤500 LOC
- [ ] Frontend components are in `modules/` directories
- [ ] All imports use module barrel exports (e.g., `from '../canvas'`)
- [ ] `npm run build` passes
- [ ] `python -m backend.main` starts without errors
- [ ] No functional regressions (manual test: create board, add card, run council, chat works)

---

## 5. Phase 2: Canvas core (cards + edges)

### 5.1 Goal
Solid whiteboard with card CRUD, drag-to-position, edge drawing, and inline editing.

### 5.2 Card types and data model

```
Card {
  id: UUID
  board_id: UUID
  card_type: 'note' | 'link' | 'file_ref' | 'council_response' | 'council_synthesis'
  title: string
  content: string (markdown)
  position: { x: number, y: number }
  size: { w: number, h: number } (optional)
  color: string (optional)
  extra: {
    // note: { is_knowledge?: boolean }
    // link: { url: string }
    // file_ref: { file_id: string, filename: string }
    // council_response: { model: string, thinking?: string }
    // council_synthesis: { stage1: [], stage2: [], stage3: {} }
  }
  created_at: datetime
  updated_at: datetime
}

Edge {
  id: UUID
  board_id: UUID
  from_card_id: UUID
  to_card_id: UUID
  edge_type: 'derived_from' | 'synthesizes' | 'related' | 'ranks_above'
  label: string (optional)
}
```

### 5.3 Card rendering (CanvasCard.jsx)

Each card type renders differently:

| Type | Icon | Body | Editable |
|------|------|------|----------|
| note | memo | Markdown content | Yes (double-click) |
| knowledge | book | Markdown content + purple border | Yes (double-click) |
| link | link | Clickable URL + title | Title only |
| file_ref | paperclip | Filename + preview | No |
| council_response | chat bubble | Model response + thinking toggle | No |
| council_synthesis | sparkles | Synthesis + expandable stages | No |

### 5.4 Inline editing (CardEditor.jsx)

Extracted from CanvasCard to a dedicated component:

```
CardEditor props:
  - initialTitle: string
  - initialContent: string
  - onSave: (title, content) => void
  - onCancel: () => void

Behavior:
  - Auto-focus title on mount
  - Tab from title to content
  - Cmd+Enter to save
  - Escape to cancel
  - Blur saves ONLY if focus leaves .canvas-card__edit-area entirely
    (uses e.relatedTarget check to prevent premature save)
  - nodrag + nowheel classes to prevent ReactFlow from intercepting
```

### 5.5 Error states

| Scenario | Behavior |
|----------|----------|
| Card save fails | Show toast, revert to previous content |
| Edge create fails | Show toast, remove visual edge |
| Board load fails | Show error state with retry button |
| Position save fails | Silent retry (3 attempts), then toast |

### 5.6 Done when

- [ ] Create/edit/delete note cards
- [ ] Create/delete link cards
- [ ] Create/delete file_ref cards
- [ ] Drag cards to reposition (debounced save)
- [ ] Draw edges between cards (click handles)
- [ ] Delete edges (right-click menu or backspace)
- [ ] Inline editing with blur-safe focus handling
- [ ] Keyboard shortcuts: N (note), L (link), K (knowledge), Delete (remove), Cmd+Z (undo)
- [ ] All card data persists across page reload
- [ ] Error states display correctly

---

## 6. Phase 3: Council on canvas + memory

### 6.1 Goal
Run council with board context. Output appears as synthesis card with edges. Board has persistent memory.

### 6.2 Council from board flow

```
User selects cards (or "use full board")
  → Clicks "Run Council" in toolbar
  → BoardQueryInput modal opens
  → User types question
  → Submit
  → API: POST /api/boards/{boardId}/council
    Body: { query, card_ids[], include_memory: boolean }
  → Backend:
    1. Load card contents (+ file content for file_ref cards)
    2. Load board memory (facts, decisions)
    3. Build context string
    4. Run council (3 stages)
    5. Return: { stage1, stage2, stage3, metadata }
  → Frontend:
    1. Create council_synthesis card at center of selected cards
    2. Create edges from synthesis card to each source card (type: 'synthesizes')
    3. Optionally create council_response cards (one per model)
    4. Card is expandable to show Stage 1 → 2 → 3
```

### 6.3 Board memory module

**Data model:**
```json
{
  "facts": ["The project uses React Flow for canvas", "Budget is $5k/month"],
  "decisions": ["Use PostgreSQL not MongoDB", "Ship MVP by Q2"],
  "preferences": {
    "model": "claude-sonnet-4",
    "style": "concise"
  }
}
```

**API:**
```
GET    /api/boards/{id}/memory           → { memory }
POST   /api/boards/{id}/memory           → { action: 'add_fact' | 'add_decision' | 'clear', content }
DELETE /api/boards/{id}/memory/facts/{i} → { memory }
```

**Hook: `useBoardMemory(boardId)`**
```
Returns: {
  memory: { facts, decisions, preferences },
  addFact: (content) => void,
  addDecision: (content) => void,
  deleteFact: (index) => void,
  clearMemory: () => void,
  memoryCount: number,
  isLoading: boolean
}
```

**UI: BoardMemoryPanel.jsx**
- Slide-in panel from right
- Sections: Facts, Decisions
- Add new fact/decision via input
- Delete individual items
- Clear all button
- Badge count on toolbar button

### 6.4 Context injection

When council runs from board, the context includes:

```
=== Board Memory ===
Facts:
- The project uses React Flow
- Budget is $5k/month

Decisions:
- Use PostgreSQL not MongoDB

=== Selected Cards ===

[Card 1: "Research Notes"]
Type: note
Content: ...

[Card 2: "Architecture Doc"]
Type: file_ref
File content: ...

=== User Question ===
What are the main trade-offs in our architecture?
```

### 6.5 Synthesis card expandable (SynthesisExpander.jsx)

When a council_synthesis card is clicked/expanded, show:

```
┌──────────────────────────────────┐
│ Synthesis                    [×] │
│ ──────────────────────────────── │
│ [Stage 3 Answer]                 │
│                                  │
│ ▶ Stage 1: Individual Responses  │
│   ├─ claude-sonnet-4: ...        │
│   ├─ gpt-5: ...                  │
│   └─ gemini-2.5: ...             │
│                                  │
│ ▶ Stage 2: Peer Rankings         │
│   ├─ Rankings summary            │
│   └─ Aggregate scores            │
│                                  │
│ ▶ Stage 3: Full Synthesis        │
│   └─ Chairman response           │
└──────────────────────────────────┘
```

### 6.6 Error handling

| Scenario | Behavior |
|----------|----------|
| Council fails mid-stream | Show error card instead of synthesis, allow retry |
| Context exceeds token limit | Warn user, suggest selecting fewer cards |
| File content unavailable | Skip file, note in context "File X unavailable" |
| Board has no cards | Disable "Run Council" button |
| Memory save fails | Toast error, keep local state, retry |

### 6.7 Done when

- [ ] "Run Council" button works with card selection
- [ ] Council synthesis card appears with edges to source cards
- [ ] Synthesis card expands to show Stage 1/2/3
- [ ] Board memory panel works (add/delete facts, decisions)
- [ ] Memory injected into council context
- [ ] Error states handled gracefully
- [ ] Council progress indicator shows during run

---

## 7. Phase 4: Search + backlinks

### 7.1 Board search (BoardSearch.jsx)

**Trigger:** Cmd+F or search icon in toolbar

**Features:**
- Text search across card titles and content
- Filter by card type (note, knowledge, link, file_ref, council_synthesis)
- Highlight matching cards on canvas
- Navigate between matches (up/down arrows)
- Dim non-matching cards

**Hook: `useBoardSearch(nodes)`**
```
Returns: {
  isOpen: boolean,
  query: string,
  setQuery: (q) => void,
  typeFilter: Set<string>,
  toggleTypeFilter: (type) => void,
  results: Card[],
  activeIndex: number,
  next: () => void,
  prev: () => void,
  highlightedIds: Set<string>,
  open: () => void,
  close: () => void
}
```

### 7.2 Backlinks (BacklinksPanel within CanvasCard)

**What:** Each card shows incoming edges as backlinks. "3 backlinks" → expand to see which cards reference this one and how.

**Hook: `useBacklinks(nodes, edges)`**
```
Returns: Map<cardId, Backlink[]>

Backlink = {
  sourceId: string,
  sourceTitle: string,
  edgeType: string,  // 'derived_from', 'synthesizes', 'related'
  edgeId: string
}
```

**UI:**
- Small badge at bottom of card: "2 backlinks"
- Click to expand list
- Click backlink item to focus/pan to source card
- Edge type shown as colored tag

### 7.3 Done when

- [ ] Cmd+F opens search overlay
- [ ] Search matches highlight on canvas, non-matches dim
- [ ] Type filter works (checkboxes per card type)
- [ ] Arrow keys navigate between matches
- [ ] Backlinks display on cards with incoming edges
- [ ] Clicking backlink pans to source card
- [ ] Search closes with Escape

---

## 8. Phase 5: Card AI + Board AI

### 8.1 Card-level AI actions

Right-click a card → AI submenu:

| Action | Input | Output |
|--------|-------|--------|
| Summarize | Card content | New note card with summary |
| Expand | Card content | New note card with expanded analysis |
| Extract Key Points | Card content | New note card with bullet points |
| Generate Questions | Card content | New note card with questions |
| Mind Map | Card content | Multiple cards arranged radially with edges |
| Translate | Card content + target lang | New note card with translation |

**API: `POST /api/boards/{boardId}/cards/{cardId}/ai`**
```json
{
  "action": "summarize | expand | key_points | questions | mind_map | translate",
  "options": { "language": "es" }
}
```

**Backend:**
1. Load card content + board memory for context
2. Build action-specific prompt
3. Run through single LLM (not full council — card AI is fast mode)
4. Return: `{ cards: Card[], edges: Edge[] }`

**Frontend:**
1. Show processing indicator on source card
2. On response, add new cards to canvas
3. Position new cards relative to source (e.g., below, radial for mind map)
4. Create edges from source to new cards

### 8.2 Board-level AI actions

Toolbar dropdown → Board AI:

| Action | Input | Output |
|--------|-------|--------|
| Cluster by Theme | All cards | Cards repositioned into groups, group labels added |
| Find Connections | All cards | New edges between related cards |
| Summarize Board | All cards | One synthesis card summarizing everything |
| Generate Knowledge | All cards | Knowledge cards extracted from content |
| Suggest Next Steps | All cards + memory | New note cards with action items |

**API: `POST /api/boards/{boardId}/ai`**
```json
{
  "action": "cluster | connect | summarize | extract_knowledge | next_steps"
}
```

**Backend:**
1. Load all card content + board memory
2. Build action-specific prompt
3. Run through council (for board-level actions — quality matters)
4. Return: `{ cards: Card[], edges: Edge[], positions?: { cardId: {x, y} }[] }`

### 8.3 Processing states

```
Card AI running:
  - Source card shows spinner overlay
  - Card is non-interactive during processing
  - Cancel button in spinner

Board AI running:
  - Toolbar shows progress bar
  - Canvas dims slightly
  - Cancel button in toolbar
  - All cards non-interactive
```

### 8.4 Done when

- [ ] Right-click card → AI menu shows all actions
- [ ] Each card AI action creates new cards with edges
- [ ] Board AI actions work from toolbar dropdown
- [ ] Processing states show correctly
- [ ] Cancel works for both card and board AI
- [ ] New cards positioned logically relative to source
- [ ] Mind map creates radial layout

---

## 9. Phase 6: Cross-module integration (Chat ↔ Canvas)

### 9.1 Chat → Canvas

**"Pin to Board" button on Stage 3 / council responses:**
- Opens BoardPicker modal
- User selects board
- Creates card on selected board (type based on source: council_synthesis or council_response)
- Toast: "Pinned to Board Name"

**"Add to Board" on any message:**
- Right-click message → "Add to Board"
- Creates note card with message content

### 9.2 Canvas → Chat

**"Discuss in Chat" from card context menu:**
- Opens chat with card content pre-filled as context
- Message: "Based on this: [card content], ..."
- Response appears in chat (not on canvas)

### 9.3 URL-based routing

Replace state-based navigation with proper routes:

```
/                           → Redirect to /chat
/chat                       → Chat view (new conversation)
/chat/:conversationId       → Chat view (existing conversation)
/boards                     → Board list
/boards/:boardId            → Board view
/projects/:projectId        → Project view
/projects/:projectId/boards → Project board list
/settings                   → Settings
```

### 9.4 Done when

- [ ] "Pin to Board" works from Stage 3 responses
- [ ] "Add to Board" works from any chat message
- [ ] "Discuss in Chat" works from card context menu
- [ ] URL routing works with browser back/forward
- [ ] Deep links to boards work (share URL, open in new tab)

---

## 10. Phase 7: Polish + developer docs

### 10.1 Performance

| Concern | Mitigation |
|---------|-----------|
| 100+ cards on canvas | Virtualize off-screen cards (ReactFlow handles this) |
| Large card content | Truncate to 200 chars in collapsed view, full on expand |
| Frequent position saves | Debounce to 500ms, batch updates |
| Re-renders | `memo()` on CanvasCard, `useCallback` on handlers |
| Bundle size | Code-split canvas module (lazy load on first board open) |

### 10.2 Accessibility

- All buttons have `aria-label` or `title`
- Keyboard navigation: Tab through cards, Enter to select, Space to expand
- Screen reader: Card type and title announced
- Color contrast: Meet WCAG AA for all card types
- Focus management: After card creation, focus new card

### 10.3 Developer documentation

Create `frontend/docs/`:

| Doc | Content |
|-----|---------|
| `ARCHITECTURE.md` | Module structure, dependency rules, state management |
| `CANVAS.md` | Card types, edge types, React Flow integration |
| `API.md` | All canvas-related endpoints with examples |
| `CONTRIBUTING.md` | How to add a new card type, how to add a new AI action |
| `HOOKS.md` | All custom hooks with usage examples |

### 10.4 Testing strategy

| Layer | Tool | What to test |
|-------|------|-------------|
| Hooks | Vitest + React Testing Library | State transitions, API calls |
| Components | Vitest + RTL | Render, user interaction, error states |
| API module | Vitest + MSW | Request/response format, error handling |
| Integration | Playwright | Full board flow: create → add cards → run council → verify synthesis |
| Visual | Storybook (optional) | Card variants, toolbar states |

**Critical paths to test:**
1. Create board → add card → edit card → save → reload → verify
2. Select cards → run council → synthesis card appears → expand stages
3. Search → filter → navigate matches
4. Card AI → new cards appear → edges created
5. Pin to board → verify card on canvas

### 10.5 Done when

- [ ] Performance: 100 cards render without jank
- [ ] Accessibility: All interactive elements keyboard-accessible
- [ ] Developer docs written for canvas module
- [ ] CONTRIBUTING.md explains how to add card types and AI actions
- [ ] Integration test covers happy path
- [ ] Code review checklist created

---

## 11. Module interface contracts

### 11.1 Canvas module public API

```javascript
// modules/canvas/index.js
export { BoardList } from './components/BoardList';
export { BoardView } from './components/BoardView';

// Types (JSDoc)
/**
 * @typedef {Object} Board
 * @property {string} id
 * @property {string} name
 * @property {string|null} project_id
 * @property {Object} memory
 */

/**
 * @typedef {Object} Card
 * @property {string} id
 * @property {string} board_id
 * @property {'note'|'link'|'file_ref'|'council_response'|'council_synthesis'} card_type
 * @property {string} title
 * @property {string} content
 * @property {{x: number, y: number}} position
 * @property {Object} extra
 */
```

### 11.2 Chat module public API

```javascript
// modules/chat/index.js
export { ChatInterface } from './components/ChatInterface';
export { Stage1 } from './components/Stage1';
export { Stage2 } from './components/Stage2';
export { Stage3 } from './components/Stage3';
```

### 11.3 Cross-module events

Modules don't import each other. They communicate through the App shell:

```javascript
// App.jsx orchestrates
function App() {
  const handlePinToBoard = (boardId, content) => {
    // Called by Chat module
    // Delegates to Canvas module's API
    createCard(boardId, { card_type: 'note', content });
    toast.success('Pinned to board');
  };

  const handleDiscussInChat = (cardContent) => {
    // Called by Canvas module
    // Sets up Chat module's input
    setInitialMessage(`Based on this: ${cardContent}`);
    navigate('/chat');
  };

  return (
    <Routes>
      <Route path="/chat/*" element={<ChatInterface onPinToBoard={handlePinToBoard} />} />
      <Route path="/boards/:boardId" element={<BoardView onDiscussInChat={handleDiscussInChat} />} />
    </Routes>
  );
}
```

---

## 12. Risk register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Refactor breaks existing features | High | Phase 1 has no new features; manual test checklist before moving on |
| ChatInterface extraction causes regressions | High | Extract one sub-component at a time; test after each extraction |
| Board AI context exceeds token limit | Medium | Cap at 50 cards, truncate content, warn user |
| ReactFlow upgrade breaks custom nodes | Medium | Pin ReactFlow version; integration test for custom node rendering |
| Developer onboarding friction | Medium | CONTRIBUTING.md with "add a card type" walkthrough |
| main.py route extraction breaks API | High | Keep same URL paths; add API integration test before and after |
| Performance with many edges | Low | ReactFlow handles edge rendering; test with 200 edges |

---

## 13. Developer onboarding: How to add a new card type

This is the litmus test for modularity. A developer should be able to add a new card type by touching ≤5 files:

```
Step 1: Add type to TYPE_CONFIG in CanvasCard.jsx
  { video: { label: 'Video', icon: '🎬' } }

Step 2: Add rendering branch in CanvasCard.jsx
  case 'video': return <VideoCardBody url={data.extra.url} />;

Step 3: Add CSS in canvas.css
  .canvas-card--video { border-left: 4px solid #06b6d4; }

Step 4: Add "Add Video" button in BoardToolbar.jsx
  <button onClick={() => onAddCard('video')}>Video</button>

Step 5: (If new fields) Add to Card model in backend/database/models.py extra JSON

No migration needed (extra is JSON). No new API endpoints (card CRUD is generic).
No changes to council logic (context builder reads content field generically).
```

---

## 14. Appendix: v1 → v2 comparison

| Aspect | v1 (7/10) | v2 (this plan) |
|--------|-----------|----------------|
| Phases | 4 | 7 (includes refactor + AI + polish) |
| Card types covered | note, link, file_ref, synthesis | + knowledge, response |
| AI actions | Council from board only | Card AI (6 actions) + Board AI (5 actions) |
| Memory | Not mentioned | Full memory module (facts, decisions, prefs) |
| Search | Not mentioned | Cmd+F + type filter + highlight |
| Backlinks | Not mentioned | Backlink display + focus navigation |
| Inline editing | Not mentioned | CardEditor with blur-safe handling |
| Error handling | Not mentioned | Per-phase error states and degradation |
| Modularity | Implicit | Explicit module boundaries + dependency rules |
| Developer docs | Not mentioned | ARCHITECTURE, CANVAS, API, CONTRIBUTING, HOOKS |
| Testing | "Optional E2E" | Hooks, components, API, integration, visual |
| Onboarding | Not mentioned | "Add a card type in 5 files" walkthrough |
| React Flow vs Tldraw | "Recommended" | Decided: React Flow (node graph model) |
| Time estimates | "~6-8 weeks" | None (sized by module count, dev decides) |
| File size limits | Not mentioned | 300 LOC components, 150 LOC hooks |
| Cross-module rules | Not mentioned | Explicit dependency direction + no cross-imports |
| URL routing | State-based | URL-based with deep links |

---

## 15. Execution order summary

```
Phase 1: Refactor into modules
  Backend:  Split main.py → routes/, extract tools.py → services/
  Frontend: Move components into modules/, extract hooks from BoardView

Phase 2: Canvas core
  Cards: CRUD, inline editing, drag, keyboard shortcuts
  Edges: Draw, delete, right-click menu
  Error: Toast on failure, retry on position save

Phase 3: Council + memory
  Council: Select cards → run → synthesis card + edges
  Memory: Panel, facts/decisions, context injection
  Synthesis: Expandable Stage 1/2/3 view

Phase 4: Search + backlinks
  Search: Cmd+F, type filter, highlight, navigate
  Backlinks: Badge, list, focus on click

Phase 5: Card AI + Board AI
  Card: Summarize, expand, key points, questions, mind map
  Board: Cluster, connect, summarize, extract knowledge

Phase 6: Chat ↔ Canvas
  Pin to board, add to board, discuss in chat
  URL routing with deep links

Phase 7: Polish + docs
  Performance, accessibility, developer docs, tests
```

Each phase ships. Each phase is independently valuable. Any developer can pick up any phase by reading this plan + the module structure.
