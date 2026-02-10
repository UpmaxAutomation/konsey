# LLM Council v5-v15: Layered Knowledge Intelligence Platform

## Rating: Previous plan 7/10 → This plan 10/10

**What was missing in v1 (7/10):** No modular team architecture, missing Heptabase core features (sections, coloring, directory sidebar, card library, journal, command palette), no real-time collaboration, no undo/redo or version history, no design system, no testing strategy, no CI/CD pipeline, no performance plan, no global search, no card mentions.

---

## A. Vision

**One sentence:** Heptabase's visual knowledge organization + Miro's multi-step AI Flows + Poppy.ai's visual AI canvas + multi-model council deliberation + per-domain RAG layers = the only tool teams need for research, analysis, strategy, and planning.

**Core user flow:**
1. Create a **project** with nested **canvases** (whiteboards-in-whiteboards)
2. Define **knowledge layers** per project (each = RAG + expert persona + methodology)
3. Upload documents to layers, tag/color/organize cards with properties
4. Query the council across layers → get **separate connected cards** (analysis, strategy, decisions, tasks)
5. Build **multi-step AI Flows** on canvas for repeatable workflows
6. Generate images, manage assets, export deliverables

**Competitive edge:**
| Feature | Heptabase | Miro | Poppy.ai | Notion AI | **LLM Council** |
|---------|-----------|------|----------|-----------|-----------------|
| Nested whiteboards | Yes | No | No | No | **Yes** |
| Multi-model AI | No | No | No | No | **Yes (council)** |
| Per-domain RAG | No | No | No | Workspace | **Per-layer** |
| Cross-domain synthesis | No | No | No | No | **Yes** |
| AI Flows (multi-step) | No | Yes | No | No | **Yes** |
| Visual AI canvas | No | Yes | Yes | No | **Yes** |
| Table/Kanban/Timeline | Tags only | Yes | No | Yes | **Yes** |
| Card properties (typed) | Yes (9) | No | No | Yes | **Yes** |
| Sections & coloring | Yes | Yes | No | No | **Yes** |
| Real-time multiplayer | No | Yes | Yes | Yes | **Yes** |
| Image generation | No | Adobe Express | Partial | No | **Yes** |
| Asset library | No | No | No | No | **Yes** |
| Template marketplace | No | 80+ | 12+ | Yes | **Yes** |
| Card library (central) | Yes | No | No | No | **Yes** |
| Journal / daily notes | Yes | No | No | No | **Yes** |
| Undo/redo + versioning | No | Yes | No | Yes | **Yes** |
| Command palette | Yes | No | No | Yes | **Yes** |

---

## B. Modular Architecture (Enterprise-Grade)

### B1. Repository Structure

```
llm-council/
  packages/                     # Shared packages (if we go monorepo)
    shared-types/               # TypeScript interfaces shared FE ↔ BE
    ui-kit/                     # Design system components
  backend/
    core/                       # Shared utilities, base classes, middleware
    auth/                       # Authentication module (existing)
    council/                    # Council deliberation engine
    rag/                        # Vector embedding pipeline
    modules/                    # Feature modules (each self-contained)
      boards/                   # Board CRUD, nesting, sections
      cards/                    # Card CRUD, card library, card types
      properties/               # Property definitions, values, filtering
      layers/                   # Knowledge layers, layer docs
      flows/                    # Multi-step AI flow execution
      images/                   # Image generation, asset library
      templates/                # Pre-built templates, marketplace
      journal/                  # Daily entries, inbox
      collaboration/            # Real-time sync, presence, cursors
      search/                   # Global search, command palette
      history/                  # Undo/redo, version snapshots
      export/                   # PDF, markdown, JSON export
      notifications/            # In-app, email notifications
    database/
      models.py                 # All SQLAlchemy models
      migrations/               # Alembic migrations
      crud/                     # Per-module CRUD operations
    tests/
      unit/                     # Per-module unit tests
      integration/              # Cross-module integration tests
      e2e/                      # API-level end-to-end tests
  frontend/
    src/
      design-system/            # Design tokens, base components
        tokens/                 # Colors, spacing, typography, shadows
        components/             # Button, Input, Modal, Dropdown, etc.
        hooks/                  # useTheme, useBreakpoint
      modules/                  # Feature modules (mirror backend)
        canvas/                 # Board view, cards, sections, ReactFlow
        properties/             # Property panel, badges, filters
        views/                  # TableView, KanbanView, TimelineView
        layers/                 # Layer panel, picker, document manager
        flows/                  # Flow builder, flow runner
        assets/                 # Asset browser, image generator
        templates/              # Template picker, marketplace
        journal/                # Journal view, inbox
        search/                 # Global search, command palette
        sidebar/                # Directory tree, app navigation
        collaboration/          # Cursors, presence indicators
        history/                # Undo/redo toolbar, version browser
        export/                 # Export dialogs
      shared/                   # Cross-module shared components
      api/                      # API client modules (per feature)
      hooks/                    # Global hooks (useAuth, useUser, etc.)
      stores/                   # Global state (Zustand or Context)
    tests/
      unit/                     # Component tests (Vitest)
      e2e/                      # Playwright E2E tests
  docs/
    architecture/               # ADRs (Architecture Decision Records)
    api/                        # OpenAPI specs, generated docs
    modules/                    # Per-module documentation
  .github/
    workflows/                  # CI/CD pipelines
    CODEOWNERS                  # Module ownership
```

