# Canvas Hooks Reference

All custom hooks live in `frontend/src/modules/canvas/hooks/`. They extract specific concerns from `BoardView` into composable, testable units.

---

## useBoardState

**File:** `useBoardState.js`

Manages board loading, saving, rename, and board memory (facts/decisions).

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `boardId` | `string` | The current board ID. Triggers a reload when it changes. |
| `setNodes` | `Function` | ReactFlow `setNodes` dispatcher. Called with loaded cards mapped through `cardToNode`. |
| `setEdges` | `Function` | ReactFlow `setEdges` dispatcher. Called with loaded edges mapped through `edgeToFlow`. |

### Return Value

| Property | Type | Description |
|----------|------|-------------|
| `board` | `Object \| null` | The loaded board object (name, description, viewport, memory, timestamps). |
| `setBoard` | `Function` | State setter for direct board updates. |
| `loading` | `boolean` | `true` while the board is being fetched. |
| `boardMemory` | `Object` | Board memory object: `{ facts: [], decisions: [], preferences: {} }`. |
| `setBoardMemory` | `Function` | State setter for direct memory updates. |
| `handleRenameBoard` | `Function(newName: string)` | Renames the board via API and updates local state. |
| `handleAddFact` | `Function(content: string)` | Adds a fact to board memory via API. |
| `handleDeleteFact` | `Function(factIndex: number)` | Deletes a fact by index via API. |
| `handleClearMemory` | `Function()` | Clears all board memory via API. |
| `memoryCount` | `number` | Total count of facts + decisions. |

### Example

```jsx
const {
  board, loading, boardMemory,
  handleRenameBoard, handleAddFact, handleDeleteFact, handleClearMemory, memoryCount,
} = useBoardState(boardId, setNodes, setEdges);

if (loading) return <Spinner />;
```

---

## useCardActions

**File:** `useCardActions.js`

Manages card CRUD operations and AI actions. Handles creating cards, inline editing, toggling the knowledge flag, and dispatching card-level AI actions.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `boardId` | `string` | The current board ID. |
| `nodes` | `Array` | Current ReactFlow nodes. Used by `handleToggleKnowledge` to read current card state. |
| `setNodes` | `Function` | ReactFlow `setNodes` dispatcher. |
| `setEdges` | `Function` | ReactFlow `setEdges` dispatcher. |

### Return Value

| Property | Type | Description |
|----------|------|-------------|
| `handleAddCard` | `Function(cardType: string)` | Creates a new card at a random position. Accepts `'note'`, `'link'`, or `'knowledge'`. |
| `stableUpdateCard` | `Function(cardId: string, updates: Object)` | Updates card title/content via API. Identity-stable (never changes reference) via a `useRef` wrapper, making it safe to pass into node data without triggering re-renders. |
| `handleToggleKnowledge` | `Function(cardId: string)` | Toggles `extra.is_knowledge` flag on a note card. |
| `handleCardAIAction` | `Function(cardId: string, action: string, customPrompt?: string)` | Runs an AI action on a card. Adds the card to `processingCards` during execution. Appends resulting cards and edges to the canvas. |
| `processingCards` | `Set<string>` | Set of card IDs currently being processed by an AI action. Cards in this set receive a `canvas-card--processing` CSS class. |
| `setProcessingCards` | `Function` | State setter for `processingCards`. |

### Example

```jsx
const {
  handleAddCard, stableUpdateCard, handleToggleKnowledge,
  handleCardAIAction, processingCards,
} = useCardActions(boardId, nodes, setNodes, setEdges);

// Create a note
handleAddCard('note');

// Run summarize on a card
handleCardAIAction(cardId, 'summarize');
```

---

## useEdgeActions

**File:** `useEdgeActions.js`

Manages edge connections and deletion of selected nodes and edges.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `boardId` | `string` | The current board ID. |
| `nodes` | `Array` | Current ReactFlow nodes. Used to compute `selectedNodes`. |
| `edges` | `Array` | Current ReactFlow edges. Used to compute `selectedEdges`. |
| `setNodes` | `Function` | ReactFlow `setNodes` dispatcher. |
| `setEdges` | `Function` | ReactFlow `setEdges` dispatcher. |

### Return Value

| Property | Type | Description |
|----------|------|-------------|
| `handleConnect` | `Function(connection: Object)` | Called when the user drags between node handles. Creates a `related` edge via API and adds it to the canvas. |
| `handleDeleteSelected` | `Function()` | Deletes all selected edges and nodes via API. Also removes orphaned edges when a node is deleted. |
| `selectedNodes` | `Array` | Memoized list of currently selected nodes. |
| `selectedEdges` | `Array` | Memoized list of currently selected edges. |

### Example

```jsx
const {
  handleConnect, handleDeleteSelected, selectedNodes, selectedEdges,
} = useEdgeActions(boardId, nodes, edges, setNodes, setEdges);

// Pass to ReactFlow
<ReactFlow onConnect={handleConnect} />

// Show delete button when items are selected
{selectedNodes.length > 0 && <button onClick={handleDeleteSelected}>Delete</button>}
```

---

## useDebouncedPositions

**File:** `useDebouncedPositions.js`

Manages debounced persistence of card positions (on drag) and viewport state (on pan/zoom). Prevents excessive API calls by batching position updates with a 500ms debounce and viewport saves with an 800ms debounce.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `boardId` | `string` | The current board ID. |
| `onNodesChange` | `Function` | ReactFlow's raw `onNodesChange` handler from `useNodesState`. |

### Return Value

