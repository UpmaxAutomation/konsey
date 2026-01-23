# LLM Council - Project Context

## Overview
LLM Council is a collaborative multi-model deliberation system that leverages multiple LLMs to provide higher-quality answers through structured peer review and synthesis.

## Core Concept: 3-Stage Deliberation

### Stage 1: Parallel Collection
- Query sent to multiple LLMs simultaneously
- Each model provides independent response
- No cross-contamination between models

### Stage 2: Anonymized Peer Review
- Each LLM receives ALL responses (anonymized)
- Models rank responses 1-N (best to worst)
- Prevents bias from knowing which model produced which response

### Stage 3: Chairman Synthesis
- Chairman LLM receives:
  - Original query
  - All responses with rankings
  - Peer review comments
- Synthesizes final authoritative answer

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL via SQLAlchemy + asyncpg
- **Migrations**: Alembic
- **API Client**: OpenRouter (unified LLM access)
- **Auth**: JWT + Google OAuth

### Frontend
- **Framework**: React 19 + Vite
- **Router**: React Router DOM 7
- **Styling**: CSS (consider Tailwind)
- **Markdown**: react-markdown + syntax highlighting

### Infrastructure
- **Container**: Docker + docker-compose
- **Proxy**: nginx
- **Database**: PostgreSQL (Supabase compatible)

## Key Directories
```
llm-council/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API routes
│   │   ├── core/            # Config, security, deps
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # DB migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Route pages
│   │   ├── hooks/           # Custom hooks
│   │   └── api/             # API client
│   └── public/
├── nginx/                   # Reverse proxy config
└── docker-compose.yml
```

## Council Presets

| Preset | Models | Use Case |
|--------|--------|----------|
| code_review | Claude, GPT-4, Gemini | Code analysis, debugging |
| research | Claude, GPT-4, Perplexity | Factual research |
| creative | Claude, GPT-4, Gemini | Creative writing |
| reasoning | O1, Claude, Gemini | Logic, math, puzzles |
| budget | Haiku, GPT-3.5, Gemini Flash | Quick, cheap queries |

## Environment Variables
```bash
OPENROUTER_API_KEY=        # Required: OpenRouter access
DATABASE_URL=              # PostgreSQL connection
JWT_SECRET=                # Auth token signing
GOOGLE_CLIENT_ID=          # OAuth (optional)
```

## API Base URL
- Development: `http://localhost:8000/api/v1`
- Frontend: `http://localhost:5173`
