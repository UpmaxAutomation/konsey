# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-23)

**Core value:** Heptabase-quality canvas + council deliberation as composable modules
**Current focus:** All milestones complete (v1.0-v6.0), deployed to production

## Current Position

Milestone: v6.0 Workflows & Agents
Phase: 32 (Deploy)
Plan: Complete
Status: Deployed
Last activity: 2026-02-09 — v6.0 deployed (Vercel + Railway)

Progress: v1.0-v6.0 complete and deployed

## Performance Metrics

**Velocity:**
- Total plans completed: 27 phases (v1.0-v4.0)
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| v1.0 (1-10) | 10 | — | — |
| v1.1 (11-12) | 2 | — | — |
| v1.2 (13) | 1 | — | — |
| v2.0 (14-16) | 3 | — | — |
| v3.0 (17-23) | 7 | — | — |
| v4.0 (24-27) | 4 | — | — |

## Accumulated Context

### Decisions

- React Flow chosen over Tldraw (node graph model fits cards+edges better)
- Modular architecture: modules/canvas/, modules/chat/, shared/
- Heptabase-inspired card design: left accents, header tints, Inter font
- Knowledge cards use extra.is_knowledge flag (no migration needed)
- Board memory mirrors project memory pattern (facts, decisions, preferences)
- No Redux/Zustand — React Context + useReducer for feature state
- File size limits: 300 LOC components, 150 LOC hooks
- URL-based routing for boards (/boards, /boards/:id) via React Router
- Event-based cross-module communication (discussCardInChat, openBoards)
- useBoardSearch/useBacklinks extracted as standalone hooks
- Card AI actions: summarize, expand, key_points, ask_council, mind_map, custom
- Board AI actions: summarize_board, cluster_themes, find_connections
- Tiptap chosen for rich text editing (ProseMirror-based, markdown I/O)
- Single editor instance pattern (only editing card has Tiptap, view uses SafeMarkdown)
- Content stored as markdown strings — no data migration needed
- Self-contained editor/ module — no Tiptap imports leak into card components
- BubbleMenuPlugin registered imperatively (tiptap v3 has no React wrapper)
- Card mentions stored as [[Title|id]] in markdown
- Autosave: 2s debounce with status indicator
- Card templates: 6 presets as markdown strings
- Zustand chosen for workflow/agent state (simpler than Redux for isolated stores)
- Workflow engine uses streaming SSE for real-time step progress
- Agent system: goal → plan → iterate → create cards loop
- Deploy: Vercel for frontend (SPA + API proxy), Railway for backend (Docker)

### Deferred Issues

None.

### Blockers/Concerns

- ~~main.py at 7,539 LOC~~ — Resolved in Phase 17 (now 275 LOC + 14 route files)
- ~~ChatInterface at 2,714 LOC~~ — Resolved in Phase 17 (now 1,415 LOC + 7 hooks)
- ~~Card editing 4/10~~ — Resolved in v4.0 (Tiptap WYSIWYG, 10/10)

## Session Continuity

Last session: 2026-02-09
Stopped at: v6.0 deployed to production
Resume file: N/A (project shipped)

## Environment

- Database: Supabase (PostgreSQL)
- Backend: FastAPI (port 8001)
- Frontend: React 19 + Vite (port 5173)
- Deployment: Vercel (frontend), Railway (backend)

## Quick Reference

**All milestones complete:**
- v1.0 (Phases 1-10): Testing, error handling, dark mode, streaming, polish
- v1.1 (Phases 11-12): Search & analysis
- v1.2 (Phase 13): Document processing
- v2.0 (Phases 14-16): Project system (security, context injection, UX)
- v3.0 (Phases 17-23): Council Canvas
- v4.0 (Phases 24-27): 10/10 Cards
- v4.1 (Phase 28): Card fixes
- v5.0 (Phases 29-30): Sections, nested boards, inbox, journal
- v6.0 (Phases 31-32): Workflows, agents, deploy

**v4.0 deliverables:**
- Phase 24: Rich Editor Core (Tiptap, BubbleToolbar, extensions registry, markdown bridge)
- Phase 25: Card Interactions (single-click edit, slash commands, task lists, highlight, card resize)
- Phase 26: Media & Linking (image paste/drop, [[ card mentions, floating add menu)
- Phase 27: Card Polish (autosave, smooth transitions, 6 templates, dark mode, reading time)

**Editor module files (modules/canvas/editor/):**
- TiptapEditor.jsx — Core WYSIWYG editor (useEditor, EditorContent, paste/drop handlers)
- BubbleToolbar.jsx — Floating format bar (12 buttons: B/I/S/Code/Hi | H1/H2/H3 | List/1./"/\<\>)
- FloatingAddMenu.jsx — "+" button on empty lines with block palette
- SlashMenu.jsx — "/" command dropdown (10 commands, 3 categories)
- CardMention.jsx — "[[ card linking suggestion popup
- CardTemplates.jsx — 6 template definitions
- useAutoSave.js — 2s debounced autosave with status
- extensions.js — Extension registry (StarterKit, Placeholder, Link, Markdown, TaskList, TaskItem, Highlight, Typography, Image, CharacterCount, SlashCommands, CardMentionNode)
- slash-commands.js — Command definitions array (H1-3, lists, code, quote, hr, highlight, image)
- slash-extension.js — Tiptap suggestion plugin wiring
- card-mention.js — Custom [[ node extension
- markdown-bridge.js — toMarkdown(), isEditorEmpty() utils
- index.js — Barrel exports
