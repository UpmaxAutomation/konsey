# LLM Council

[![CI/CD](https://github.com/yourusername/llm-council/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/llm-council/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![LLM Council](header.jpg)

A multi-LLM deliberation system that combines the wisdom of multiple AI models to produce higher-quality, more reliable responses. Instead of asking one AI, assemble a **council** of the best LLMs to collaborate on your questions.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Council Deliberation                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📝 Your Question                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Stage 1: COLLECT - Each model answers independently     │    │
│  │  [GPT-4o] [Claude Sonnet] [Gemini] [Grok] [DeepSeek]   │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Stage 2: REVIEW - Models rank each other (anonymized)   │    │
│  │  Responses → "Response A, B, C..." → Fair evaluation    │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Stage 3: SYNTHESIZE - Chairman creates final answer     │    │
│  │  Best insights from all models combined                 │    │
│  └─────────────────────────────────────────────────────────┘    │
│       │                                                          │
│       ▼                                                          │
│  ✅ Final Answer (better than any single model)                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-LLM Deliberation**: Query 3-10+ models simultaneously
- **Anonymized Peer Review**: Models can't play favorites - responses are labeled A, B, C...
- **Aggregate Rankings**: See which models perform best across evaluations
- **70+ Models Available**: Access OpenAI, Anthropic, Google, xAI, DeepSeek, Mistral, Qwen, and more
- **Council Presets**: One-click specialized councils (Code Review, Research, Creative, Reasoning, Budget)
- **Reasoning Model Support**: Special handling for O1, O3, R1, QwQ with thinking process display
- **Voting System**: Multi-choice voting with confidence scores
- **Model Personas**: Assign roles like "Security Expert" or "Devil's Advocate"
- **Web Search & Code Execution**: Enhanced capabilities for complex queries
- **MCP Server**: Integrate with Claude Code, Cursor, and other AI assistants
- **Docker Ready**: Full containerized deployment with PostgreSQL

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 20+
- [OpenRouter API key](https://openrouter.ai/)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-council.git
cd llm-council

# Install backend dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY
```

### Running

**Option 1: Start script**
```bash
./start.sh
```

**Option 2: Manual**
```bash
# Terminal 1 - Backend (port 8001)
uv run python -m backend.main

# Terminal 2 - Frontend (port 5173)
cd frontend && npm run dev
```

Open http://localhost:5173 in your browser.

### Using PostgreSQL (recommended for developers)

Set in `.env`:

```bash
USE_DATABASE=true
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database_name
```

Tables are created on first backend start. See **[DATABASE_SETUP.md](DATABASE_SETUP.md)** for local and hosted Postgres (Supabase, Railway, Render). For full onboarding (design, stack, daily workflow), see **[docs/DEVELOPER_MANUAL.md](docs/DEVELOPER_MANUAL.md)**.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Yes | - | Your OpenRouter API key |
| `SECRET_KEY` | Prod only | - | JWT secret (required in production) |
| `ENVIRONMENT` | No | development | Set to `production` for prod mode |
| `USE_DATABASE` | No | false | Use PostgreSQL instead of JSON files |
| `DATABASE_URL` | If DB | - | PostgreSQL connection string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 30 | JWT access token expiry |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | 30 | JWT refresh token expiry |

### Council Presets

| Preset | Models | Use Case |
|--------|--------|----------|
| **Code Review** | Claude Sonnet 4, GPT-5.1 Codex, DeepSeek V3, Qwen Coder | Code analysis, bugs, best practices |
| **Research** | Gemini 2.5 Pro, Claude Opus 4.5, GPT-5, Grok 3 | Deep research, analysis |
| **Creative** | Claude Sonnet 4, GPT-5, Gemini Flash | Writing, brainstorming |
| **Reasoning** | O3, DeepSeek R1, QwQ 32B, O4 Mini | Math, logic, complex problems |
| **Budget** | DeepSeek R1, Qwen Coder, Gemma 2 (Free) | Cost-effective quality |

### Custom Council

Configure via Settings UI or edit `backend/config.py`:

```python
DEFAULT_COUNCIL_MODELS = [
    "openai/gpt-4o",
    "google/gemini-2.5-flash",
    "anthropic/claude-sonnet-4",
    "x-ai/grok-3",
]

DEFAULT_CHAIRMAN_MODEL = "google/gemini-2.5-flash"
```

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose up -d

# View logs
docker compose logs -f
```

Services:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **PostgreSQL**: localhost:5432

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive production deployment guide including:
- Vercel + Railway (recommended for quickest setup)
- Proxmox LXC setup
- SSL/TLS configuration
- Cloudflare tunnel integration
- Environment hardening

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/conversations` | List all conversations |
| `POST` | `/api/conversations` | Create new conversation |
| `POST` | `/api/conversations/{id}/message` | Send message (triggers 3-stage deliberation) |
| `POST` | `/api/conversations/{id}/vote` | Run voting on multiple-choice question |
| `GET` | `/api/presets` | List council presets |
| `POST` | `/api/presets/{id}/apply` | Apply a preset |
| `GET` | `/api/config` | Get current configuration |
| `POST` | `/api/config` | Update configuration |

### Example: Send a Query

```bash
curl -X POST http://localhost:8001/api/conversations/new/message \
  -H "Content-Type: application/json" \
  -d '{"content": "What is the best programming language for beginners?"}'
```

### Response Structure

```json
{
  "stage1": [
    {"model": "openai/gpt-4o", "content": "...", "thinking": null},
    {"model": "google/gemini-2.5-flash", "content": "...", "thinking": null}
  ],
  "stage2": [
    {"model": "openai/gpt-4o", "ranking": "...", "parsed_ranking": ["Response B", "Response A"]},
    {"model": "google/gemini-2.5-flash", "ranking": "...", "parsed_ranking": ["Response A", "Response B"]}
  ],
  "stage3": "Final synthesized answer...",
  "metadata": {
    "label_to_model": {"Response A": "openai/gpt-4o", "Response B": "google/gemini-2.5-flash"},
    "aggregate_rankings": [
      {"model": "openai/gpt-4o", "avg_position": 1.5, "votes": 2}
    ]
  }
}
```

## MCP Server Integration

The LLM Council includes an MCP (Model Context Protocol) server for integration with AI assistants like Claude Code.

### Setup

```bash
cd mcp-server
npm install
```

Add to your Claude Desktop config:
```json
{
  "mcpServers": {
    "llm-council": {
      "command": "node",
      "args": ["/path/to/llm-council/mcp-server/index.js"],
      "env": {
        "LLM_COUNCIL_API": "http://localhost:8001"
      }
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `council_query` | Full 3-stage deliberation |
| `council_quick` | Quick answer (synthesis only) |
| `council_search` | Web search with council |
| `council_execute` | Execute Python/JS code |
| `council_vote` | Multi-choice voting |
| `council_models` | List available models |

See [mcp-server/README.md](mcp-server/README.md) for complete documentation.

## Architecture

```
llm-council/
├── backend/                 # FastAPI Python backend
│   ├── main.py              # API endpoints
│   ├── config.py            # Models, presets, settings
│   ├── council.py           # 3-stage deliberation logic
│   ├── voting.py            # Voting system
│   ├── openrouter.py        # OpenRouter API client
│   ├── storage.py           # JSON file storage
│   ├── auth/                # JWT authentication
│   └── database/            # SQLAlchemy models (optional)
│
├── frontend/                # React + Vite frontend
│   └── src/
│       ├── App.jsx          # Main app
│       ├── api.js           # API client
│       └── components/      # Stage1, Stage2, Stage3, Settings
│
├── mcp-server/              # MCP server for AI assistants
├── directives/              # SOP documentation
├── execution/               # CLI scripts
├── tests/                   # Pytest test suite
└── docker-compose.yml       # Container orchestration
```

## Tech Stack

- **Backend**: FastAPI, Python 3.10+, async httpx, SQLAlchemy (optional)
- **Frontend**: React 19, Vite 7, react-markdown, Tailwind CSS
- **Database**: JSON files (default) or PostgreSQL
- **Auth**: JWT with refresh tokens, Google OAuth (optional)
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## Development

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=backend --cov-report=html

# Specific test file
uv run pytest tests/test_voting.py -v
```

### Linting

```bash
# Check
uv run ruff check backend/

# Fix
uv run ruff check backend/ --fix
```

### Type Checking

```bash
uv run mypy backend/
```

## Documentation

| Document | Description |
|----------|-------------|
| [**docs/DEVELOPER_MANUAL.md**](docs/DEVELOPER_MANUAL.md) | **For new developers:** what we designed, full tech stack, PostgreSQL setup, daily workflow |
| [DATABASE_SETUP.md](DATABASE_SETUP.md) | PostgreSQL connection (local, Supabase, Railway, Render) |
| [docs/ONBOARDING.md](docs/ONBOARDING.md) | What’s in the repo, getting DB backup/restore |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Module structure, data flow, patterns |
| [QUICK_START.md](QUICK_START.md) | Backend/frontend start options |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Development setup
- Code style
- Pull request process
- Testing requirements

## Vibe Code Notice

This project started as a fun weekend hack to explore multiple LLMs side-by-side while [reading books with LLMs](https://x.com/karpathy/status/1990577951671509438). It has since grown into a full-featured deliberation system, but the spirit of exploration remains. Feel free to fork, modify, and make it your own!

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [OpenRouter](https://openrouter.ai/) for unified LLM API access
- Inspired by the idea of "wisdom of crowds" applied to AI
- All the amazing LLM providers: OpenAI, Anthropic, Google, xAI, DeepSeek, Mistral, and more