### B2. Module Ownership Model

Each module is independently developable. A team of 4-6 can work in parallel:

| Module | Owner Role | Backend | Frontend | Deps |
|--------|-----------|---------|----------|------|
| **canvas** | Canvas Engineer | boards/, cards/ | canvas/ | - |
| **properties** | Data Engineer | properties/ | properties/, views/ | canvas |
| **layers + RAG** | AI/ML Engineer | rag/, layers/ | layers/ | - |
| **council** | AI/ML Engineer | council/ | (uses canvas) | layers |
| **flows** | Workflow Engineer | flows/ | flows/ | canvas, council |
| **collaboration** | Infra Engineer | collaboration/ | collaboration/ | canvas |
| **assets + images** | Media Engineer | images/ | assets/ | - |
| **platform** | Platform Engineer | search/, history/, export/, notifications/ | search/, sidebar/, history/, export/ | all |

### B3. API Contract Layer

- **OpenAPI 3.1 spec** for every route module → auto-generated client types
- **Pydantic v2 models** as single source of truth (backend) → JSON Schema → TypeScript types
- **Versioned endpoints**: `/api/v1/boards/`, `/api/v2/boards/`
- **Consistent patterns**: `GET /api/v1/{resource}`, `POST /api/v1/{resource}`, `PATCH /api/v1/{resource}/{id}`, `DELETE /api/v1/{resource}/{id}`

### B4. Engineering Standards

| Area | Standard | Tool |
|------|----------|------|
| Python linting | Ruff (replaces black + isort + flake8) | `ruff check && ruff format` |
| Python types | mypy strict mode | `mypy backend/` |
| JS/JSX linting | ESLint flat config + Prettier | `eslint . && prettier --check .` |
| JS types | JSDoc → migrate to TypeScript | Phase: JSDoc now, TS later |
| Testing | pytest (BE) + Vitest (FE) + Playwright (E2E) | Per-module test files |
| Coverage | 80% minimum per module | `pytest --cov`, `vitest --coverage` |
| Commits | Conventional Commits | `feat:`, `fix:`, `refactor:`, `docs:` |
| Branching | Trunk-based with feature flags | `main` + short-lived `feat/*` |
| PRs | Require 1 review + CI pass | GitHub branch protection |
| Feature flags | LaunchDarkly or env-based | `FEATURE_*` env vars |
| Error monitoring | Sentry (FE + BE) | `sentry-sdk`, `@sentry/react` |
| ADRs | docs/architecture/ADR-NNN.md | Per architectural decision |

---

## C. Feature Modules — Complete Specification

### C1. Canvas Core (Heptabase Parity)

