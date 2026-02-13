# LLM Council Roadmap

## Milestones

- ✅ **v1.0 10/10 Polish** - Phases 1-10 (shipped 2026-01-20)
- ✅ **v1.1 Search & Analysis** - Phases 11-12 (shipped 2026-01-26)
- ✅ **v1.2 Document Processing** - Phase 13 (shipped 2026-01-29)
- ✅ **v2.0 Project System World-Class** - Phases 14-16 (shipped 2026-01-26)
- ✅ **v3.0 Council Canvas** - Phases 17-23 (shipped 2026-02-06)
- ✅ **v4.0 10/10 Cards** - Phases 24-27 (shipped 2026-02-05)
- ✅ **v4.1 Card Fixes** - Phase 28 (shipped 2026-02-07)
- ✅ **v5.0 Sections & Nested Boards** - Phases 29-30 (shipped 2026-02-08)
- ✅ **v6.0 Workflows & Agents** - Phases 31-32 (shipped 2026-02-09)
- ✅ **v9.0 Undo/Redo + Version History** (shipped 2026-02-09)
- ✅ **v9.1 Card Mentions + Block Types** (shipped 2026-02-09)
- ✅ **v10.0 Real-time Collaboration** (shipped 2026-02-09)
- ✅ **v11.0 Multi-step AI Flows** (shipped 2026-02-09)
- ✅ **v12.0 Properties, Tags, RAG & Asset Library** (shipped 2026-02-09)
- ✅ **v13.0 Template Marketplace** (shipped 2026-02-10)
- ✅ **v14.0 Export & Integrations** (shipped 2026-02-10)
- ✅ **v15.0 Performance** (shipped 2026-02-10)
- ✅ **v17.0 Visual LLM Pipeline Editor** (shipped 2026-02-10)
- ✅ **v19.0 Cross-Board Cards, Global Library, Auto-Layout, PDF Annotation** (shipped 2026-02-10)

## Domain Expertise

Tiptap/ProseMirror (rich text editor framework — Phase 24+)

---

<details>
<summary>✅ v2.0 Project System World-Class (Phases 14-16) - SHIPPED 2026-01-26</summary>

**Milestone Goal:** Transform the project system from 5/10 to world-class with proper security, DB-backed storage, LLM context injection, and unified UX.

### Phase 14: Security + DB Migration ✅
**Goal**: User-scoped projects with SQLAlchemy storage and ownership validation
**Status**: Complete
**Commit**: `02eba31`

### Phase 15: Context Injection ✅
**Goal**: Project context (system prompt, knowledge base, memory) flows into council/quick mode
**Status**: Complete

### Phase 16: UX Cohesion ✅
**Goal**: Single unified project experience across sidebar, panels, and views
**Status**: Complete

</details>

<details>
<summary>✅ v1.0-v1.2 (Phases 1-13) - SHIPPED</summary>

- Phase 1-10: Testing, error handling, OpenAPI docs, dark mode, cost estimation, progress indicators, API modularization, streaming cancellation, E2E tests, final polish
- Phase 11-12: Search & analysis improvements
- Phase 13: Document processing (PDF OCR, tiktoken, code-aware chunking)

</details>

---

## ✅ v3.0 Council Canvas (Phases 17-23) — SHIPPED 2026-02-06

**Milestone Goal:** Heptabase-quality infinite canvas where boards, cards, and council deliberation compose as modular building blocks. Every AI action = multi-model deliberation visible on the board.

**Design Language:** Heptabase-inspired — clean card surfaces, colored left accents, subtle shadows, strong typography hierarchy, pastel card-type tints, seamless dark mode.

**Architecture:** Modular — each feature is a self-contained module with its own components, hooks, API, and CSS. Modules communicate through well-defined interfaces. Any developer can own a module without reading the rest.

**Reference Plan:** `.planning/PLAN-council-canvas-v2.md`

## Phases

- [x] **Phase 17: Modular Refactor** - Split monoliths (main.py, ChatInterface) into module structure
- [x] **Phase 18: Heptabase-Style Cards** - Polished card design, inline editing, edge drawing, visual identity
- [x] **Phase 19: Council on Canvas** - Run council with card context, synthesis cards, board memory
- [x] **Phase 20: Search & Backlinks** - Cmd+F search, type filtering, backlink navigation
- [x] **Phase 21: Card AI & Board AI** - Per-card and per-board intelligent actions
- [x] **Phase 22: Chat ↔ Canvas Bridge** - Pin to board, discuss in chat, URL-based routing
- [x] **Phase 23: Polish & Developer Docs** - Performance, accessibility, testing, contributor guide

