---
name: council-vote
description: Run a voting session where council members vote on multiple-choice options. Use for decision-making, A/B testing, preference ranking, or consensus building.
scripts:
  - execution/run_council_vote.py
  - backend/voting.py
---

# Council Vote

## Purpose
Have all council members vote on a multiple-choice question, with each providing their choice, confidence level, and reasoning. Determines winner by total score (votes × average confidence).

## Prerequisites
- OpenRouter API key in `.env`
- Backend server running on port 8001
- Active conversation (creates one if not provided)

## Inputs
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| question | string | Yes | The question to vote on |
| options | list | Yes | 2-26 options to choose from |
| conversation_id | string | No | Existing conversation context |

## Process Steps

### 1. Option Presentation
```
Question + Options → All Council Models
         ↓
Each model receives same prompt
```

### 2. Individual Voting
```
Each model responds with:
├── VOTE: Their chosen option
├── CONFIDENCE: 0-100% certainty
└── REASON: Brief explanation
```

### 3. Vote Aggregation
```
All votes collected
         ↓
Results grouped by option
         ↓
Total score = votes × avg confidence
         ↓
Winner determined
```

## Outputs
```json
{
  "votes": [
    {
      "model": "openai/gpt-5.1",
      "vote": "Option A",
      "confidence": 85,
      "reason": "Most comprehensive approach"
    }
  ],
  "results": {
    "Option A": {
      "count": 3,
      "avg_confidence": 82.5,
      "total_score": 247.5
    }
  },
  "winner": {
    "option": "Option A",
    "votes": 3,
    "avg_confidence": 82.5,
    "total_score": 247.5
  }
}
```

## API Usage

### Python
```python
import httpx

async def run_vote(question: str, options: list, conversation_id: str = None):
    async with httpx.AsyncClient() as client:
        if not conversation_id:
            response = await client.post("http://localhost:8001/api/conversations")
            conversation_id = response.json()["id"]

        response = await client.post(
            f"http://localhost:8001/api/conversations/{conversation_id}/vote",
            json={"question": question, "options": options}
        )
        return response.json()
```

### CLI
```bash
python execution/run_council_vote.py \
  --question "Which database should we use?" \
  --options "PostgreSQL,MongoDB,Redis,SQLite"
```

### REST API
```bash
curl -X POST http://localhost:8001/api/conversations/{id}/vote \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which framework is best for this project?",
    "options": ["React", "Vue", "Svelte", "Angular"]
  }'
```

## Use Cases

| Scenario | Question Example |
|----------|------------------|
| Tech decisions | "Which database for high-write workloads?" |
| Code review | "Which implementation is most maintainable?" |
| Design choices | "Which UI pattern is most intuitive?" |
| Strategy | "Which market segment to target first?" |

## Vote Matching Logic
```
Priority:
1. Exact match (case-insensitive)
2. Numeric match ("1" → first option)
3. Partial match (substring)
```

## Edge Cases
- Invalid option: Vote recorded but flagged
- 0% confidence: Still counts but weighted low
- Model timeout: Excluded from results, continues with others

## Self-Annealing Notes
_Auto-updated learnings:_
