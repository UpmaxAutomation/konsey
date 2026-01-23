# LLM Council Voting System

## Overview

The voting system allows the LLM Council to collectively vote on multiple-choice questions. Each council model independently selects one option, provides a confidence level (0-100%), and gives reasoning for their choice.

## Features

- **Multiple Options Support**: 2-26 options per vote
- **Confidence Scores**: Each model provides 0-100% confidence
- **Reasoning**: Models explain their choice
- **Aggregate Results**: View total votes, average confidence, and weighted scores
- **Winner Determination**: Automatically calculates winner based on total score (votes × avg confidence)

## API Endpoint

### POST `/api/conversations/{conversation_id}/vote`

Run a vote on a question with multiple options.

**Request Body:**
```json
{
  "question": "What is the best approach for state management in React?",
  "options": [
    "Redux",
    "Context API",
    "Zustand",
    "MobX"
  ]
}
```

**Response:**
```json
{
  "votes": [
    {
      "model": "anthropic/claude-3.5-sonnet",
      "choice": "Zustand",
      "confidence": 85,
      "reasoning": "Zustand provides a simple, modern API with minimal boilerplate..."
    },
    ...
  ],
  "results": {
    "Redux": {
      "count": 1,
      "avg_confidence": 70.0,
      "voters": [
        {"model": "openai/gpt-4o", "confidence": 70}
      ],
      "total_score": 70.0
    },
    "Zustand": {
      "count": 2,
      "avg_confidence": 82.5,
      "voters": [
        {"model": "anthropic/claude-3.5-sonnet", "confidence": 85},
        {"model": "google/gemini-2.5-flash", "confidence": 80}
      ],
      "total_score": 165.0
    },
    ...
  },
  "winner": {
    "option": "Zustand",
    "total_votes": 2,
    "avg_confidence": 82.5,
    "total_score": 165.0
  }
}
```

## Implementation Details

### Vote Format

Models are prompted to respond in this exact format:

```
VOTE: [option text or number]
CONFIDENCE: [0-100]%
REASON: [reasoning text]
```

**Example:**
```
VOTE: Zustand
CONFIDENCE: 85%
REASON: Zustand provides a simple, modern API with minimal boilerplate while still offering powerful features like middleware and devtools support. It's easier to learn than Redux and more scalable than Context API for complex state.
```

### Option Matching

The parser intelligently matches votes to options using:

1. **Exact match** (case-insensitive): `"zustand"` matches `"Zustand"`
2. **Number match**: `"2"` or `"Option 2"` matches the 2nd option in the list
3. **Partial match**: `"context"` matches `"Context API"`

### Scoring System

- **Total Score** = `vote_count × average_confidence`
- **Winner** = Option with highest total score
- This balances both popularity and confidence

**Example:**
- Option A: 3 votes at 60% avg confidence = 180 score
- Option B: 2 votes at 95% avg confidence = 190 score ← **Winner**

### Error Handling

- Returns empty vote if parsing fails (model didn't follow format)
- Gracefully continues even if some models fail
- Validates 2-26 options (alphabetic labels limit)
- Returns null winner if no valid votes

## Files

- **`backend/voting.py`**: Core voting logic
  - `run_vote()`: Main entry point for running votes
  - `_parse_vote()`: Parses model responses into structured votes
  - `_calculate_results()`: Aggregates votes by option
  - `_determine_winner()`: Finds winning option

- **`backend/main.py`**: API endpoint
  - `VoteRequest`: Pydantic model for request validation
  - `POST /api/conversations/{conversation_id}/vote`: Endpoint handler

- **`backend/test_voting.py`**: Test suite
  - Parser unit tests
  - Full voting system integration test

## Usage Example

```python
import asyncio
from backend.voting import run_vote

async def main():
    question = "Best frontend framework for 2025?"
    options = ["React", "Vue", "Svelte", "SolidJS"]

    results = await run_vote(question, options)

    print(f"Winner: {results['winner']['option']}")
    print(f"Score: {results['winner']['total_score']}")

asyncio.run(main())
```

## Testing

Run the test suite:

```bash
cd /Users/sezars/llm-council
python3 backend/test_voting.py
```

This will:
1. Test the vote parser with various formats
2. Run a full vote with all council models
3. Display individual votes and aggregate results

## Future Enhancements

Potential improvements:

- **Ranked Choice Voting**: Allow models to rank all options
- **Weighted Voting**: Give different weights to different models
- **Streaming Results**: Stream votes as they come in
- **Vote History**: Store votes in conversation history
- **Custom Criteria**: Vote based on specific criteria (speed, cost, ease of use, etc.)
- **Tie Breaking**: Advanced tie-breaking rules
- **Explanatory Synthesis**: Chairman summarizes the vote results and reasoning