## Phase Details

### Phase 17: Modular Refactor
**Goal**: Split the monolithic files into the modular directory structure defined in PLAN-council-canvas-v2.md. No new features — purely structural.
**Depends on**: Nothing (first phase of v3.0)
**Research**: Unlikely (internal refactoring, established patterns)
**Plans**: 3 plans

Plans:
- [x] 17-01: Backend refactor — main.py 7,539→275 LOC, 14 route files, 201 unique routes
- [x] 17-02: Frontend refactor — modules/canvas/ (9 components), modules/chat/ (10 components), shared/ (9 components), barrel exports
- [x] 17-03: Hook extraction — BoardView 573→312 LOC (5 hooks), ChatInterface 2,714→1,415 LOC (7 hooks)

### Phase 18: Heptabase-Style Cards
**Goal**: Polished card rendering with Heptabase-quality visual design — clean surfaces, strong type hierarchy, color-coded card types with left accents and header tints, subtle shadows with depth, smooth editing UX.
**Depends on**: Phase 17
**Research**: Unlikely (CSS/React work, established React Flow patterns)
**Plans**: 4 plans

Plans:
- [ ] 18-01: Card visual redesign — Heptabase-style color system per card type with left accent + header gradient + body tint + shadow depth
- [ ] 18-02: Card typography & layout — Title hierarchy (14px/600), content truncation with expand, metadata footer, tag pills, card sizing presets
- [ ] 18-03: Inline editing polish — CardEditor.jsx extraction, blur-safe focus, auto-resize textarea, markdown preview toggle, keyboard shortcuts
- [ ] 18-04: Edge visual polish — Animated connection drawing, edge labels, edge type colors (synthesizes=green, derived=blue, related=gray), bezier curves

**Card Color System (Heptabase-inspired):**

```
┌─────────────────────────────────────────────────────────┐
│ Card Type       │ Left Accent  │ Header Tint       │ BG │
│─────────────────┼──────────────┼───────────────────┼────│
│ Note            │ #6366f1 Ind  │ indigo/4%         │ wh │
│ Knowledge       │ #8b5cf6 Vio  │ violet/6%         │ wh │
│ Query           │ #f59e0b Amb  │ amber/5%          │ wh │
│ Council Response│ #06b6d4 Cya  │ cyan/4%           │ wh │
│ Synthesis       │ #10b981 Emer │ emerald/6%        │ wh │
│ File Ref        │ #64748b Slat │ slate/4%          │ wh │
│ Link            │ #3b82f6 Blue │ blue/4%           │ wh │
└─────────────────────────────────────────────────────────┘

Shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)
Selected: + 0 0 0 2px accent-color/20%
Hover: shadow lifts to 0 4px 12px rgba(0,0,0,0.08)
Border-radius: 10px (body) + 10px 10px 0 0 (header)
Font: Inter / system-ui — Title: 14px/600, Body: 13px/400, Meta: 11px/500
```

### Phase 19: Council on Canvas
**Goal**: Full council loop — select cards → run council → synthesis card with edges + expandable Stage 1/2/3. Board memory (facts, decisions) injected into context.
**Depends on**: Phase 18
**Research**: Unlikely (council patterns established, extending existing board API)
**Plans**: 3 plans

Plans:
- [ ] 19-01: Council from board — BoardQueryInput modal, card selection UX, API call with card_ids, progress indicator during run
- [ ] 19-02: Synthesis cards & edges — Create council_synthesis card at center of selection, edges to source cards, SynthesisExpander component for Stage 1/2/3 drill-down
- [ ] 19-03: Board memory module — useBoardMemory hook, BoardMemoryPanel sidebar, add/delete facts+decisions, memory context injection into council prompts

### Phase 20: Search & Backlinks
**Goal**: Navigate large boards with Cmd+F search, type filtering, match highlighting. Show backlinks (incoming edges) on each card with focus navigation.
**Depends on**: Phase 19
**Research**: Unlikely (internal patterns, React Flow filtering)
**Plans**: 2 plans

Plans:
- [ ] 20-01: Board search — useBoardSearch hook, BoardSearch overlay (Cmd+F), text query + card type checkboxes, highlight matches + dim non-matches, arrow key navigation
- [ ] 20-02: Backlinks — useBacklinks hook to compute incoming edge map, BacklinksPanel in CanvasCard footer, click backlink → pan/focus source card, edge type colored tags

