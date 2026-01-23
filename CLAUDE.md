# LLM Council - Multi-LLM Deliberation System

> **Cross-Reference**: This file is mirrored across `CLAUDE.md`, `AGENTS.md`, and `GEMINI.md` so the same instructions load in any AI environment.

---

## 3-Layer Agent Architecture (DOE Framework)

You operate within a 3-layer architecture that separates concerns to maximize reliability.

### Layer 1: Directive (What to do)
- SOPs written in Markdown, live in `directives/`
- Define goals, inputs, outputs, and edge cases
- **Each directive has YAML front matter** with `name`, `description`, and `scripts` fields

### Layer 2: Orchestration (Decision making)
- This is you. Your job: intelligent routing.
- Read directives, call execution tools in the right order, handle errors, ask for clarification
- You're the glue between intent and execution

### Layer 3: Execution (Doing the work)
- Deterministic Python scripts in `execution/`
- Handle API calls, data processing, CLI operations
- Reliable, testable, fast. Use scripts instead of manual work.

---

## Quick Start

```bash
# Backend (port 8001)
python -m backend.main

# Frontend
cd frontend && npm run dev
```

---

## Directory Structure

```
llm-council/
├── .planning/           # Project planning (GSD)
├── directives/          # SOP markdown files
│   ├── _template.md     # Template for new directives
│   ├── council_query.md # 3-stage deliberation queries
│   ├── council_vote.md  # Multi-choice voting system
│   └── preset_management.md # Council preset management
│
├── execution/           # Execution scripts
│   ├── run_council_query.py   # CLI for council queries
│   ├── run_council_vote.py    # CLI for voting
│   └── manage_presets.py      # Preset management CLI
│
├── backend/             # FastAPI application
│   ├── main.py          # FastAPI app
│   ├── config.py        # Models and presets
│   ├── council.py       # 3-stage logic
│   ├── voting.py        # Voting system
│   └── openrouter.py    # OpenRouter API client
│
├── frontend/            # React application
├── .tmp/                # Ephemeral intermediate files
└── config/              # Credentials (git-ignored)
```

---

## Available Directives

| Directive | Purpose | Scripts |
|-----------|---------|---------|
| `council_query.md` | 3-stage LLM deliberation | `run_council_query.py` |
| `council_vote.md` | Multi-choice voting | `run_council_vote.py` |
| `preset_management.md` | Manage council presets | `manage_presets.py` |

---

## Self-Annealing Error Loop

```
Error Occurs → Pattern Match → Auto-Fix → Learn → Update Directive
```

When something breaks:
1. Fix it
2. Update the execution script
3. Test the script
4. Update directive with new flow
5. System is now stronger

---

## Project Overview (Technical Details)

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Core Functionality

LLM Council is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Contains `COUNCIL_PRESETS` (5 specialized preset configurations)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**Council Presets** (NEW - 2025-12-25)
Five specialized preset configurations available:
1. **code_review**: Expert code reviewers (Claude Sonnet 4, GPT-5.1 Codex, DeepSeek V3, Qwen Coder)
2. **research**: Deep research and analysis (Gemini 2.5 Pro, Claude Opus 4.5, GPT-5, Grok 3)
3. **creative**: Creative writing and brainstorming (Claude Sonnet 4, GPT-5, Gemini 2.5 Flash)
4. **reasoning**: Complex logic and mathematics (O3, DeepSeek R1, QwQ 32B, O4 Mini)
5. **budget**: Cost-effective models (DeepSeek R1 0528, Qwen Coder, Gemma 2 9B free)

Each preset includes both council member models and a chairman model optimized for that use case.

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic
- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_collect_rankings()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization
  - Prompts models to evaluate and rank (with strict format requirements)
  - Returns tuple: (rankings_list, label_to_model_dict)
  - Each ranking includes both raw text and `parsed_ranking` list
- `stage3_synthesize_final()`: Chairman synthesizes from all responses + rankings
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section, handles both numbered lists and plain format
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations

**`voting.py`** - Voting System (NEW - 2025-12-25)
- `run_vote()`: Main entry point for running votes on multiple-choice questions
- `_parse_vote()`: Parses model responses (VOTE/CONFIDENCE/REASON format)
- `_calculate_results()`: Aggregates votes by option with confidence scores
- `_determine_winner()`: Calculates winner based on total score (votes × avg confidence)
- Each model votes for ONE option with 0-100% confidence and reasoning
- Supports 2-26 options (alphabetic labeling limit)
- Intelligent option matching: exact, numeric, or partial match

