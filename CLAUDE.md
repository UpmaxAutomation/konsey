# LLM Council - Development Guide

## Quick Start
```bash
# Backend (port 8001)
python -m backend.main
# Frontend (port 5173)
cd frontend && npm run dev
```

## Architecture
3-stage deliberation: Parallel queries → Anonymized peer review → Chairman synthesis

### Backend (`backend/`)
- `main.py` — FastAPI app, CORS for localhost:5173 + localhost:3000
- `config.py` — COUNCIL_MODELS, CHAIRMAN_MODEL, COUNCIL_PRESETS (5 presets)
- `council.py` — stage1/stage2/stage3 logic, ranking parser
- `voting.py` — Multi-choice voting (2-26 options, confidence scoring)
- `openrouter.py` — Async OpenRouter API client, reasoning model support
- `storage.py` — JSON conversation storage in data/conversations/

### Frontend (`frontend/src/`)
- `App.jsx` — Main orchestration, conversation + metadata state
- `components/ChatInterface.jsx` — Multiline input, Enter=send, Shift+Enter=newline
- `components/Stage1.jsx` — Model response tabs, reasoning toggle (brain emoji)
- `components/Stage2.jsx` — Anonymous evaluations with de-anonymized display
- `components/Stage3.jsx` — Chairman synthesis (green background #f0fff0)

## Key Rules
- **Always update ROADMAP.md** when completing features/milestones — roadmap must match reality
- Backend: relative imports (`from .config import ...`), run as `python -m backend.main`
- Frontend: wrap ReactMarkdown in `<div className="markdown-content">`
- Python: type hints, PEP 8, async/await, Pydantic models
- TypeScript: strict mode, no `any`, named exports, props interfaces
- Port 8001 for backend (not 8000), 5173 for frontend
- Models use OpenRouter API via OPENROUTER_API_KEY from .env

## API Endpoints
- `POST /api/conversations/{id}/message` — Council deliberation
- `POST /api/conversations/{id}/vote` — Multi-choice voting
- `GET /api/presets` — List council presets
- `POST /api/presets/{id}/apply` — Apply preset
- `GET/POST /api/config` — Get/update config
- `POST /api/config/reset` — Reset to defaults

## Presets
code_review, research, creative, reasoning, budget — each with tuned models + chairman

## Reasoning Models
Auto-detected (O1/O3/R1/QwQ), 120s timeout, thinking extraction, collapsible UI display

## Agent Teams — File Ownership
- **Frontend teammate:** `frontend/src/` — components, pages, hooks, styles
- **Backend teammate:** `backend/` — main.py, council.py, voting.py, openrouter.py, storage.py
- **QA teammate:** tests, build verification, lint
- **Shared (team lead only):** `backend/config.py`, `.env`, `package.json`
- After all tests pass: `python ~/.claude/scripts/notify-discord.py "LLM Council" "details" success`
