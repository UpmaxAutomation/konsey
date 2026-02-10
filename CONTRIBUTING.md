# Contributing to LLM Council

Thank you for your interest in contributing to LLM Council! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful and constructive. We're all here to build something cool.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 20+
- Docker (optional, for containerized development)
- uv (Python package manager)

### Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-council.git
cd llm-council

# Backend setup
uv sync --all-extras

# Frontend setup
cd frontend
npm install
cd ..

# Copy environment file
cp .env.example .env
# Edit .env with your API keys
```

### Running Locally

```bash
# Option 1: Use start script
./start.sh

# Option 2: Run manually
# Terminal 1 - Backend
uv run python -m backend.main

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## Development Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation
- `refactor/description` - Code refactoring

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new council preset for legal analysis
fix: resolve ranking parse failure with special characters
docs: update README with MCP server instructions
refactor: extract common API patterns to utilities
test: add coverage for voting system edge cases
```

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch from `master`
3. **Make** your changes with tests
4. **Run** the test suite: `uv run pytest`
5. **Run** linting: `uv run ruff check backend/`
6. **Push** to your fork
7. **Open** a Pull Request

### PR Checklist

- [ ] Tests pass locally
- [ ] Linting passes
- [ ] New features have tests
- [ ] Documentation updated if needed
- [ ] No secrets or API keys committed

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints
- Max line length: 100 characters
- Use `ruff` for formatting and linting

```python
# Good
async def query_model(
    model: str,
    messages: list[dict],
    timeout: int = 60
) -> dict[str, Any]:
    """Query a single model via OpenRouter."""
    ...

# Bad
async def query_model(model, messages, timeout=60):
    ...
```

### JavaScript (Frontend)

- Use ES6+ features
- Prefer functional components
- Use meaningful variable names

```jsx
// Good
const ModelSelector = ({ models, onSelect, selectedModel }) => {
  const handleSelect = (model) => {
    onSelect(model);
  };
  ...
};

// Bad
const MS = ({ m, os, sm }) => { ... };
```

## Testing

### Backend Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend --cov-report=html

# Run specific test file
uv run pytest tests/test_voting.py -v

# Run specific test
uv run pytest tests/test_voting.py::test_parse_vote -v
```

### Writing Tests

```python
# tests/test_example.py
import pytest
from backend.council import parse_ranking_from_text

def test_parse_ranking_basic():
    """Test basic ranking parsing."""
    text = "FINAL RANKING:\n1. Response A\n2. Response B"
    result = parse_ranking_from_text(text)
    assert result == ["Response A", "Response B"]

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await some_async_function()
    assert result is not None
```

## Architecture Overview

```
llm-council/
├── backend/           # FastAPI Python backend
│   ├── main.py        # FastAPI app entry point
│   ├── config.py      # Configuration and models
│   ├── council.py     # 3-stage deliberation logic
│   ├── voting.py      # Voting system
│   ├── openrouter.py  # API client
│   ├── storage.py     # JSON/DB storage
│   ├── auth/          # Authentication
│   └── database/      # SQLAlchemy models
│
├── frontend/          # React frontend
│   └── src/
│       ├── App.jsx    # Main app
│       ├── api.js     # API client
│       └── components/
│
├── mcp-server/        # MCP server for AI assistants
├── tests/             # Test suite
└── docs/              # Documentation
```

## Adding New Features

### Adding a New Council Preset

1. Edit `backend/config.py`:

```python
COUNCIL_PRESETS = {
    ...
    "your_preset": {
        "name": "Your Preset Name",
        "description": "What this preset is for",
        "models": ["model/a", "model/b", "model/c"],
        "chairman": "model/chairman"
    }
}
```

2. Add tests in `backend/test_presets.py`
3. Update documentation

### Adding a New API Endpoint

1. Add route in `backend/main.py` or create new router
2. Add tests
3. Update `frontend/src/api.js` if frontend needs it
4. Update MCP server if applicable

## Questions?

Open an issue or start a discussion. We're happy to help!

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