### Phase 21: Card AI & Board AI
**Goal**: AI-powered actions on individual cards (summarize, expand, mind map) and board-level actions (cluster themes, find connections, extract knowledge).
**Depends on**: Phase 20
**Research**: Likely (prompt engineering for card AI actions, layout algorithms for mind map/clustering)
**Research topics**: Radial layout algorithm for mind maps, force-directed layout for clustering, prompt templates for card summarization/expansion
**Plans**: 3 plans

Plans:
- [ ] 21-01: Card AI actions — Right-click AI submenu (summarize, expand, key points, questions, mind map), processing overlay on card, new cards positioned relative to source
- [ ] 21-02: Board AI actions — Toolbar dropdown (cluster themes, find connections, summarize board, extract knowledge, suggest next steps), board-wide processing state
- [ ] 21-03: AI layout engine — Radial layout for mind maps, force-directed clustering, smart card positioning after AI generates new cards

### Phase 22: Chat ↔ Canvas Bridge
**Goal**: Bidirectional flow between chat and canvas. Pin chat responses to boards, discuss board cards in chat. URL-based routing with deep links.
**Depends on**: Phase 21
**Research**: Unlikely (React Router patterns established, existing Pin-to-Board partially implemented)
**Plans**: 2 plans

Plans:
- [ ] 22-01: Cross-module actions — "Pin to Board" from Stage 3 / council responses, "Add to Board" from any message, "Discuss in Chat" from card context menu
- [ ] 22-02: URL-based routing — /chat/:id, /boards/:id, /projects/:id routes with browser back/forward, deep-linkable board URLs, replace state-based navigation

### Phase 23: Polish & Developer Docs
**Goal**: Performance optimization (100+ cards), accessibility (keyboard nav, WCAG AA), integration tests (Playwright), and developer documentation (ARCHITECTURE, CONTRIBUTING, HOOKS).
**Depends on**: Phase 22
**Research**: Unlikely (standard testing/docs patterns)
**Plans**: 3 plans

Plans:
- [ ] 23-01: Performance & accessibility — memo() on CanvasCard, virtualized off-screen cards, debounced batch saves, keyboard navigation (Tab/Enter/Space), WCAG AA color contrast
- [ ] 23-02: Integration tests — Playwright tests for: create board → add cards → run council → verify synthesis, card AI action flow, search/filter flow
- [ ] 23-03: Developer documentation — ARCHITECTURE.md (module structure, dependency rules), CONTRIBUTING.md ("add a card type in 5 files" walkthrough), CANVAS.md (card types, edge types), HOOKS.md (all custom hooks with examples)

---

## Progress Tracking (v3.0)

**Execution Order:**
Phases execute in numeric order: 17 → 18 → 19 → 20 → 21 → 22 → 23

| Phase | Plans Complete | Status | Completed |
|-------|---------------|--------|-----------|
| 17. Modular Refactor | 3/3 | Complete | 2026-02-06 |
| 18. Heptabase-Style Cards | 4/4 | Complete | 2026-02-06 |
| 19. Council on Canvas | 3/3 | Complete | 2026-02-06 |
| 20. Search & Backlinks | 2/2 | Complete | 2026-02-06 |
| 21. Card AI & Board AI | 3/3 | Complete | 2026-02-06 |
| 22. Chat ↔ Canvas Bridge | 2/2 | Complete | 2026-02-06 |
| 23. Polish & Developer Docs | 3/3 | Complete | 2026-02-06 |

**Total plans:** 20
**Architecture:** Modular (see PLAN-council-canvas-v2.md for full module structure)

---

## 🚧 v4.0 10/10 Cards (Phases 24-27)

**Milestone Goal:** Upgrade card editing from 4/10 to 10/10 Heptabase parity. Tiptap WYSIWYG editor, bubble toolbar, slash commands, task lists, image embedding, card linking, autosave, card templates.

**Architecture:** Self-contained `editor/` module inside `modules/canvas/`. All Tiptap code lives in `editor/` — no Tiptap imports leak into card components. Content stored as markdown (no data migration).

