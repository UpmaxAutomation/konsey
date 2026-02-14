# LLM Council – Developer Manual

This manual is for developers joining the project. It describes **what we designed**, **what we use** (tech stack), and how to run and work on the app **with PostgreSQL**.

---

## 1. What we designed

### Product

**LLM Council** is a multi-LLM deliberation system:

- Users ask a question; multiple AI models answer in parallel (Stage 1).
- Models then rank each other’s answers anonymously (Stage 2).
- A “chairman” model synthesizes a final answer (Stage 3).

The app also provides:

- **Canvas/boards**: Cards (notes, queries, council results) on a ReactFlow canvas, with edges, AI actions, and board-level council runs.
- **Chat**: Council conversations, voting, presets, and “add to board” to push results onto a board.
- **Projects, tags, workflows, RAG**: Project context, knowledge layers, document chunks, and workflow runs, all persisted when using the database.

### Design choices

| Area | Decision | Reason |
|------|----------|--------|
| Storage | PostgreSQL when enabled; otherwise JSON files under `data/` | One codebase for dev (no DB) and production (PostgreSQL). |
| API | FastAPI, async | Async I/O for LLM and DB; OpenAPI docs out of the box. |
| Frontend | React 19, Vite, React Router | Fast dev experience; modules (canvas, chat) stay decoupled. |
| Canvas | ReactFlow (@xyflow/react) | Nodes/edges, drag-and-drop, layout; fits card/board model. |
| LLM access | OpenRouter first, optional direct keys | Single integration for many models; fallback to provider keys. |
| Auth | JWT + optional Google OAuth | Stateless API; optional social login. |
| DB access | SQLAlchemy 2 (async) + asyncpg | Async all the way; Alembic for migrations. |

---

## 2. What we use (tech stack)

### Backend

| Category | Technology | Version / notes |
|----------|------------|------------------|
| Runtime | Python | 3.10+ |
| Package manager | uv | See `pyproject.toml` |
| Framework | FastAPI | 0.115+ |
| Server | Uvicorn | 0.32+ |
| ORM / DB | SQLAlchemy (async) | 2.0+ |
| PostgreSQL driver | asyncpg | 0.29+ |
| Migrations | Alembic | 1.13+ |
| Auth | python-jose, passlib (argon2), authlib | JWT + OAuth |
| HTTP client | httpx | For OpenRouter and external APIs |
| Config | pydantic-settings, python-dotenv | .env + typed settings |
| Logging | structlog | Structured JSON logs |
| Rate limiting | slowapi | Per-route limits |

### Frontend

| Category | Technology | Version / notes |
|----------|------------|------------------|
| Runtime | Node.js | 20+ (22.x in package.json) |
| Package manager | npm | See `frontend/package.json` |
| Framework | React | 19.x |
| Build | Vite | 7.x |
| Routing | React Router | 7.x |
| Canvas | @xyflow/react | 12.x |
| Rich text | Tiptap | 3.19.x |
| Data fetching | TanStack Query | 5.x |
| Auth (Google) | @react-oauth/google | 0.12.x |

### Database (PostgreSQL)

- **Database**: PostgreSQL (local, Supabase, Railway, Render, or any Postgres host).
- **Driver**: `asyncpg` (async-only).
- **Connection string format**: `postgresql+asyncpg://user:password@host:port/database_name`
- **Schema**: Managed by SQLAlchemy models in `backend/database/models.py` and Alembic migrations in `backend/database/migrations/`.

### External services (optional)

- **OpenRouter**: Primary LLM API (required for council features).
- **Google OAuth**: Optional login.
- **Supabase**: Optional; used only as PostgreSQL host (no Supabase SDK/RLS).

---

## 3. PostgreSQL setup (for new developers)

We assume **PostgreSQL** for persistent storage. Follow these steps.

### 3.1 Install PostgreSQL

