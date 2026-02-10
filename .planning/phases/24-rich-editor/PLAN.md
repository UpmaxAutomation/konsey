# Phase 24: Tiptap Rich Editor Core

## Goal
Replace the plain textarea CardEditor with a Tiptap (ProseMirror) WYSIWYG editor. Zero data migration — content stays as markdown strings. Only one Tiptap instance active at a time (edit mode), read-only cards still use SafeMarkdown.

## Architecture

```
modules/canvas/
  editor/                        ← NEW module (self-contained)
    TiptapEditor.jsx             ← Core editor component (useEditor hook)
    TiptapEditor.css             ← Editor-specific styles (ProseMirror overrides)
    BubbleToolbar.jsx            ← Floating toolbar on text selection
    BubbleToolbar.css
    extensions.js                ← Extension registry (StarterKit + extras)
    markdown-bridge.js           ← toMarkdown() / fromMarkdown() helpers
    index.js                     ← Barrel export
```

**Dependency rule:** `editor/` imports from `@tiptap/*` only. No imports from `canvas/components/`. CardEditor.jsx imports from `editor/`.

## Plans

### 24-01: Install Tiptap + markdown bridge
- `npm install @tiptap/react @tiptap/pm @tiptap/starter-kit @tiptap/extension-placeholder @tiptap/extension-markdown`
- Create `editor/extensions.js` — configure StarterKit (bold, italic, strike, code, codeBlock, heading 1-3, bulletList, orderedList, blockquote, horizontalRule, hardBreak, history)
- Create `editor/markdown-bridge.js` — `toMarkdown(editor)` and `fromMarkdown(content)` wrappers around `@tiptap/extension-markdown`
- Add `vendor-tiptap` chunk to `vite.config.js` manualChunks
- Unit test: round-trip markdown → Tiptap → markdown preserves formatting

### 24-02: TiptapEditor component
- Create `editor/TiptapEditor.jsx` — wraps `useEditor` + `EditorContent`
- Props: `content` (markdown string), `onSave(markdown)`, `onCancel()`, `placeholder`, `autoFocus`
- Uncontrolled pattern: load content on mount, extract markdown on save
- `Cmd+Enter` saves, `Escape` cancels (same shortcuts as current CardEditor)
- `editor/TiptapEditor.css` — ProseMirror base styles, match existing card typography (Inter, 13px/400 body, 14px/600 title)

### 24-03: BubbleToolbar (floating format bar)
- Create `editor/BubbleToolbar.jsx` — appears on text selection
- Buttons: Bold, Italic, Strike, Code, Link, Heading 1-3, BulletList, OrderedList, Blockquote
- Each button shows active state (highlighted when format is applied)
- Compact pill design matching card accent colors
- `editor/BubbleToolbar.css` — dark floating bar, rounded, subtle shadow

### 24-04: CardEditor swap
- Replace textarea in `CardEditor.jsx` with `<TiptapEditor>`
- Remove markdown preview toggle (no longer needed — WYSIWYG is the preview)
- Keep title input as plain `<input>` (titles don't need rich text)
- Keep toolbar footer: character count, keyboard hints
- Preserve blur-safe focus behavior (save on focus-out)
- Verify: existing cards with markdown content load correctly in Tiptap
- Verify: saved content is still markdown string (no data format change)

## Acceptance Criteria
- [ ] Double-click card → Tiptap WYSIWYG editor opens
- [ ] Select text → floating toolbar appears with format buttons
- [ ] Bold, italic, headings, lists, code blocks work visually
- [ ] Cmd+Enter saves as markdown string to API (no format change)
- [ ] Existing markdown cards render correctly in Tiptap
- [ ] Build size increase < 200KB gzipped
- [ ] Only one Tiptap instance active at a time (no perf regression)