```
modules/canvas/editor/          ← NEW self-contained module
  TiptapEditor.jsx              ← Core WYSIWYG editor
  BubbleToolbar.jsx             ← Floating format bar on selection
  SlashMenu.jsx                 ← / command popup
  CardMention.jsx               ← [[ card linking popup
  ImageUpload.jsx               ← Paste/drop image handler
  CardTemplates.jsx             ← Template picker for new cards
  useAutoSave.js                ← Debounced autosave hook
  extensions.js                 ← Tiptap extension registry
  markdown-bridge.js            ← Markdown ↔ Tiptap conversion
  slash-commands.js             ← Command definitions array
  card-mention.js               ← Custom [[ extension
  image-upload.js               ← Custom image extension
  index.js                      ← Barrel export
  *.css                         ← Scoped styles per component
```

## Phases

- [x] **Phase 24: Rich Editor Core** — Tiptap install, WYSIWYG editor, bubble toolbar, swap CardEditor
- [x] **Phase 25: Card Interactions** — Single-click edit, slash commands, task lists, card resize
- [x] **Phase 26: Media & Linking** — Image paste/drop, `[[` card mentions, floating menu
- [x] **Phase 27: Card Polish** — Autosave, smooth transitions, templates, syntax highlighting, 10/10 finish

## Phase Details

### Phase 24: Rich Editor Core
**Goal**: Replace plain textarea with Tiptap WYSIWYG. Bubble toolbar on text selection. Zero data migration — markdown in, markdown out.
**Depends on**: Phase 23 (v3.0 complete)
**Research**: Likely (Tiptap React integration, markdown extension behavior)
**Plans**: 4 plans

Plans:
- [ ] 24-01: Install Tiptap + markdown bridge — packages, extension config, markdown-bridge.js, vite chunk
- [ ] 24-02: TiptapEditor component — useEditor hook, EditorContent, keyboard shortcuts, typography match
- [ ] 24-03: BubbleToolbar — floating format bar (Bold, Italic, Strike, Code, Link, H1-3, Lists, Quote)
- [ ] 24-04: CardEditor swap — replace textarea, remove preview toggle, verify markdown round-trip

### Phase 25: Card Interactions
**Goal**: Heptabase editing UX — single-click to edit, slash commands, task lists, card resize.
**Depends on**: Phase 24
**Research**: Likely (slash command extension patterns, resize interaction with ReactFlow)
**Plans**: 4 plans

Plans:
- [ ] 25-01: Single-click editing — click content area enters edit mode, distinguish from node selection
- [ ] 25-02: Slash commands — `/` trigger, searchable command list, keyboard navigation, category groups
- [ ] 25-03: Task lists + extended formatting — checkboxes, highlight, smart typography
- [ ] 25-04: Card resize — drag handle, 200-600px width, snap to grid, persist to DB

### Phase 26: Media & Linking
**Goal**: Image embedding (paste, drag-drop, URL) and card-to-card linking via `[[` syntax.
**Depends on**: Phase 25
**Research**: Likely (Supabase Storage upload, custom Tiptap mention extension)
**Plans**: 3 plans

Plans:
- [ ] 26-01: Image embedding — clipboard paste, drag-drop, upload to Supabase Storage, inline rendering
- [ ] 26-02: Card linking — `[[` trigger, card search popup, colored mention pills, click-to-navigate
- [ ] 26-03: Floating menu — `+` button on empty lines, block insertion options

### Phase 27: Card Polish
**Goal**: Final 10/10 finish — autosave, smooth view↔edit transitions, card templates, syntax highlighting.
**Depends on**: Phase 26
**Research**: Unlikely (established patterns)
**Plans**: 4 plans

Plans:
- [ ] 27-01: Autosave with conflict detection — 2s debounce, save indicator, retry on failure
- [ ] 27-02: Seamless view↔edit transition — fade animation, cursor placement, shadow elevation
- [ ] 27-03: Card templates — 6 presets (blank, meeting, decision, research, task, pros/cons)
- [ ] 27-04: Visual micro-polish — syntax highlighting, reading time, dark mode styles, accent cursors

---

## Progress Tracking (v4.0)

**Execution Order:**
Phases execute in order: 24 → 25 → 26 → 27

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 24. Rich Editor Core | 4/4 | Complete | 2026-02-05 |
| 25. Card Interactions | 4/4 | Complete | 2026-02-05 |
| 26. Media & Linking | 3/3 | Complete | 2026-02-05 |
| 27. Card Polish | 4/4 | Complete | 2026-02-05 |

**Total plans:** 15
**Architecture:** Self-contained `editor/` module (see phase dirs for full plans)

---

---

## ✅ v9.0 Undo/Redo + Version History — SHIPPED 2026-02-09

