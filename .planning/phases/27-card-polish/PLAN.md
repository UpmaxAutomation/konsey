# Phase 27: Card Polish & 10/10 Finish

## Goal
Final polish to reach Heptabase parity: smooth transitions between view/edit modes, undo/redo UX, autosave with conflict detection, card templates, and visual refinements. After this phase, cards are 10/10.

## Architecture

```
modules/canvas/
  editor/
    useAutoSave.js               ← NEW — debounced autosave hook
    CardTemplates.jsx            ← NEW — template picker for new cards
    CardTemplates.css
    extensions.js                ← MODIFY — add CharacterCount extension
  components/
    CanvasCard.jsx               ← MODIFY — seamless view↔edit transition
    CanvasCard.css               ← MODIFY — transition animations
    BoardToolbar.jsx             ← MODIFY — add card template dropdown
  hooks/
    useCardActions.js            ← MODIFY — template-aware card creation
```

## Plans

### 27-01: Autosave with conflict detection
- Create `editor/useAutoSave.js` hook:
  - Debounced save every 2 seconds while editing (not on every keystroke)
  - Saves via existing `stableUpdateCard` callback
  - Shows subtle "Saving..." / "Saved" indicator in card footer
  - On save failure: show error state, retry once, then show "Save failed" with manual retry button
  - On stale data (409 Conflict from API): show "Card modified elsewhere" with reload option
- Integrate into CardEditor.jsx — autosave replaces manual Cmd+Enter as primary save mechanism
- Cmd+Enter still works as explicit "save and close editor"
- Escape cancels unsaved changes (reverts to last saved state)

### 27-02: Seamless view↔edit transition
- Remove jarring switch between SafeMarkdown and Tiptap
- Approach: when entering edit mode, Tiptap loads with content pre-rendered at same position
- CSS transition: fade-in editor (opacity 0→1, 150ms) instead of abrupt swap
- Editor opens at the click position (cursor placed where user clicked)
- Card shadow elevates smoothly (current 1px → 8px over 200ms)
- Title and content preserve visual alignment between modes (same padding, font, line-height)

### 27-03: Card templates
- Create `editor/CardTemplates.jsx` — template picker dropdown
- Templates:
  - **Blank Note** — empty card (default)
  - **Meeting Notes** — pre-filled with Date, Attendees, Agenda, Action Items headings
  - **Decision** — Context, Options, Decision, Rationale headings
  - **Research** — Topic, Sources, Key Findings, Questions headings
  - **Task** — task list with checkboxes
  - **Pros/Cons** — two-column comparison
- Toolbar: "Add Note" button gets a dropdown arrow for template selection
- Templates are just pre-filled markdown content strings (no special handling needed)
- Keyboard shortcut: `N` creates blank note (unchanged), `T` opens template picker

### 27-04: Visual micro-polish
- Card focus ring animation: smooth scale-in (0→2px outline over 100ms)
- Content area subtle line grid (optional, togglable in toolbar)
- Word count → reading time estimate in footer ("~2 min read")
- Tiptap `CharacterCount` extension for accurate counts
- Improve code block rendering: syntax highlighting via `lowlight` + `@tiptap/extension-code-block-lowlight`
- Dark mode Tiptap styles: proper contrast for all formatting elements
- Cursor blink rate and selection color match card accent
- Print-friendly styles (hide toolbar, full content expansion)

## Acceptance Criteria
- [ ] Cards autosave every 2s while editing (no data loss)
- [ ] View→edit transition is smooth (no flash/jump)
- [ ] 6 card templates available from toolbar
- [ ] Code blocks have syntax highlighting
- [ ] Reading time shown in card footer
- [ ] Dark mode fully styled for all Tiptap elements
- [ ] "Saved" indicator appears after autosave
- [ ] Card editing feels native — no "I'm using an editor" friction