| Property | Type | Description |
|----------|------|-------------|
| `handleNodesChange` | `Function(changes: Array)` | Wraps `onNodesChange`. Intercepts position changes (when `dragging` is `false`) and batches them for a debounced API call to `batchUpdateCardPositions`. |
| `handleMoveEnd` | `Function(event, viewport)` | Viewport move-end handler. Saves `{x, y, zoom}` to the backend after an 800ms debounce. |

### Implementation Details

- Position changes accumulate in a `pendingPositions` ref, keyed by node ID.
- After 500ms of inactivity, all pending positions are flushed in a single `batchUpdateCardPositions` API call.
- Viewport saves use a separate 800ms timer via `updateBoardViewport`.

### Example

```jsx
const { handleNodesChange, handleMoveEnd } = useDebouncedPositions(boardId, onNodesChange);

<ReactFlow
  onNodesChange={handleNodesChange}
  onMoveEnd={handleMoveEnd}
/>
```

---

## useKeyboardShortcuts

**File:** `useKeyboardShortcuts.js`

Registers global keyboard shortcuts for the board canvas. This is a side-effect-only hook that returns nothing.

### Parameters

Accepts a single options object:

| Property | Type | Description |
|----------|------|-------------|
| `selectedNodes` | `Array` | Currently selected nodes. |
| `selectedEdges` | `Array` | Currently selected edges. |
| `handleDeleteSelected` | `Function` | Delete selected elements. |
| `handleAddCard` | `Function` | Add a new card by type. |
| `showSearch` | `boolean` | Whether the search panel is currently open. |
| `setShowCouncilModal` | `Function` | Toggle the council modal. |
| `setShowSearch` | `Function` | Toggle the search panel. |
| `setHighlightedCards` | `Function` | Set search-highlighted card IDs. Typically a no-op since highlighting is derived from search state. |
| `setContextMenu` | `Function` | Set or clear the context menu. |
| `setNodes` | `Function` | ReactFlow `setNodes` dispatcher. |
| `setEdges` | `Function` | ReactFlow `setEdges` dispatcher. |
| `searchReset` | `Function` | Reset the board search state. |

### Return Value

None. This hook only registers and cleans up a `keydown` event listener.

### Registered Shortcuts

See the [Keyboard Shortcuts table in CANVAS.md](./CANVAS.md#keyboard-shortcuts) for the full list.

### Guard

All shortcuts are skipped when `e.target.tagName` is `INPUT` or `TEXTAREA`, preventing interference with text editing.

### Example

```jsx
useKeyboardShortcuts({
  selectedNodes, selectedEdges, handleDeleteSelected, handleAddCard,
  showSearch, setShowCouncilModal, setShowSearch,
  setHighlightedCards: () => {},
  setContextMenu, setNodes, setEdges, searchReset,
});
```

---

## useBoardSearch

**File:** `useBoardSearch.js`

Encapsulates board search logic including query filtering, card type filtering, and match navigation with wraparound.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `nodes` | `Array` | ReactFlow nodes to search through. Searches `data.title` and `data.content` fields. |

### Return Value

| Property | Type | Description |
|----------|------|-------------|
| `query` | `string` | Current search query string. |
| `setQuery` | `Function` | Update the search query. |
| `filterType` | `string` | Active card type filter. `'all'` matches any type. |
| `setFilterType` | `Function` | Update the type filter. |
| `matches` | `Array` | Memoized array of nodes matching both the query and type filter. Case-insensitive. |
| `matchIds` | `Array<string>` | Memoized array of matched node IDs. Used to derive `highlightedCards`. |
| `activeIndex` | `number` | Zero-based index of the currently focused match. |
| `activeMatchId` | `string \| null` | ID of the currently focused match, or `null` if no matches. |
| `goNext` | `Function` | Advance to the next match (wraps around). |
| `goPrev` | `Function` | Go to the previous match (wraps around). |
| `reset` | `Function` | Clear query, reset filter to `'all'`, and reset active index to 0. |

### How Highlighting Works

`BoardView` derives a `highlightedCards` set from `matchIds`. When this set is non-null, all non-matching cards receive `isDimmed: true` in their node data, applying the `canvas-card--dimmed` CSS class.

### Example

```jsx
const {
  query, setQuery, filterType, setFilterType,
  matches, matchIds, activeIndex, activeMatchId,
  goNext, goPrev, reset,
} = useBoardSearch(nodes);

// Navigate to active match
if (activeMatchId) {
  reactFlow.setCenter(matchNode.position.x, matchNode.position.y, { zoom: 1.2 });
}
```

---

## useBacklinks

**File:** `useBacklinks.js`

Computes a backlinks map from edges. For each target node, returns an array of incoming edge descriptions. Uses a `nodesRef` so that the memo only recomputes when edges change while always reading the latest node titles.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `edges` | `Array` | ReactFlow edges. The memo recomputes when this array changes. |
| `nodes` | `Array` | ReactFlow nodes. Used for title lookup but changes do not trigger recomputation (accessed via ref). |

### Return Value

| Type | Description |
|------|-------------|
| `Object<string, Array>` | Map of target node ID to an array of backlink entries. |

Each backlink entry has the shape:

```js
{
  edgeType: string,    // e.g. "derived_from", "synthesizes", "related"
  sourceTitle: string, // Title of the source node, or card_type, or "Card"
  sourceId: string,    // ID of the source node
}
```

### How Backlinks are Displayed

`CanvasCard` receives `backlinks` via its `data` prop. When backlinks exist, a collapsible section appears at the bottom of the card showing the count and a list of linked cards. Clicking a backlink item calls `data.onFocusCard(sourceId)` to pan the viewport to that card.

### Example

```jsx
const backlinksMap = useBacklinks(edges, nodes);

// Inject into node data
setNodes(nds => nds.map(n => ({
  ...n,
  data: { ...n.data, backlinks: backlinksMap[n.id] || [] },
})));
```
