# Voting System Flow Diagram

## High-Level Flow

```
User Request
     ↓
POST /api/conversations/{id}/vote
     ↓
Validate Request
  - Check conversation exists
  - Validate 2-26 options
  - Validate request structure
     ↓
Build Voting Prompt
  - Include question
  - List all options (numbered)
  - Request VOTE/CONFIDENCE/REASON format
     ↓
Query All Council Models in Parallel
  (asyncio.gather)
     ↓
Parse Each Model's Response
  - Extract VOTE (option)
  - Extract CONFIDENCE (0-100%)
  - Extract REASON (text)
  - Match vote to option (exact/numeric/partial)
     ↓
Aggregate Results by Option
  - Count votes per option
  - Calculate average confidence per option
  - Track which models voted for each
  - Calculate total score (votes × avg_confidence)
     ↓
Determine Winner
  - Find option with highest total score
  - Include vote count and confidence
     ↓
Return Results
  {
    votes: [...],
    results: {...},
    winner: {...}
  }
```

## Detailed Vote Processing

```
Model Response:
  "VOTE: PostgreSQL
   CONFIDENCE: 85%
   REASON: PostgreSQL offers ACID compliance..."
     ↓
Parse Vote:
     ↓
  Extract Components:
    - raw_choice = "PostgreSQL"
    - confidence = 85
    - reasoning = "PostgreSQL offers ACID compliance..."
     ↓
  Match to Option:
    ┌─ Try exact match (case-insensitive)
    │   ✓ "PostgreSQL" == "PostgreSQL"
    │
    ├─ Try numeric match
    │   ✗ Not a number
    │
    └─ Try partial match
        ✗ Not needed (exact match succeeded)
     ↓
  Return Parsed Vote:
    {
      choice: "PostgreSQL",
      confidence: 85,
      reasoning: "PostgreSQL offers ACID compliance..."
    }
```

## Result Aggregation Example

```
Input Votes:
  Model A: PostgreSQL @ 85%
  Model B: PostgreSQL @ 90%
  Model C: MongoDB @ 75%
     ↓
Aggregate by Option:
     ↓
  PostgreSQL:
    - count: 2
    - confidences: [85, 90]
    - avg_confidence: 87.5
    - total_score: 2 × 87.5 = 175.0
    - voters: [Model A, Model B]
     ↓
  MongoDB:
    - count: 1
    - confidences: [75]
    - avg_confidence: 75.0
    - total_score: 1 × 75.0 = 75.0
    - voters: [Model C]
     ↓
Winner Determination:
     ↓
  Sort by total_score (descending):
    1. PostgreSQL: 175.0 ← WINNER
    2. MongoDB: 75.0
     ↓
Return Winner:
  {
    option: "PostgreSQL",
    total_votes: 2,
    avg_confidence: 87.5,
    total_score: 175.0
  }
```

## Scoring Examples

### Example 1: Confidence Matters
```
Option A: 3 votes @ 60% avg = 180 score
Option B: 2 votes @ 95% avg = 190 score ← WINNER

Interpretation: Even with fewer votes, Option B wins
because models are much more confident about it.
```

### Example 2: Clear Consensus
```
Option A: 4 votes @ 85% avg = 340 score ← WINNER
Option B: 1 vote @ 90% avg = 90 score

Interpretation: Strong consensus with high confidence
makes Option A the clear winner.
```

### Example 3: Split Decision
```
Option A: 2 votes @ 80% avg = 160 score
Option B: 2 votes @ 78% avg = 156 score ← Very close

Interpretation: Nearly tied. Small differences in
confidence break the tie.
```

## Error Handling Flow

```
Model Response Parse
     ↓
  Check for VOTE field
     ├─ Found: Continue
     └─ Not Found: Return None (skip this vote)
     ↓
  Match to valid option
     ├─ Matched: Continue
     └─ No Match: Return None (skip this vote)
     ↓
  Extract confidence
     ├─ Found: Use value (clamped 0-100)
     └─ Not Found: Default to 50%
     ↓
  Extract reasoning
     ├─ Found: Use text
     └─ Not Found: "No reasoning provided"
     ↓
Return Valid Vote
```

## Parallel Execution

```
┌─────────────────────────────────────┐
│  POST /vote request received        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  asyncio.gather() starts parallel   │
│  queries to all council models      │
└─────────────────────────────────────┘
                 ↓
    ┌────────────┴────────────┐
    ↓            ↓            ↓
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Model A │ │ Model B │ │ Model C │
│  Query  │ │  Query  │ │  Query  │
└─────────┘ └─────────┘ └─────────┘
    ↓            ↓            ↓
┌─────────┐ ┌─────────┐ ┌─────────┐
│Response │ │Response │ │Response │
└─────────┘ └─────────┘ └─────────┘
    └────────────┬────────────┘
                 ↓
┌─────────────────────────────────────┐
│  All responses collected            │
│  (or timeout after 60s)             │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  Parse each response in sequence    │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  Aggregate results                  │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│  Return JSON response               │
└─────────────────────────────────────┘
```

## Option Matching Logic

```
Input: raw_choice = "postgres"
Options: ["PostgreSQL", "MongoDB", "MySQL"]
     ↓
Step 1: Exact Match (case-insensitive)
  "postgres" == "postgresql"? ✗
  "postgres" == "mongodb"? ✗
  "postgres" == "mysql"? ✗
     ↓
Step 2: Numeric Match
  Is "postgres" a number? ✗
     ↓
Step 3: Partial Match
  "postgres" in "postgresql"? ✓ MATCH!
     ↓
Return: "PostgreSQL"
```

## Vote Format Variations Handled

```
✓ Supported Formats:

  VOTE: PostgreSQL
  CONFIDENCE: 85%
  REASON: ...

  VOTE: 1
  CONFIDENCE: 85
  REASON: ...

  VOTE: Option 2
  CONFIDENCE: 85%
  REASON: ...

  vote: postgres
  confidence: 85%
  reason: ...

✗ Unsupported (will be skipped):

  I vote for PostgreSQL (no VOTE: prefix)

  VOTE:
  (empty vote)

  My confidence is 85% (no CONFIDENCE: prefix)
```

## Response Structure

```
{
  "votes": [
    {
      "model": "anthropic/claude-3.5-sonnet",
      "choice": "PostgreSQL",
      "confidence": 85,
      "reasoning": "..."
    },
    ...
  ],
  "results": {
    "PostgreSQL": {
      "count": 2,
      "avg_confidence": 87.5,
      "voters": [
        {"model": "...", "confidence": 85},
        {"model": "...", "confidence": 90}
      ],
      "total_score": 175.0
    },
    ...
  },
  "winner": {
    "option": "PostgreSQL",
    "total_votes": 2,
    "avg_confidence": 87.5,
    "total_score": 175.0
  }
}
```
