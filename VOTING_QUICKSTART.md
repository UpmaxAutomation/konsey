# Voting System - Quick Start Guide

## What is it?

The LLM Council voting system allows all council models to vote on a multiple-choice question, each providing their choice, confidence level (0-100%), and reasoning.

## How to Use

### 1. Start the Backend

```bash
cd /Users/sezars/llm-council
python3 -m backend.main
```

Backend runs on `http://localhost:8001`

### 2. Create a Conversation

```bash
curl -X POST http://localhost:8001/api/conversations
```

Save the `id` from the response.

### 3. Run a Vote

```bash
curl -X POST "http://localhost:8001/api/conversations/{conversation_id}/vote" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the best database for a startup?",
    "options": ["PostgreSQL", "MongoDB", "MySQL", "Supabase"]
  }'
```

### 4. Using Python

```python
import requests

# Create conversation
response = requests.post("http://localhost:8001/api/conversations")
conversation_id = response.json()["id"]

# Run vote
vote_result = requests.post(
    f"http://localhost:8001/api/conversations/{conversation_id}/vote",
    json={
        "question": "Best frontend framework for 2025?",
        "options": ["React", "Vue", "Svelte", "SolidJS"]
    }
).json()

# Print winner
winner = vote_result["winner"]
print(f"Winner: {winner['option']}")
print(f"Votes: {winner['total_votes']}")
print(f"Confidence: {winner['avg_confidence']}%")
```

## Response Format

```json
{
  "votes": [
    {
      "model": "anthropic/claude-3.5-sonnet",
      "choice": "React",
      "confidence": 85,
      "reasoning": "Most mature ecosystem with strongest community support..."
    }
  ],
  "results": {
    "React": {
      "count": 2,
      "avg_confidence": 82.5,
      "voters": [...],
      "total_score": 165.0
    },
    ...
  },
  "winner": {
    "option": "React",
    "total_votes": 2,
    "avg_confidence": 82.5,
    "total_score": 165.0
  }
}
```

## Understanding the Scoring

- **Total Score** = `votes × average_confidence`
- Higher score wins (balances popularity and confidence)

**Example:**
- Option A: 3 votes @ 60% = 180 score
- Option B: 2 votes @ 95% = 190 score ← **Winner**

## Run Example Script

```bash
cd /Users/sezars/llm-council
python3 examples/vote_example.py
```

This runs three example votes with different questions.

## Constraints

- Minimum 2 options
- Maximum 26 options (A-Z labeling)
- Each vote requires valid conversation ID

## Common Use Cases

1. **Technical Decisions**: "Which database should we use?"
2. **Architecture Choices**: "Monolith vs Microservices?"
3. **Library Selection**: "Best state management library?"
4. **Approach Comparison**: "TDD vs BDD vs no testing framework?"
5. **Priority Setting**: "What should we build first?"

## Tips

- Make questions specific and clear
- Provide distinct options (avoid overlap)
- Include relevant context in the question
- Check individual reasoning to understand the vote
- Use confidence scores to gauge certainty

## See Also

- **Full Documentation**: `/Users/sezars/llm-council/VOTING_SYSTEM.md`
- **Example Code**: `/Users/sezars/llm-council/examples/vote_example.py`
- **Test Suite**: `/Users/sezars/llm-council/backend/test_voting.py`