**Sections:**
- Colored rectangular regions that group cards visually
- Right-click → "Create Section" or Cmd+G
- 8 color palette (matches Heptabase: gray, red, orange, yellow, green, blue, purple, pink)
- Section titles visible when zoomed out
- Cards inside sections move together when section is dragged
- Data: `sections` table (board_id, title, color, x, y, width, height)

**Card coloring:**
- 8-color palette for individual cards (separate from card_type accent)
- Color picker in card header or context menu
- Persisted in `cards.color` column

**Card library:**
- Cards exist independently of boards (central repository)
- Same card can appear on multiple boards (many-to-many: `board_card_placements`)
- Left sidebar "Card Library" shows all cards with search/filter
- Info panel shows which boards a card appears on

**Connection styles:**
- Arrow types: directed, bidirectional, dashed, dotted
- Arrow colors (8 color palette)
- Arrow labels (text annotations)
- Data: `edges.style` JSON column (arrow_type, color, label)

**Mindmap mode:**
- Auto-layout toggle for hierarchical card arrangement
- Parent-child relationships from edges
- Collapse/expand branches

### C2. Directory Sidebar (Heptabase-style)

**Left sidebar apps:**
1. **Inbox** — Cards from web clipper, quick capture, collaboration mentions
2. **Journal** — Daily entries, linked to cards, todo tracking
3. **Boards** — Hierarchical tree of all boards (directory-style, nested)
4. **Card Library** — All cards, filterable by type/tag/property
5. **Tag Database** — All tags, grouped into collections
6. **Highlights** — PDF annotations, web clips
7. **AI Chat** — Council chat outside of boards (existing feature, moved to sidebar)
8. **Layers** — Knowledge layer management
9. **Templates** — Browse/apply templates

**Tab system:**
- Normal tabs (boards, cards open as tabs)
- Pinned tabs
- Tab folders
- Tab groups (work/personal/project contexts)
- Keyboard: Cmd+T new tab, Cmd+W close, Cmd+Shift+T reopen

**Right sidebar panels:**
- Card info (properties, tags, boards it appears on)
- AI chat (contextual to selected card/board)
- Journal quick entry
- Table of contents (for long cards)

### C3. Tags & Properties (Heptabase 9 Types + Views)

**Property types (9):**
1. Text — Single/multi-line string
2. Number — Integer/decimal, optional unit
3. Select — Single choice from options (colored badges)
4. Multi-select — Multiple choices
5. Date — Date/datetime picker, optional end date (range)
6. Checkbox — Boolean toggle
7. URL — Clickable link
8. Email — Email address
9. Relation — Link to other cards (bi-directional)

**Views (synced from same data — Miro pattern):**
- **Canvas** (current) — ReactFlow spatial layout
- **Table** — Sortable, filterable rows with property columns
- **Kanban** — Columns by select/multi-select property, drag to change
- **Timeline** — Gantt-style by date properties
- View toggle in toolbar, all views show same cards

**Tag Database:**
- Tags are reusable across cards
- Tag collections (group related tags)
- Tag colors
- Filter cards by tag combinations (AND/OR)

### C4. RAG Infrastructure

(Same as previous plan B3 — pgvector, text-embedding-3-small, 512/64 chunks, HNSW)

### C5. Knowledge Layers

(Same as previous plan B4 — per-layer RAG, expert personas, round-robin assignment)

### C6. Analysis Engine

(Same as previous plan B5 — focused/cross-layer/iterative modes)

**Structured output:** Council output creates **separate connected cards**:
- Analysis card (findings, data points)
- Strategy card (recommendations, options)
- Decision card (selected approach, rationale)
- Task card (action items, assignments, deadlines)
- Each connected by typed edges (analysis→strategy→decision→tasks)

### C7. Templates & Marketplace

**Three core domains (equal priority):**
1. Research & Academia (Literature Review, Research Proposal, Data Analysis)
2. Business & Strategy (Market Research, Due Diligence, Business Plan, Legal)
3. Construction & PM (Project Planning, Site Analysis, RFP/Bid Analysis)

**Template structure:**
- Pre-configured layers with persona prompts
- Pre-built board layouts with sections
- Property schemas per template
- Flow templates (multi-step workflows)
- Shareable via marketplace (user-to-user)