- **Undo/Redo**: Zustand `historyStore` (MAX_HISTORY=50), Ctrl/Cmd+Z / Ctrl/Cmd+Y keyboard shortcuts
- **Snapshots**: `BoardSnapshot` model, auto-snapshot on card edits (5-min debounce), safety snapshot before restore
- **Version History Panel**: Browse, restore, delete snapshots via `VersionHistoryPanel.jsx`
- Backend: 4 endpoints under `/api/boards/{board_id}/snapshots`

## ✅ v9.1 Card Mentions + Block Types — SHIPPED 2026-02-09

- **Card Mentions**: `[[` trigger with search popup, `CardMention` model, colored mention pills, click-to-navigate
- **Block Types**: Callout, math-block, embed editor extensions
- **Slash Commands**: Extended command definitions in `slash-commands.js`

## ✅ v10.0 Real-time Collaboration — SHIPPED 2026-02-09

- **WebSocket**: `/ws/boards/{board_id}` endpoint, board-scoped connections
- **Presence**: User profiles with avatars, connection timestamps, per-user colors
- **Remote Cursors**: Real-time cursor tracking with SVG overlay (`CollaborationOverlay.jsx`)
- **Reconnect**: Auto-reconnect with exponential backoff (max 10 attempts)
- **State**: Zustand `collaborationStore`, `useCollaboration` hook

## ✅ v11.0 Multi-step AI Flows — SHIPPED 2026-02-09

- **Workflow Engine**: Multi-step AI pipelines with 5 step types (council_query, ai_transform, combine, conditional, human_review)
- **Visual Builder**: `WorkflowBuilder.jsx`, `FlowGraph.jsx`, `WorkflowRunner.jsx`
- **Templates**: `WorkflowTemplateGallery.jsx` with research, analysis, content creation presets
- **Execution**: SSE streaming, step approval/cancellation, run history
- Backend: 8 endpoints, `Workflow`/`WorkflowStep`/`WorkflowRun` models

## ✅ v12.0 Properties, Tags, RAG & Asset Library — SHIPPED 2026-02-09

- **Properties System**: 9 editor types (text, number, select, multi-select, date, checkbox, url, email, relation)
  - `PropertyPanel.jsx`, `PropertyRow.jsx`, `PropertyDefinitionForm.jsx`, `PropertyBadge.jsx`
  - Zustand `propertyStore`, 5 backend endpoints
- **Tags**: `TagDatabase.jsx` sidebar panel, create/delete/colorize/search, `Tag`/`CardTag` models
- **RAG**: Document chunking + embedding, semantic search, per-project status
  - `DocumentChunk`/`KnowledgeLayer` models, 5 RAG endpoints, 7 layer endpoints
- **Asset Library**: `AssetBrowser.jsx` (images, documents, other), 5 backend endpoints

## ✅ v13.0 Template Marketplace — SHIPPED 2026-02-10

- **Marketplace UI**: `TemplateMarketplace.jsx` with category filtering, star ratings, tabs (board/workflow/prompt)
- **Board Templates**: Create from board, apply to board, `BoardTemplate`/`TemplateRating` models
- **Flow Templates**: `UserFlowTemplate` model, workflow template creation
- Backend: 6 board-template endpoints + marketplace listing

## ✅ v14.0 Export & Integrations — SHIPPED 2026-02-10

- **Export**: `ExportDialog.jsx` — Markdown, JSON, CSV, ZIP formats
- **Share Links**: Token-based public board sharing
- **Webhooks**: GitHub + Slack incoming webhook endpoints
- **Integrations Panel**: `IntegrationPanel.jsx` for managing connections

## ✅ v15.0 Performance — SHIPPED 2026-02-10

- **Monitoring**: `frontend/src/utils/monitoring.js` performance utilities
- **Debounced Positions**: `useDebouncedPositions` hook for canvas optimization
- **Lazy Loading**: Card attachments, heavy panels (`lazy()` + `Suspense`)
- **DB Pooling**: SQLAlchemy async connection pooling

## ✅ v15+ Additional Features (uncommitted) — IN PROGRESS

- **Card Attachments**: `CardAttachments.jsx`, `CardAttachment` model, CRUD + queries
- **Multi-View System**: `ViewContainer.jsx` switcher with 4 view types:
  - Canvas (default ReactFlow), Table (sortable columns), Kanban (swim lanes), Timeline (month/week/day zoom)
- **Claude Sidebar**: `ClaudeSidebar.jsx` AI assistant panel
- **Sidebar Tabs**: `SidebarTabs.jsx` with tag database, views, settings

## ✅ v17.0 Visual LLM Pipeline Editor — SHIPPED 2026-02-10