**`storage.py`**
- JSON-based conversation storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, stage2, stage3}`
- Note: metadata (label_to_model, aggregate_rankings) is NOT persisted to storage, only returned via API

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns metadata in addition to stages
- GET `/api/presets` lists all available council presets (NEW)
- POST `/api/presets/{preset_id}/apply` applies a preset configuration (NEW)
- Metadata includes: label_to_model mapping and aggregate_rankings

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper

**`components/Stage2.jsx`**
- **Critical Feature**: Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display (models receive anonymous labels)
- Shows "Extracted Ranking" below each evaluation so users can validate parsing
- Aggregate rankings shown with average position and vote count
- Explanatory text clarifies that boldface model names are for readability only

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Prompt Format
The Stage 2 prompt is very specific to ensure parseable output:
```
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
4. No additional text after ranking section
```

This strict format allows reliable parsing while still getting thoughtful evaluations.

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models can be configured three ways:
1. **Manual configuration** via Settings UI (select individual models)
2. **Presets** via dropdown (one-click specialized councils)
3. **Direct config file editing** in `backend/config.py`

The current default is Gemini as chairman per user preference.

### Preset System (NEW)
Presets allow one-click council configuration for specific use cases:
- Each preset defines council members + chairman
- Presets are immutable (defined in code, not user-editable)
- Applying a preset updates the runtime config and persists to `data/settings.json`
- Frontend will display preset dropdown in Settings (to be implemented separately)

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses
5. **Preset Validation**: Frontend should validate that preset models exist in available_models before displaying

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file (DONE via presets)
- Streaming responses instead of batch loading
- Export conversations to markdown/PDF
- Model performance analytics over time
- Custom ranking criteria (not just accuracy/insight)
- Support for reasoning models (o1, etc.) with special handling (DONE - see Reasoning Models section)
- User-defined custom presets (save current config as preset)
- Preset recommendations based on query content
- Add reasoning token count display in UI
- Export thinking process to markdown
- Highlight key reasoning steps in thinking blocks

## Testing Notes

Use `test_openrouter.py` to verify API connectivity and test different model identifiers before adding to council. The script tests both streaming and non-streaming modes.

## API Endpoints Reference

### Preset Endpoints (NEW)
- `GET /api/presets` - List all available presets
  - Returns: `{"presets": [{"id": "code_review", "name": "...", "description": "...", "models": [...], "chairman": "..."}]}`
- `POST /api/presets/{preset_id}/apply` - Apply a preset
  - Returns: `{"status": "success", "message": "Applied preset: ...", "council_models": [...], "chairman_model": "...", "preset_name": "...", "preset_description": "..."}`
  - Errors: 404 if preset_id not found

### Voting Endpoint (NEW - 2025-12-25)
- `POST /api/conversations/{conversation_id}/vote` - Run a vote on multiple-choice question
  - Request: `{"question": "...", "options": ["Option 1", "Option 2", ...]}`
  - Returns: `{"votes": [...], "results": {...}, "winner": {...}}`
  - Each model votes for ONE option with confidence (0-100%) and reasoning
  - Winner determined by total score (votes × avg confidence)
  - Validates 2-26 options, requires valid conversation ID

### Config Endpoints
- `GET /api/config` - Get current configuration
- `POST /api/config` - Update configuration manually
- `POST /api/config/reset` - Reset to defaults

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking queries → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 3: Chairman synthesis with full context
    ↓
Return: {stage1, stage2, stage3, metadata}
    ↓
Frontend: Display with tabs + validation UI
```

The entire flow is async/parallel where possible to minimize latency.

## Reasoning Models Support (NEW - 2025-12-25)

### Overview
Special support for reasoning models that expose their internal thinking process (O1, O3, R1, QwQ, etc.).

### Supported Models
- OpenAI: o1, o1-mini, o1-pro, o3, o3-mini, o3-pro, o3-deep-research, o4-mini, o4-mini-deep-research
- DeepSeek: deepseek-r1, deepseek-r1-0528
- Qwen: qwq-32b
- Anthropic: claude-3.7-sonnet:thinking

### Key Features
1. **Auto-Detection**: System automatically detects reasoning models via `is_reasoning_model()`
2. **Extended Timeout**: 120 seconds (vs default) to allow for reasoning computation
3. **Thinking Extraction**: Captures internal reasoning from multiple API response formats
4. **UI Display**: Brain emoji indicator, collapsible thinking blocks, monospace formatting
5. **Graceful Degradation**: Standard models continue to work normally

### Implementation Details
- `backend/config.py`: `REASONING_MODELS` list and `REASONING_MODEL_CONFIG` dict
- `backend/openrouter.py`: Auto-timeout extension and thinking field extraction
- `backend/council.py`: Pass-through of `thinking` field in Stage 1 results
- `frontend/Stage1.jsx`: Toggle button and collapsible thinking display
- `frontend/Stage1.css`: Gray background, monospace font, max-height scroll

### User Experience
1. Select reasoning model in council (e.g., use "Reasoning Council" preset)
2. Ask complex question requiring multi-step reasoning
3. Look for brain emoji (🧠) on response tabs
4. Click "Show Reasoning" to view internal thought process
5. Compare thinking approaches across different reasoning models

See `REASONING_MODELS_IMPLEMENTATION.md` for complete technical documentation.

## Recent Changes

### 2025-12-25: Reasoning Models Support
- Added detection and handling for reasoning models (O1, O3, R1, QwQ)
- Implemented extended timeout (120s) for reasoning computation
- Added thinking token extraction from API responses (multiple formats)
- Created collapsible UI for displaying reasoning process
- Added brain emoji indicator on tabs with thinking available
- Supports DeepSeek R1, OpenAI O-series, QwQ, and Claude thinking formats
- See `REASONING_MODELS_IMPLEMENTATION.md` for full documentation

### 2025-12-25: Voting System Implementation
- Added `backend/voting.py` with complete voting system
- Added `POST /api/conversations/{conversation_id}/vote` endpoint
- Each model votes for ONE option with confidence (0-100%) and reasoning
- Intelligent option matching (exact, numeric, partial)
- Winner calculation based on total score (votes × avg confidence)
- Created documentation: `VOTING_SYSTEM.md` and `VOTING_QUICKSTART.md`
- Created example script: `examples/vote_example.py`
- Created test suite: `backend/test_voting.py`

### 2025-12-25: Council Presets Implementation
- Added `COUNCIL_PRESETS` dict to `backend/config.py` with 5 specialized presets
- Added `get_presets()` and `apply_preset()` functions to config.py
- Added `GET /api/presets` endpoint to list available presets
- Added `POST /api/presets/{preset_id}/apply` endpoint to apply presets
- Frontend implementation (Settings dropdown) to be handled separately
