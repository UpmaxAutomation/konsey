# Phase 25: Card Interactions & Editing UX

## Goal
Match Heptabase editing UX: single-click to edit, slash commands for block insertion, task lists (checkboxes), and keyboard-driven formatting. Make cards feel like native note-taking surfaces.

## Architecture

```
modules/canvas/
  editor/
    SlashMenu.jsx                ← NEW — slash command popup
    SlashMenu.css
    slash-commands.js             ← NEW — command definitions registry
    extensions.js                 ← MODIFY — add TaskList, TaskItem, Highlight, Typography
  components/
    CanvasCard.jsx               ← MODIFY — single-click edit trigger
    CanvasCard.css               ← MODIFY — task list checkbox styles
```

**Modular command registry:** `slash-commands.js` exports an array of command objects. Each command has `{ title, icon, description, aliases, command(editor) }`. Adding a new slash command = adding one object to the array.

## Plans

### 25-01: Single-click editing
- Change edit trigger from double-click to single-click on card content area
- Double-click on title selects title text (standard behavior)
- Click on non-editable cards (query, council_response, etc.) does nothing
- Clicking outside the card content area still allows drag/selection
- Key challenge: distinguish "click to edit" from "click to select node" — only content area clicks trigger editing, header/footer clicks don't

### 25-02: Slash commands
- Install `@tiptap/suggestion` (slash command engine)
- Create `editor/slash-commands.js` — command registry:
  - Heading 1/2/3
  - Bullet List / Ordered List / Task List
  - Code Block
  - Blockquote
  - Horizontal Rule
  - Image (placeholder — insert from URL)
  - Callout (custom node — info/warning/tip box)
- Create `editor/SlashMenu.jsx` — dropdown popup at cursor position
  - Fuzzy search filtering as user types after `/`
  - Arrow key navigation + Enter to select
  - Escape to close
  - Grouped by category (Text, Lists, Media, Advanced)
- `editor/SlashMenu.css` — compact dropdown matching card design language

### 25-03: Task lists + extended formatting
- Install `@tiptap/extension-task-list @tiptap/extension-task-item @tiptap/extension-highlight @tiptap/extension-typography`
- Add to `extensions.js` registry
- Task lists: clickable checkboxes, strikethrough on completed items
- Highlight: `==text==` syntax, yellow highlight
- Typography: smart quotes, em-dashes, ellipsis
- CSS for task checkboxes in `.canvas-card__content` (both edit and view mode)

### 25-04: Card resize
- Add drag handles to bottom-right corner of cards
- On resize, update node `style.width` and persist via card update API
- Min width: 200px, max width: 600px
- Height: auto (content-driven), no manual height control
- Snap to 16px grid (matches existing snap grid)
- Save width to DB via existing `updateCard` endpoint (width field exists in Card model)

## Acceptance Criteria
- [ ] Single click on card content enters edit mode
- [ ] Type `/` → slash menu appears with searchable commands
- [ ] Task lists render with clickable checkboxes
- [ ] Cards are resizable via drag handle (200-600px width)
- [ ] Highlight and smart typography work
- [ ] No regression on drag/select card interactions
