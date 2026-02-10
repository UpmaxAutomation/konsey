---
name: council-query
description: Run a 3-stage deliberation query through the LLM Council. Use when you need consensus from multiple LLMs, peer-reviewed answers, or synthesized expert opinions.
scripts:
  - execution/run_council_query.py
  - backend/council.py
---

# Council Query

## Purpose
Execute a 3-stage deliberation process where multiple LLMs provide independent answers, anonymously review each other's work, and a chairman synthesizes the final response.

## Prerequisites
- OpenRouter API key in `.env`
- Backend server running on port 8001
- Council models configured in `backend/config.py`

## Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | The question to ask the council |
| conversation_id | string | No | Existing conversation to continue |
| preset | string | No | Preset to use (code_review, research, creative, reasoning, budget) |

## Process Steps

### Stage 1: First Opinions
```
Query → All Council Models (parallel)
         ↓
Individual Responses Collected
         ↓
Tab view available for inspection
```

### Stage 2: Peer Review
```
Responses Anonymized (A, B, C...)
         ↓
Each model reviews all responses
         ↓
Rankings with explanations
         ↓
Aggregate rankings calculated
```

### Stage 3: Synthesis
```
All responses + rankings → Chairman
         ↓
Final synthesized answer
         ↓
Green-highlighted conclusion
```

## Outputs
- Stage 1: Individual model responses
- Stage 2: Rankings and evaluations (with de-anonymization mapping)
- Stage 3: Chairman's synthesized final answer
- Metadata: label_to_model mapping, aggregate_rankings

## API Usage

### Python
```python
import httpx

async def run_council_query(query: str, conversation_id: str = None):
    async with httpx.AsyncClient() as client:
        # Create new conversation if needed
        if not conversation_id:
            response = await client.post("http://localhost:8001/api/conversations")
            conversation_id = response.json()["id"]

        # Send query to council
        response = await client.post(
            f"http://localhost:8001/api/conversations/{conversation_id}/message",
            json={"content": query}
        )
        return response.json()
```

### CLI
```bash
# Run via CLI script
python execution/run_council_query.py --query "What is the best programming language for AI?" --preset reasoning
```

### REST API
```bash
# Create conversation
curl -X POST http://localhost:8001/api/conversations

# Send message
curl -X POST http://localhost:8001/api/conversations/{id}/message \
  -H "Content-Type: application/json" \
  -d '{"content": "Your question here"}'
```

## Council Presets

| Preset | Use Case | Models |
|--------|----------|--------|
| code_review | Code analysis | Claude Sonnet 4, GPT-5.1 Codex, DeepSeek V3, Qwen Coder |
| research | Deep analysis | Gemini 2.5 Pro, Claude Opus 4.5, GPT-5, Grok 3 |
| creative | Creative writing | Claude Sonnet 4, GPT-5, Gemini 2.5 Flash |
| reasoning | Logic & math | O3, DeepSeek R1, QwQ 32B, O4 Mini |
| budget | Cost-effective | DeepSeek R1, Qwen Coder, Gemma 2 9B |

## Edge Cases
- Model timeout: Extended to 120s for reasoning models
- Model failure: Graceful degradation, continue with successful responses
- Parse failure: Fallback regex extracts "Response X" patterns

## Self-Annealing Notes
_Auto-updated learnings:_