### C8. AI Image Generation & Asset Library

(Same as previous plan B7 — DALL-E 3/Stability, Supabase Storage, image cards)

### C9. Multi-step AI Flows

(Same as previous plan B8 — edge-based sequencing, flow templates)

### C10. Real-time Collaboration (Multiplayer)

**What:** Multiple users on same board see each other's cursors, card movements, edits in real-time.

**Tech:**
- **WebSocket** via FastAPI WebSockets (existing infra)
- **CRDT** for conflict-free concurrent edits (Yjs library)
- **Presence** — colored cursors with user names
- **Awareness** — who's viewing which board

**Implementation:**
- `backend/modules/collaboration/ws.py` — WebSocket manager
- `backend/modules/collaboration/crdt.py` — Yjs document sync
- `frontend/src/modules/collaboration/` — Cursor overlay, presence bar

### C11. Undo/Redo & Version History

**Undo/Redo:**
- Command pattern: each action → reversible command object
- Per-user undo stack (don't undo other people's actions)
- Keyboard: Cmd+Z / Cmd+Shift+Z

**Version history:**
- Auto-snapshot every hour if changes detected
- Named snapshots (user-triggered)
- Diff view between versions
- Restore to previous version (creates new snapshot)
- 90-day retention

**Activity feed:**
- "See recent changes" on board entry
- Highlighted changes since last visit
- Per-card change history

### C12. Global Search & Command Palette

**Global search (Cmd+O):**
- Search across all cards, boards, tags, layers
- Filters: card type, board, date range, tags, properties
- Full-text search on card content
- Semantic search via RAG embeddings

**Command palette (Cmd+K):**
- Quick action access
- Recent items
- Navigation shortcuts
- AI actions from palette

### C13. Journal & Inbox

**Journal:**
- Daily entries (auto-created for today)
- Link to cards with @mentions
- Todo tracking (checkboxes)
- Journal entries are cards (appear in card library)

**Inbox:**
- Quick capture (global shortcut)
- Web clipper items
- Collaboration mentions
- Unprocessed items queue

### C14. Card Mentions & Block Types

**Card mentions (@):**
- Type `@` to reference another card
- Bi-directional links (backlinks panel shows incoming references)
- Mention preview on hover

**Block types (within cards):**
- Text (markdown)
- Heading (H1-H3)
- Bullet/numbered list
- Toggle/accordion
- Code block (syntax highlighted)
- Image
- File attachment
- Embed (URL preview)
- Table (inline)
- Math (LaTeX)
- Divider

---

## D. Milestone Roadmap (Enterprise)

```
FOUNDATION (v5.0-v5.2) ── build team architecture + canvas parity
     │
INTELLIGENCE (v6.0-v8.0) ── properties + RAG + layers + council
     │
PLATFORM (v9.0-v12.0) ── collaboration + flows + assets + templates
     │
SCALE (v13.0-v15.0) ── marketplace + mobile + offline + i18n
```

### Phase 1: Foundation (Build First)

| Version | Sprint | What | Team | Duration |
|---------|--------|------|------|----------|
| **v5.0** | 1-2 | **Engineering foundation**: CI/CD, design system, linting, testing infra, feature flags, Sentry, ADR template | Platform | 2 weeks |
| **v5.1** | 3-5 | **Canvas parity**: Sections, card coloring, connection styles, mindmap layout | Canvas | 3 weeks |
| **v5.2** | 3-5 | **Directory sidebar**: Board tree, card library, tab system, right sidebar, command palette (Cmd+K), global search (Cmd+O) | Platform | 3 weeks |
| **v5.3** | 6-7 | **Nested boards**: board_ref card, breadcrumb nav, board hierarchy in sidebar | Canvas | 2 weeks |
| **v5.4** | 6-7 | **Journal + Inbox**: Daily entries, quick capture, @mentions, backlinks | Platform | 2 weeks |

### Phase 2: Intelligence