- **Pipeline Nodes = Cards**: 6 node types stored as Card rows with `pl_*` card_type values
  - `pl_input` (green), `pl_llm` (blue), `pl_council` (purple), `pl_transform` (orange), `pl_output` (gray), `pl_conditional` (yellow)
- **PipelineNode Component**: Compact 220px ReactFlow custom node with model selector, prompt template, status indicators, result preview
- **DAG Execution Engine**: `pipeline_engine.py` — Kahn's algorithm topological sort, per-node dispatch, conditional routing (TRUE/FALSE branches)
- **SSE Streaming**: Real-time progress events (node_start, node_complete, node_error, pipeline_complete)
- **Frontend Hook**: `usePipeline.js` — tracks per-node status/output, updates ReactFlow nodes live
- **Edge Auto-detection**: Connecting pl_* nodes auto-sets `edge_type: 'pipeline'`
- **Pipeline Palette**: 6 draggable node types in BoardToolbar dropdown + "Run Pipeline" button
- **Migration**: `0005_v17_pipeline_types.py` — CHECK constraints for new types (run `alembic upgrade head`)
- **Files**: 6 new (PipelineNode.jsx, PipelineNode.css, pipeline_engine.py, pipeline.py route, pipeline.js API, usePipeline.js), 6 modified

---

## Summary

**v1.0-v2.0 Complete** (Phases 1-16)
- 47 unit tests, retry logic, OpenAPI docs, dark mode
- Cost estimation, progress indicators, streaming cancellation
- Search & analysis, document processing
- Project system world-class (security, context injection, UX)

**v3.0 Complete** (Phases 17-23) — Council Canvas
- Modular refactor (main.py 7.5K→200 LOC), Heptabase-style cards, council on canvas
- Search & backlinks, card AI & board AI, chat-canvas bridge, polish & docs

**v4.0 Complete** (Phases 24-27) — 10/10 Cards
- Tiptap WYSIWYG, bubble toolbar, slash commands, task lists, card resize
- Image paste/drop, `[[` card mentions, autosave, templates, dark mode polish

**v4.1 Complete** (Phase 28) — Card Fixes
- Editor crash fix, position persistence, Heptabase card redesign

**v5.0 Complete** (Phases 29-30) — Sections & Nested Boards
- Section grouping, nested boards, breadcrumbs, inbox, journal, edge handles

**v6.0 Complete** (Phases 31-32) — Workflows & Agents
- Workflow engine, templates, autonomous agents, deploy (Vercel + Railway)

**v9.0** — Undo/Redo + Version History (snapshots, keyboard shortcuts)
**v9.1** — Card Mentions + Block Types (callout, math, embed)
**v10.0** — Real-time Collaboration (WebSocket, presence, remote cursors)
**v11.0** — Multi-step AI Flows (workflow builder, runner, templates)
**v12.0** — Properties (9 types), Tags, RAG + Knowledge Layers, Asset Library
**v13.0** — Template Marketplace (board/workflow/prompt, ratings)
**v14.0** — Export (4 formats) + Integrations (GitHub/Slack webhooks, share links)
**v15.0** — Performance (monitoring, lazy loading, debounced positions)
**v17.0** — Visual LLM Pipeline Editor (6 node types, DAG execution, SSE streaming)

---

## What's Next

### v18.0 — Candidates for Next Development

| Feature | Description | Complexity | Impact |
|---------|-------------|------------|--------|
| **Pipeline v2** | Typed sockets, sub-pipelines, node caching, JSON export/import | Medium | High |
| **Full Council Pipeline Node** | `pl_council` runs actual 3-stage deliberation (not just single LLM call) | Small | High |
| **Pipeline Templates** | Pre-built pipeline DAGs (research chain, content pipeline, analysis) | Small | Medium |
| **Mobile / Responsive** | Touch support, responsive canvas, mobile sidebar | Large | Medium |
| **Plugin System** | Custom node types, third-party integrations, extension API | Large | High |
| **AI Memory** | Cross-board memory, user preference learning, context carryover | Medium | High |
| **Collaboration v2** | Operational transform / CRDT for concurrent editing, edit locks | Large | Medium |
| **Advanced Views** | Gallery view, calendar view, graph/network view | Medium | Medium |
| **API Keys / Webhooks** | User-managed API keys, outbound webhooks, Zapier integration | Medium | Medium |
| **Testing** | E2E Playwright tests, integration tests, CI pipeline | Medium | High |
