# Canvas Module Reference

The canvas module provides a visual knowledge board built on [xyflow/react](https://reactflow.dev/) (formerly React Flow). Users create, connect, and manipulate cards on an infinite pan-and-zoom canvas. AI actions run on individual cards or entire boards, and the council deliberation system can be invoked directly from the board with selected cards as context.

---

## Card Types

Every card has a `card_type` field that determines its accent color, header icon, and behavior.

| Type | Label | Accent Color | Icon | Editable | Description |
|------|-------|-------------|------|----------|-------------|
| `note` | Note | `#6366f1` (Indigo) | &#x270E; | Yes | User-created notes. Double-click to edit. |
| `knowledge` | Knowledge | `#8b5cf6` (Violet) | &#x25C8; | Yes | Knowledge base entries. A `note` with `extra.is_knowledge = true`. Included as context in AI actions. |
| `query` | Query | `#f59e0b` (Amber) | ? | No | Represents a user query sent to the council. |
| `council_response` | Response | `#06b6d4` (Cyan) | &#x25B7; | No | An individual model response from Stage 1. Shows model name in the header. |
| `council_synthesis` | Synthesis | `#10b981` (Emerald) | &#x2726; | No | Final synthesis from the chairman model. Contains a `SynthesisExpander` that drills down into Stage 1 responses, Stage 2 rankings, and Stage 3 metadata. |
| `file_ref` | File | `#64748b` (Slate) | &#x25A1; | No | File reference cards. Displays `extra.filename` in a file-icon layout. |
| `link` | Link | `#3b82f6` (Blue) | &#x2197; | Yes | External link cards. Renders `extra.url` as a clickable anchor. |

Knowledge is a virtual type. Under the hood it is stored as `card_type: "note"` with `extra.is_knowledge: true`. Up to 10 knowledge cards (max 2000 chars each) are automatically included as context when AI actions run on the board.

---

## Edge Types

Edges connect cards on the board. Each edge type carries its own visual style, defined in `frontend/src/modules/canvas/utils.js`.

| Edge Type | Stroke Color | Width | Animated | Dashed | Label | Typical Usage |
|-----------|-------------|-------|----------|--------|-------|---------------|
| `derived_from` | `#94a3b8` (Slate) | 1.5 | No | No | "derived" | Query to response, source card to AI-generated result |
| `ranks_above` | `#f59e0b` (Amber) | 1.5 | No | Yes | "ranks" | Stage 2 ranking relationships |
| `synthesizes` | `#10b981` (Emerald) | 2 | Yes | No | "synthesizes" | Response cards to synthesis card |
| `related` | `#cbd5e1` (Light Slate) | 1 | No | Yes | *(none)* | General-purpose relationship. Default type for user-created connections. |

All edges render as bezier curves with an `ArrowClosed` marker on the target end. The `AnimatedEdge` component includes a transparent 20px-wide hit area for easier hover and selection.

---

## Card AI Actions

Right-click a card to open the context menu. AI actions send the card content (with board/project context prepended) to the chairman model and create new linked cards from the response.

Prompt templates are defined in `backend/council/card_prompts.py` (`CARD_AI_PROMPTS` dict).

| Action | Key | Description | Result |
|--------|-----|-------------|--------|
| Summarize | `summarize` | Condenses card content into 2-4 sentences. | Single new note card linked via `derived_from` edge. |
| Expand | `expand` | Adds detail, examples, evidence, and analysis to the card content. | Single new note card linked via `derived_from` edge. |
| Key Points | `key_points` | Extracts a structured bullet-point list of key facts and conclusions. | Single new note card linked via `derived_from` edge. |
| Ask Council | `ask_council` | Provides a multi-perspective analysis with counterarguments and implications. | Single new note card linked via `derived_from` edge. |
| Mind Map | `mind_map` | Breaks content into 3-6 sub-topics. Returns JSON array of `{title, content}`. | Multiple note cards fanned out below the source, each linked via `derived_from`. |
| Custom Prompt | `custom` | User enters a free-form prompt. The card content is appended as context. | Single new note card linked via `derived_from` edge. |

All result cards are positioned 250px below the source card. Mind map cards are horizontally distributed with 280px spacing, centered on the source card's x-position.

---

## Board AI Actions

Board-level AI actions operate on all cards (or only selected cards if any are selected). Triggered from the "AI" dropdown in the toolbar.

Prompt templates are defined in `backend/council/card_prompts.py` (`BOARD_AI_PROMPTS` dict).

| Action | Key | Description | Result |
|--------|-----|-------------|--------|
| Summarize Board | `summarize_board` | Generates a comprehensive summary capturing key themes and relationships across cards. | Creates a `council_synthesis` card positioned above the card cluster. |
| Cluster by Theme | `cluster_themes` | Groups cards into 2-6 thematic clusters. Returns JSON with cluster names, descriptions, and card ID lists. | Creates a label note card per cluster, applies matching colors to grouped cards, and creates `related` edges labeled "grouped". |
| Find Connections | `find_connections` | Identifies non-obvious connections between cards. Returns JSON array of `{from_id, to_id, label}`. | Creates `related` edges with descriptive labels between the identified card pairs. |

Cluster colors cycle through: `#6366f1`, `#f59e0b`, `#10b981`, `#ef4444`, `#3b82f6`, `#8b5cf6`.

---

## Council from Board

The toolbar "Council" button opens a modal (`BoardQueryInput`) to run a full 3-stage council deliberation using selected cards as context. The backend streams results via SSE and automatically creates cards and edges on the board when complete:

1. A `query` card for the user's question.
2. One `council_response` card per model, linked from the query via `derived_from` edges.
3. A `council_synthesis` card linked from each response via `synthesizes` edges.
4. `related` edges from each context card to the query card.
5. The synthesis is saved to board memory as a decision.

Options in the council modal:
- **Web Search** -- enables web search augmentation.
- **Fast Mode** -- skips Stage 2 ranking for faster results.
- **Cmd+Enter** -- submits the query.

---

## Keyboard Shortcuts

Shortcuts are registered globally by `useKeyboardShortcuts`. They are disabled when focus is inside an `INPUT` or `TEXTAREA` element.

| Key | Action |
|-----|--------|
| `N` | Create a new note card |
| `K` | Create a new knowledge card |
| `Delete` / `Backspace` | Delete selected cards and edges |
| `Escape` | Close modals, clear search, deselect all cards and edges, close context menu |
| `Cmd/Ctrl + A` | Select all cards |
| `Cmd/Ctrl + F` | Toggle board search panel |

Additional keyboard interactions within specific components:

| Context | Key | Action |
|---------|-----|--------|
| Card Editor | `Cmd/Ctrl + Enter` | Save edits |
| Card Editor | `Escape` | Cancel editing |
| Card Editor | `Cmd/Ctrl + P` | Toggle markdown preview |
| Board Search | `Enter` / `ArrowDown` | Next match |
| Board Search | `Shift+Enter` / `ArrowUp` | Previous match |
| Board Search | `Escape` | Close search |
| Council Modal | `Cmd/Ctrl + Enter` | Run council |
| Council Modal | `Escape` | Close modal |
| Board Memory | `Enter` | Add fact |
| Board Memory | `Escape` | Close panel |
| Context Menu (custom prompt) | `Enter` | Submit custom prompt |
| Context Menu (custom prompt) | `Escape` | Cancel custom prompt |

---

## Component Architecture

All components live under `frontend/src/modules/canvas/components/`. Barrel exports are in `frontend/src/modules/canvas/index.js`.

### Top-Level

| Component | File | Responsibility |
|-----------|------|----------------|
| `BoardView` | `BoardView.jsx` | Root component. Wraps the canvas in `ReactFlowProvider`. Orchestrates all hooks, renders the toolbar, search bar, context menu, council modal, memory panel, and the ReactFlow canvas. |
| `BoardList` | `BoardList.jsx` | Full-page board listing with create and delete. Entry point before opening a board. |

### Canvas Elements

| Component | File | Responsibility |
|-----------|------|----------------|
| `CanvasCard` | `CanvasCard.jsx` | Custom ReactFlow node. Renders card header (icon, type label, model name, collapse toggle), markdown content, backlinks section, thinking toggle for reasoning models, and overflow handling. Memoized with `React.memo`. |
| `AnimatedEdge` | `AnimatedEdge.jsx` | Custom ReactFlow edge. Renders bezier path with configurable stroke, dash pattern, animation, and an optional label. Includes a 20px transparent hit area. Memoized with `React.memo`. |
| `CardEditor` | `CardEditor.jsx` | Inline title+content editor for editable cards (`note`, `link`, `knowledge`). Supports markdown preview toggle, auto-resize textarea, blur-safe saving, and character count. |
| `SynthesisExpander` | `SynthesisExpander.jsx` | Collapsible drill-down inside `council_synthesis` cards. Shows Stage 1 individual responses with model pills, Stage 2 aggregate rankings with bar visualization, and a Stage 3 chairman label. |

### Toolbar and Panels

| Component | File | Responsibility |
|-----------|------|----------------|
| `BoardToolbar` | `BoardToolbar.jsx` | Top toolbar. Board name (click to rename), add card buttons (Note, Link, Knowledge), Council button with selection badge, AI actions dropdown, search toggle, memory toggle, and delete-selected button. |
| `CardContextMenu` | `CardContextMenu.jsx` | Right-click context menu for cards. Lists AI actions (summarize, expand, key points, ask council, mind map), custom prompt input, knowledge flag toggle (for note cards), "Discuss in Chat" via `CustomEvent`, and delete. |
| `BoardQueryInput` | `BoardQueryInput.jsx` | Modal overlay for running council from the board. Shows selected context card chips, query textarea, web search and fast mode toggles, and a progress bar during execution. |
| `BoardSearch` | `BoardSearch.jsx` | Search bar with text query input, card type filter dropdown, match counter with prev/next navigation, and keyboard navigation support. |
| `BoardMemoryPanel` | `BoardMemoryPanel.jsx` | Side panel for board memory. Tabbed interface with Facts (user-added, deletable) and Decisions (auto-saved from council runs). Supports add, delete, and clear-all operations. |
| `BoardPicker` | `BoardPicker.jsx` | Compact dropdown for selecting or creating a board. Used from the chat interface to send conversation turns to a board. |

---

## API Endpoints

All board endpoints are prefixed with `/api/boards` and require authentication.

### Board CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/boards` | List boards (optional `project_id` filter) |
| `POST` | `/api/boards` | Create a board |
| `GET` | `/api/boards/{board_id}` | Get board with all cards and edges |
| `PUT` | `/api/boards/{board_id}` | Update board name/description |
| `PATCH` | `/api/boards/{board_id}/viewport` | Save viewport (pan x/y, zoom) |
| `DELETE` | `/api/boards/{board_id}` | Delete board and all contents |

### Card CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/boards/{board_id}/cards` | List all cards on a board |
| `POST` | `/api/boards/{board_id}/cards` | Create a card |
| `PATCH` | `/api/boards/{board_id}/cards/{card_id}` | Update a card |
| `PATCH` | `/api/boards/{board_id}/cards/batch-positions` | Batch update card positions |
| `DELETE` | `/api/boards/{board_id}/cards/{card_id}` | Delete a card |

### Edge CRUD

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/boards/{board_id}/edges` | List all edges on a board |
| `POST` | `/api/boards/{board_id}/edges` | Create an edge |
| `DELETE` | `/api/boards/{board_id}/edges/{edge_id}` | Delete an edge |

### Chat-to-Canvas

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/boards/{board_id}/cards/from-message` | Create a card from a conversation message |
| `POST` | `/api/boards/{board_id}/cards/from-council-turn` | Bulk create cards from a full council turn (query + responses + synthesis + edges) |

### AI Actions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/boards/{board_id}/cards/{card_id}/ai-action` | Run AI action on a single card |
| `POST` | `/api/boards/{board_id}/ai-action` | Run board-level AI action |

### Board Memory

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/boards/{board_id}/memory` | Get board memory |
| `POST` | `/api/boards/{board_id}/memory` | Add fact, add decision, or clear memory |
| `DELETE` | `/api/boards/{board_id}/memory/facts/{fact_index}` | Delete a specific fact by index |

### Council from Board

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/boards/{board_id}/council` | Run council deliberation with board context. Returns an SSE stream. |