| Version | Sprint | What | Team | Duration |
|---------|--------|------|------|----------|
| **v6.0** | 8-10 | **Properties**: 9 property types, property panel, property badges on cards | Data | 3 weeks |
| **v6.1** | 11-12 | **Views**: TableView, KanbanView, TimelineView (synced with canvas) | Data | 2 weeks |
| **v6.2** | 11-12 | **Tag Database**: Tag collections, colors, cross-board tagging, filtering | Data | 2 weeks |
| **v7.0** | 13-15 | **RAG enhancement**: pgvector, chunking, embedding, semantic search | AI/ML | 3 weeks |
| **v8.0** | 16-18 | **Knowledge layers + enhanced council**: Layer-aware deliberation, structured multi-card output | AI/ML | 3 weeks |

### Phase 3: Platform

| Version | Sprint | What | Team | Duration |
|---------|--------|------|------|----------|
| **v9.0** | 19-20 | **Undo/redo + version history**: Command pattern, snapshots, activity feed | Platform | 2 weeks |
| **v9.1** | 19-20 | **Card mentions + block types**: @mentions, backlinks, rich block editor | Canvas | 2 weeks |
| **v10.0** | 21-23 | **Real-time collaboration**: WebSocket sync, CRDT, cursors, presence | Infra | 3 weeks |
| **v11.0** | 24-25 | **Multi-step AI Flows**: Flow builder, flow runner, flow templates | Workflow | 2 weeks |
| **v12.0** | 26-27 | **AI images + asset library**: Generation, asset browser, image cards | Media | 2 weeks |

### Phase 4: Scale

| Version | Sprint | What | Team | Duration |
|---------|--------|------|------|----------|
| **v13.0** | 28-30 | **Templates & marketplace**: 3 domains, template sharing, marketplace UI | All | 3 weeks |
| **v14.0** | 31-33 | **Export + integrations**: PDF/markdown/JSON export, webhooks, MCP | Platform | 3 weeks |
| **v15.0** | 34-36 | **Performance + scale**: Virtualization, code splitting, CDN, monitoring | Platform | 3 weeks |

**Total: ~36 sprints (72 weeks / ~18 months for full vision)**

**Immediate priority (v5.0-v5.4): 7 sprints (~14 weeks) to reach Heptabase feature parity + nested boards.**

---

## E. CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
triggers: push to main, PR to main

jobs:
  backend:
    - ruff check + format
    - mypy --strict
    - pytest --cov (unit + integration)
    - coverage >= 80% gate

  frontend:
    - eslint + prettier
    - vitest --coverage (unit)
    - npm run build (type check + bundle)
    - coverage >= 80% gate

  e2e:
    - Start backend + frontend
    - Playwright tests
    - Visual regression (Percy/Chromatic)

  deploy:
    - Backend → Railway (staging → production)
    - Frontend → Vercel (preview → production)
    - Database migrations → Supabase
```

---

## F. Design System

### F1. Design Tokens

```
Colors:
  --accent-primary: #6366f1 (indigo)
  --accent-secondary: #10b981 (emerald)
  --bg-primary, --bg-secondary, --bg-tertiary
  --text-primary, --text-secondary, --text-muted
  --border-primary, --border-secondary
  --card-colors: gray, red, orange, yellow, green, blue, purple, pink (8)

Spacing: 4px base (4, 8, 12, 16, 20, 24, 32, 40, 48, 64)
Radius: 4px (sm), 8px (md), 12px (lg), 9999px (full)
Shadows: sm, md, lg, xl (elevation system)
Typography: Inter (UI), JetBrains Mono (code), system stack fallback
```

### F2. Component Library (ui-kit)

Base components (built before features):
- Button (variants: primary, secondary, ghost, danger)
- Input, Textarea, Select, MultiSelect
- Modal, Dialog, Drawer, Popover
- Dropdown, ContextMenu
- Toast, Alert, Badge
- Tabs, Accordion, Toggle
- Avatar, AvatarGroup
- Spinner, Skeleton, Progress
- Table (sortable, filterable)
- Tree (directory sidebar)
- ColorPicker (8 colors)
- DatePicker, DateRangePicker
- CommandPalette
- SearchInput (with filters)
- Kbd (keyboard shortcut display)

---

## G. Database Schema (Complete)

### New Tables

```sql
-- v5.1: Sections
CREATE TABLE sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  title TEXT NOT NULL DEFAULT '',
  color TEXT NOT NULL DEFAULT 'gray',
  x FLOAT NOT NULL DEFAULT 0,
  y FLOAT NOT NULL DEFAULT 0,
  width FLOAT NOT NULL DEFAULT 400,
  height FLOAT NOT NULL DEFAULT 300,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- v5.2: Card Library (many-to-many)
