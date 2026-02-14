# Developer onboarding – what you get from this repo

**For a full manual (what we designed, tech stack, PostgreSQL setup, daily workflow), see [DEVELOPER_MANUAL.md](DEVELOPER_MANUAL.md).**

## What’s in the repo (another dev gets this)

| Item | In repo? | Notes |
|------|----------|--------|
| **Source code** | ✅ Yes | Backend (Python/FastAPI), frontend (React/Vite), migrations, scripts |
| **Schema & migrations** | ✅ Yes | `backend/database/models.py`, `backend/database/migrations/`, Alembic |
| **Config template** | ✅ Yes | `.env.example` – copy to `.env` and fill in |
| **Docs** | ✅ Yes | README, QUICK_START, DATABASE_SETUP, this file |
| **Actual database contents** | ❌ No | Not in git (see below) |
| **Secrets / .env** | ❌ No | `.env` is gitignored; use `.env.example` as template |
| **Local data/ folder** | ❌ No | `data/` is gitignored (JSON storage when DB is off) |

So: another developer gets the **full build** (code + schema + config shape), but **not** the live data or secrets.

---

## Getting “everything” including a database

### Option A: Empty database (recommended for new devs)

1. **Clone and install**
   ```bash
   git clone https://github.com/UpmaxAutomation/konsey.git
   cd konsey
   uv sync
   cd frontend && npm install && cd ..
   ```

2. **Environment**
   ```bash
   cp .env.example .env
   # Edit .env: OPENROUTER_API_KEY (required), optionally USE_DATABASE and DATABASE_URL
   ```

3. **Run without PostgreSQL (simplest)**
   - In `.env`: `USE_DATABASE=false` (or leave unset).
   - No DB setup; app uses JSON files under `data/` (created at runtime).
   - Start: `./start-backend.sh` and `cd frontend && npm run dev`.

4. **Run with PostgreSQL (full app behavior)**
   - In `.env`: `USE_DATABASE=true` and set `DATABASE_URL` (e.g. local Postgres or Supabase).
   - On first start the app creates tables (or run `alembic upgrade head` from project root).
   - See **DATABASE_SETUP.md** for URLs and options.

So: another dev can get **everything needed to run the build**, including an **empty DB** (schema only), by following the repo and `.env.example`.

---

## Getting the same data as production / you (DB contents)

The **database contents** (boards, cards, users, etc.) are **not** in the repo. To give another dev a copy of the data:

1. **Export a backup** (on the machine that has the DB):
   ```bash
   ./backup_full.sh
   # Or manually: pg_dump "$DATABASE_URL" -F c -f backup.dump
   ```

2. **Share the backup**  
   Send the backup file (or `backups/YYYYMMDD_HHMMSS/` folder) by secure channel (e.g. shared drive, not in public git).

3. **Restore on the other dev’s machine**
   - They create a PostgreSQL database and set `DATABASE_URL` in `.env` with `USE_DATABASE=true`.
   - Restore:
     ```bash
     ./restore_backup.sh backups/YYYYMMDD_HHMMSS "postgresql+asyncpg://user:pass@host:port/dbname"
     ```
   - Or restore manually with `pg_restore` / `psql` and the dump file.

So: **yes, another developer can get everything from this build including the DB**, but the **DB contents** must be shared separately (backup/restore), not via GitHub.

---

## Quick checklist for a new developer

- [ ] Clone repo, `uv sync`, `cd frontend && npm install`
- [ ] `cp .env.example .env` and set at least `OPENROUTER_API_KEY`
- [ ] Choose: `USE_DATABASE=false` (no DB) or `USE_DATABASE=true` + `DATABASE_URL`
- [ ] If using DB: create Postgres (local or Supabase), then start app (tables created on first run or run `alembic upgrade head`)
- [ ] Start backend: `uv run uvicorn backend.main:app --reload --port 8001 --host 127.0.0.1`
- [ ] Start frontend: `cd frontend && npm run dev` → http://localhost:5173
- [ ] (Optional) If you need production-like data: get a backup from the team and run `restore_backup.sh` (or equivalent) into your `DATABASE_URL`
