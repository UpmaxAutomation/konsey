# Phase 26: Media Embedding & Card Linking

## Goal
Add image embedding (paste, drag-drop, URL) and card-to-card linking (`[[` syntax) to make cards first-class knowledge containers like Heptabase.

## Architecture

```
modules/canvas/
  editor/
    ImageUpload.jsx              ← NEW — image paste/drop/URL handler
    ImageUpload.css
    CardMention.jsx              ← NEW — [[ card link suggestion popup
    CardMention.css
    card-mention.js              ← NEW — Tiptap extension for [[ links
    image-upload.js              ← NEW — Tiptap extension for image handling
    extensions.js                ← MODIFY — register image + mention extensions
  components/
    CanvasCard.jsx               ← MODIFY — render card mentions as clickable links
    CanvasCard.css               ← MODIFY — image + mention inline styles

backend/
  routes/boards.py               ← MODIFY — image upload endpoint
  storage_adapter.py             ← MODIFY — store images (S3/Supabase Storage)
```

**Storage strategy:** Images upload to Supabase Storage (already configured). Backend returns a public URL. Card content stores `![alt](url)` markdown. No base64 blobs in the database.

## Plans

### 26-01: Image embedding
- Install `@tiptap/extension-image` (if not already via StarterKit)
- Create `editor/image-upload.js` — custom Tiptap extension:
  - Paste image from clipboard → upload to `/api/boards/{id}/images` → insert markdown
  - Drag-drop image file → same upload flow
  - `/image` slash command → URL input dialog
- Create `editor/ImageUpload.jsx` — upload progress indicator (inline, within card)
- Backend: `POST /api/boards/{board_id}/images` — accept multipart file, store in Supabase Storage, return `{ url }`
- Max file size: 5MB, accepted types: image/png, image/jpeg, image/gif, image/webp
- Images render inline in both edit mode (Tiptap) and view mode (SafeMarkdown — already supports `![](url)`)

### 26-02: Card linking (`[[` mentions)
- Create `editor/card-mention.js` — custom Tiptap extension using `@tiptap/suggestion`:
  - Trigger: `[[` keystroke
  - Fetches board cards via existing API (`getBoard` already returns all cards)
  - Shows filtered dropdown as user types card title
  - Inserts card link node: `[[Card Title|card_id]]`
- Create `editor/CardMention.jsx` — suggestion popup with card type icons and titles
- Rendering: card mentions appear as colored pills (accent color of linked card type)
- Click on mention → `stableFocusCard(cardId)` pans to that card
- In markdown storage: `[[Card Title|card_id]]` preserved as custom syntax
- SafeMarkdown: add custom remark plugin to render `[[...]]` as clickable links

### 26-03: Floating menu (empty line blocks)
- Install `@tiptap/extension-floating-menu`
- Create floating `+` button that appears on empty lines
- Shows same block options as slash menu (heading, list, code, image, task list)
- Compact icon-only design, appears left of the empty paragraph
- Optional — lower priority than slash commands (slash is the primary insertion pattern)

## Acceptance Criteria
- [ ] Paste image from clipboard → uploads and renders inline
- [ ] Drag-drop image onto card → uploads and renders
- [ ] Type `[[` → card search popup appears, select card → inserts link pill
- [ ] Click card mention → viewport pans to linked card
- [ ] Images persist as markdown `![](url)` — no data format change
- [ ] Card mentions persist as `[[Title|id]]` — survives round-trip
- [ ] Image upload size limit enforced (5MB)
