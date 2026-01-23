---
name: preset-management
description: Manage council presets for different use cases. Use to switch between specialized model configurations quickly.
scripts:
  - execution/manage_presets.py
  - backend/config.py
---

# Preset Management

## Purpose
Apply and manage pre-configured council setups optimized for specific use cases like code review, research, creative writing, or budget-conscious queries.

## Prerequisites
- Backend server running
- Understanding of use case requirements

## Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| action | string | Yes | "list", "apply", "get" |
| preset_id | string | Conditional | Required for "apply" and "get" |

## Available Presets

### code_review
**Purpose**: Expert code analysis and review
```yaml
chairman: anthropic/claude-sonnet-4
council:
  - anthropic/claude-sonnet-4
  - openai/gpt-5.1-codex
  - deepseek/deepseek-v3
  - qwen/qwen-coder
```

### research
**Purpose**: Deep research and analysis
```yaml
chairman: google/gemini-2.5-pro
council:
  - google/gemini-2.5-pro
  - anthropic/claude-opus-4.5
  - openai/gpt-5
  - x-ai/grok-3
```

### creative
**Purpose**: Creative writing and brainstorming
```yaml
chairman: anthropic/claude-sonnet-4
council:
  - anthropic/claude-sonnet-4
  - openai/gpt-5
  - google/gemini-2.5-flash
```

### reasoning
**Purpose**: Complex logic and mathematics
```yaml
chairman: openai/o3
council:
  - openai/o3
  - deepseek/deepseek-r1
  - qwen/qwq-32b
  - openai/o4-mini
```

### budget
**Purpose**: Cost-effective queries
```yaml
chairman: deepseek/deepseek-r1-0528
council:
  - deepseek/deepseek-r1-0528
  - qwen/qwen-coder
  - google/gemma-2-9b-free
```

## API Usage

### Python
```python
import httpx

async def list_presets():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8001/api/presets")
        return response.json()

async def apply_preset(preset_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://localhost:8001/api/presets/{preset_id}/apply")
        return response.json()
```

### CLI
```bash
# List all presets
python execution/manage_presets.py --action list

# Apply a preset
python execution/manage_presets.py --action apply --preset code_review
```

### REST API
```bash
# List presets
curl http://localhost:8001/api/presets

# Apply preset
curl -X POST http://localhost:8001/api/presets/reasoning/apply
```

## Outputs

### List Response
```json
{
  "presets": [
    {
      "id": "code_review",
      "name": "Code Review Council",
      "description": "Expert code reviewers...",
      "models": ["anthropic/claude-sonnet-4", "..."],
      "chairman": "anthropic/claude-sonnet-4"
    }
  ]
}
```

### Apply Response
```json
{
  "status": "success",
  "message": "Applied preset: Code Review Council",
  "council_models": ["..."],
  "chairman_model": "anthropic/claude-sonnet-4",
  "preset_name": "Code Review Council",
  "preset_description": "..."
}
```

## Edge Cases
- Invalid preset ID: Returns 404 error
- Model unavailable: May fail during query (check OpenRouter status)

## Self-Annealing Notes
_Auto-updated learnings:_