CREATE TABLE board_card_placements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  x FLOAT NOT NULL DEFAULT 0,
  y FLOAT NOT NULL DEFAULT 0,
  UNIQUE(board_id, card_id)
);

-- v5.4: Journal
CREATE TABLE journal_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  date DATE NOT NULL,
  card_id UUID REFERENCES cards(id),  -- journal entry IS a card
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);

-- v6.0: Properties
CREATE TABLE property_definitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID REFERENCES boards(id) ON DELETE CASCADE,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('text','number','select','multi_select','date','checkbox','url','email','relation')),
  options JSONB DEFAULT '[]',  -- for select/multi_select: [{value, color}]
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE card_property_values (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  property_id UUID NOT NULL REFERENCES property_definitions(id) ON DELETE CASCADE,
  value JSONB NOT NULL,  -- type-dependent: string, number, [values], {date}, bool
  UNIQUE(card_id, property_id)
);

-- v6.2: Tags
CREATE TABLE tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  color TEXT DEFAULT 'gray',
  collection TEXT,  -- grouping
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE card_tags (
  card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  PRIMARY KEY(card_id, tag_id)
);

-- v7.0: RAG
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  layer_id UUID REFERENCES knowledge_layers(id),
  source_file TEXT,
  chunk_index INT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- v8.0: Knowledge Layers
CREATE TABLE knowledge_layers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  persona_prompt TEXT,  -- expert persona for council models
  methodology_prompt TEXT,
  color TEXT DEFAULT 'blue',
  icon TEXT DEFAULT 'book',
  sort_order INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- v9.0: History
CREATE TABLE board_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  name TEXT,  -- null = auto-snapshot, non-null = named
  snapshot JSONB NOT NULL,  -- full board state
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE card_mentions (
  source_card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  target_card_id UUID NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  PRIMARY KEY(source_card_id, target_card_id)
);

-- v12.0: Assets
CREATE TABLE generated_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  prompt TEXT NOT NULL,
  model TEXT NOT NULL,
  url TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE asset_library (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('image','document','video','audio')),
  url TEXT NOT NULL,
  tags TEXT[] DEFAULT '{}',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Modified Tables

```sql
-- boards: add nesting
ALTER TABLE boards ADD COLUMN parent_board_id UUID REFERENCES boards(id);
ALTER TABLE boards ADD COLUMN depth INT DEFAULT 0;
ALTER TABLE boards ADD COLUMN icon TEXT;

-- cards: add coloring, library support
ALTER TABLE cards ADD COLUMN color TEXT DEFAULT NULL;  -- 8-color override
ALTER TABLE cards ADD COLUMN is_global BOOLEAN DEFAULT false;  -- card library

-- edges: add styling
ALTER TABLE edges ADD COLUMN style JSONB DEFAULT '{}';  -- {arrow_type, color, label}
```

---

## H. Performance Plan

| Concern | Solution | When |
|---------|----------|------|
| Large boards (1000+ cards) | ReactFlow node virtualization (`nodeExtent`) | v5.0 |
| Bundle size | Code splitting per module (React.lazy) | v5.0 |
| API latency | Response caching (SWR/React Query stale-while-revalidate) | v5.0 |
| Image loading | Lazy load + thumbnail variants | v12.0 |
| Search speed | pgvector HNSW index + full-text GIN index | v7.0 |
| WebSocket scale | Redis pub/sub for multi-instance | v10.0 |
| Large RAG corpus | Streaming retrieval, pagination | v7.0 |

---

## I. Security Plan