- **macOS**: `brew install postgresql@16` (or latest), start with `brew services start postgresql@16`.
- **Linux**: Use your distro package (e.g. `postgresql-16`).
- **Windows**: Install from [postgresql.org](https://www.postgresql.org/download/windows/).

Alternatively use a hosted Postgres (Supabase, Railway, Render) and skip local install.

### 3.2 Create database and user (local example)

```bash
# Connect as superuser
psql -U postgres

# In psql:
CREATE USER council WITH PASSWORD 'your_secure_password';
CREATE DATABASE llm_council OWNER council;
\q
```

### 3.3 Clone and install

```bash
git clone https://github.com/UpmaxAutomation/konsey.git
cd konsey
uv sync
cd frontend && npm install && cd ..
```

### 3.4 Environment

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```bash
# Required for council/LLM
OPENROUTER_API_KEY=sk-or-v1-...

# Use PostgreSQL
USE_DATABASE=true

# Local PostgreSQL (match your user/password/db)
DATABASE_URL=postgresql+asyncpg://council:your_secure_password@localhost:5432/llm_council
```

For **Supabase** (as Postgres only):

- Dashboard → Project Settings → Database → Connection string (URI).
- Use “Transaction” pooler (port 6543) for serverless, or direct (port 5432).
- Format: `postgresql+asyncpg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres`

### 3.5 Initialize schema

Tables are created automatically on first backend startup when `USE_DATABASE=true`. To run migrations explicitly (e.g. after pull):

```bash
# From project root
uv run alembic upgrade head
```

### 3.6 Run the app

```bash
# Terminal 1 – backend (port 8001)
uv run uvicorn backend.main:app --reload --port 8001 --host 127.0.0.1

# Terminal 2 – frontend (port 5173)
cd frontend && npm run dev
```

Open **http://localhost:5173**. API docs: **http://127.0.0.1:8001/docs**.

### 3.7 Verify database

- Backend logs should show “Database tables initialized” or similar on startup.
- In psql: `\dt` in `llm_council` should list tables (boards, cards, edges, users, etc.).

More detail: **DATABASE_SETUP.md** (project root).

---

## 4. Architecture (summary)

- **Frontend**: Feature modules (`canvas`, `chat`, etc.) that do not import from each other; cross-module events via `CustomEvent`. API calls go through `api/` (e.g. `api/boards.js`).
- **Backend**: FastAPI routers in `backend/routes/`; business logic in `backend/council/`, `backend/llm/`; data access in `backend/database/crud/`; models in `backend/database/models.py`.
- **Database**: One PostgreSQL database; all tables created/migrated via Alembic. No Supabase RLS; app uses JWT and optional Google OAuth for auth.

Full detail: **docs/ARCHITECTURE.md**.

---

## 5. Key design decisions (reference)

- **Why OpenRouter**: Single API for many models (OpenAI, Anthropic, Google, etc.); easier key and model management.
- **Why ReactFlow**: Canvas with nodes/edges, built-in pan/zoom and layout; fits boards and card relationships.
- **Why asyncpg**: Async-only stack; no blocking DB calls in FastAPI.
- **Why `USE_DATABASE` flag**: Enables running without PostgreSQL (e.g. quick local try with JSON under `data/`) and switching to Postgres for production or team use.
- **Why no Supabase SDK**: We use Postgres only; auth and API are our own (JWT/OAuth + FastAPI).

---

## 6. Daily workflow

| Task | Command |
|------|--------|
| Start backend | `uv run uvicorn backend.main:app --reload --port 8001 --host 127.0.0.1` or `./start-backend.sh` |
| Start frontend | `cd frontend && npm run dev` |
| Run tests (backend) | `uv run pytest` |
| Run tests (frontend) | `cd frontend && npm run test` |
| Lint (backend) | `uv run ruff check backend/` |
| Lint (frontend) | `cd frontend && npm run lint` |
| New migration | `uv run alembic revision -m "description"` then edit the new file in `backend/database/migrations/versions/` |
| Apply migrations | `uv run alembic upgrade head` |

---

## 7. Environment and config reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes (for council) | OpenRouter API key. |
| `USE_DATABASE` | No (default: false) | Set to `true` to use PostgreSQL. |
| `DATABASE_URL` | If `USE_DATABASE=true` | `postgresql+asyncpg://user:pass@host:port/dbname`. |
| `SECRET_KEY` | Yes in production | JWT signing; min 32 chars. |
| `ENVIRONMENT` | No | `development` \| `production`. |
| `FRONTEND_URL` / `CORS_ORIGINS` | Production | Allowed origins for CORS. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth. |

Full list and examples: **.env.example** in the project root.

---

## 8. Where to find more

| Topic | Location |
|-------|----------|
| Quick run (no DB) | **README.md** – Quick Start |
| PostgreSQL setup | **DATABASE_SETUP.md** |
| Onboarding (what’s in repo, DB backup/restore) | **docs/ONBOARDING.md** |
| Architecture, data flow, patterns | **docs/ARCHITECTURE.md** |
| Backend start options | **QUICK_START.md** |
| API reference | http://127.0.0.1:8001/docs when backend is running |
| Backup / restore DB | **backup_full.sh**, **restore_backup.sh** (project root) |

---

## 9. Checklist for a new developer (PostgreSQL)

- [ ] Clone repo, run `uv sync`, `cd frontend && npm install`
- [ ] Install and start PostgreSQL (or create a hosted DB)
- [ ] `cp .env.example .env`; set `OPENROUTER_API_KEY`, `USE_DATABASE=true`, `DATABASE_URL`
- [ ] Start backend; confirm “Database tables initialized” (or run `uv run alembic upgrade head`)
- [ ] Start frontend; open http://localhost:5173
- [ ] Read **docs/ARCHITECTURE.md** for data flow and module layout
- [ ] (Optional) Get a DB backup from the team and run **restore_backup.sh** to get production-like data