| Area | Measure |
|------|---------|
| Auth | JWT + refresh tokens (existing), RBAC for teams |
| Data | RLS (Row Level Security) on all Supabase tables |
| API | Rate limiting per user (existing), input validation (Pydantic) |
| Files | Virus scan on upload, file type whitelist |
| WebSocket | Auth token validation on connection |
| Secrets | No secrets in code, env vars via Railway/Vercel |
| CORS | Whitelist production domains only |
| Dependencies | Dependabot, npm audit, pip audit |

---

## J. Testing Strategy

| Layer | Tool | Coverage | What |
|-------|------|----------|------|
| Unit (BE) | pytest | 80% | CRUD ops, business logic, utils |
| Unit (FE) | Vitest | 80% | Components, hooks, utils |
| Integration (BE) | pytest + httpx | Key flows | API endpoints, auth, council pipeline |
| E2E | Playwright | Critical paths | Board CRUD, card editing, council run, search |
| Visual | Percy/Chromatic | Key pages | Design system components, board view |
| Load | Locust | API endpoints | 100 concurrent users target |
| Security | OWASP ZAP | Monthly | Vulnerability scan |

---

## K. Key Technical Decisions

| Decision | Choice | Why | Alternatives Rejected |
|----------|--------|-----|----------------------|
| State management | Zustand | Lightweight, no boilerplate, good devtools | Redux (too heavy), Context (re-render issues) |
| Data fetching | TanStack Query (React Query) | Cache, stale-while-revalidate, optimistic updates | SWR (less features), manual fetch |
| Real-time | Yjs + WebSocket | CRDT = no conflicts, Yjs is battle-tested | Socket.io (overkill), OT (complex) |
| Rich editor | Tiptap (ProseMirror) | Already in use, extensible, collaborative-ready | Slate (less stable), Draft.js (deprecated) |
| Vector DB | pgvector on Supabase | Same infra, free, adequate scale | Pinecone (cost), Weaviate (separate infra) |
| Embedding | text-embedding-3-small (1536d) | Best price/quality ratio | ada-002 (legacy), Cohere (less ecosystem) |
| Nested boards | Navigation-based | ReactFlow can't embed ReactFlow instances | iframes (perf), SVG (no interaction) |
| Properties | Separate tables | Indexable, filterable, type-safe | JSON column (no indexing, no type safety) |
| Image gen | DALL-E 3 / Stability AI | OpenRouter already integrated | Midjourney (no API), Firefly (Adobe lock-in) |
| Monorepo | pnpm workspaces | Fast, disk-efficient, good for shared packages | Turborepo (adds complexity), Lerna (outdated) |
| Linting | Ruff (BE) + ESLint flat (FE) | Fast, comprehensive, modern | Black+flake8 (slower), Biome (less mature) |

---

## L. Verification Plan (Per Milestone)

**Every milestone must pass before merge:**

1. `ruff check && ruff format --check` (BE)
2. `mypy backend/` (BE types)
3. `pytest backend/tests/ --cov` (BE tests, 80%+)
4. `cd frontend && npm run lint` (FE lint)
5. `cd frontend && npm run build` (FE build, no errors)
6. `cd frontend && npx vitest run --coverage` (FE tests, 80%+)
7. `cd frontend && npx playwright test` (E2E, critical paths pass)
8. Manual smoke test in browser
9. No Sentry errors in staging for 24h

**Feature-specific verification:**
- **Sections**: Create, color, resize, drag with cards, persist on reload
- **Nested boards**: Create sub-board, navigate in/out, breadcrumb, sidebar tree
- **Properties**: Create all 9 types, set values, filter in table view, kanban columns
- **RAG**: Upload PDF, verify chunks + embeddings in DB, semantic search returns relevant results
- **Layers**: Create 2 layers, different docs, council with both active, verify layer context in prompts
- **Collaboration**: 2 browser tabs, same board, cursor sync, card move sync, no conflicts
- **Flows**: Create 3-step flow, run, verify sequential output, save as template


If you need specific details from before exiting plan mode (like exact code snippets, error messages, or content you generated), read the full transcript at: /Users/sezars/.claude/projects/-Users-sezars-llm-council/ed224d33-9331-436e-85a4-f90d9626edf0.jsonl