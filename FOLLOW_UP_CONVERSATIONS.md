# Follow-up Conversation Implementation

This document describes the implementation of follow-up conversation support in LLM Council, allowing models to reference previous exchanges for contextual follow-up questions.

## Overview

When users send a follow-up message in an existing conversation, the council models now receive summarized context from the previous 3 exchanges (configurable). This enables them to:

- Answer questions that reference previous topics
- Maintain conversational continuity
- Provide contextually aware responses without re-explaining background

## Implementation Details

### 1. Storage Layer (`backend/storage.py`)

Added new function `get_conversation_context()`:

```python
def get_conversation_context(conversation_id: str, limit: int = 3) -> Optional[str]
```

**Functionality:**
- Extracts the last N user-assistant exchange pairs from conversation history
- Pairs user questions with their corresponding synthesized answers (from stage3)
- Truncates long responses (questions: 300 chars, answers: 500 chars) to manage token usage
- Formats as a readable summary with numbered exchanges
- Returns `None` for empty conversations (first message)

**Example Output:**
```
Previous conversation context:

Exchange 1:
Q: What is the capital of France?
A: The capital of France is Paris...

Exchange 2:
Q: What about Germany?
A: The capital of Germany is Berlin...
```

### 2. Council Layer (`backend/council.py`)

#### Updated `stage1_collect_responses()`

Added optional `context` parameter:

```python
async def stage1_collect_responses(
    user_query: str,
    context: Optional[str] = None
) -> List[Dict[str, Any]]
```

**Behavior:**
- If context is provided, prepends it to the user query with a separator
- Models receive: `{context}\n\n---\n\nCurrent Question: {user_query}`
- Maintains backward compatibility (context defaults to `None`)

#### Updated `run_full_council()`

Added optional `conversation_context` parameter:

```python
async def run_full_council(
    user_query: str,
    conversation_context: Optional[str] = None
) -> Tuple[List, List, Dict, Dict]
```

**Behavior:**
- Accepts conversation context as a parameter
- Passes conversation context to Stage 1 (individual model responses)
- Keeps Stage 2 (ranking) and Stage 3 (synthesis) using original query only
- Conversation context is prioritized over enhanced features (web search, memory)

**Context Priority Order:**
1. Conversation history (most relevant)
2. Web search results (if enabled)
3. Memory context (if enabled)

### 3. API Layer (`backend/main.py`)

#### Updated `/api/conversations/{id}/message` endpoint

**Changes:**
1. Checks if this is a follow-up message (`is_first_message == False`)
2. Retrieves conversation context **before** adding the current user message
3. Passes context to `run_full_council()`

**Code:**
```python
# Get conversation context for follow-up questions (before adding current message)
conversation_context = None
if not is_first_message:
    conversation_context = storage.get_conversation_context(conversation_id, limit=3)

# Run the 3-stage council process with context
stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
    request.content,
    conversation_context=conversation_context
)
```

#### Updated `/api/conversations/{id}/message/stream` endpoint

**Changes:**
- Same logic as non-streaming endpoint
- Retrieves context before starting event generation
- Passes context to `stage1_collect_responses()` during streaming

## Usage Examples

### Example 1: Geographic Follow-up

**First message:**
```
User: What is the capital of France?
Council: The capital of France is Paris.
```

**Follow-up message:**
```
User: What about its population?

[Models receive:]
Previous conversation context:

Exchange 1:
Q: What is the capital of France?
A: The capital of France is Paris...

---

Current Question: What about its population?
```

The models understand "its" refers to Paris based on the context.

### Example 2: Multi-turn Technical Discussion

**Exchange 1:**
```
User: Explain async/await in Python
Council: [Detailed explanation]
```

**Exchange 2:**
```
User: How does it compare to threads?
Council: [Comparison with context from previous answer]
```

**Exchange 3:**
```
User: Show me an example combining both approaches

[Models receive context from last 2 exchanges]
```

## Configuration

### Context Limit

Default: **3 exchanges**

To modify, change the `limit` parameter in `main.py`:

```python
conversation_context = storage.get_conversation_context(conversation_id, limit=5)
```

### Truncation Limits

Defined in `storage.py`:
- Questions: 300 characters
- Answers: 500 characters

To modify:
```python
question = exchange["question"][:500]  # Increase to 500
answer = exchange["answer"][:1000]     # Increase to 1000
```

## Testing

### Automated Test

Run the standalone test:
```bash
cd /Users/sezars/llm-council
python3 test_context_standalone.py
```

**Tests verify:**
- ✅ Correct pairing of questions with answers
- ✅ Proper limiting (last N exchanges only)
- ✅ Empty conversation handling (returns None)
- ✅ Context formatting for enhanced queries

### Manual Testing

1. Start the backend: `cd backend && python3 -m uvicorn main:app --reload --port 8001`
2. Create a conversation via API
3. Send first message: `POST /api/conversations/{id}/message`
4. Send follow-up: `POST /api/conversations/{id}/message`
5. Check Stage 1 responses to verify models received context

**Expected behavior:**
- First message: No context in Stage 1 prompts
- Second message: Context includes first exchange
- Third message: Context includes exchanges 1-2 (or all if <3 total)

## Performance Considerations

### Token Usage

Each follow-up message adds ~100-300 tokens for context (depends on conversation complexity).

**Estimation:**
- 3 exchanges × (300 char question + 500 char answer) = ~2,400 characters
- ~600 tokens per follow-up message
- Multiply by number of council models (e.g., 3 models = 1,800 tokens)

### Optimization Tips

1. **Reduce limit**: Use `limit=2` for most use cases
2. **Truncate aggressively**: Lower character limits for questions/answers
3. **Selective context**: Only include context for questions with pronouns (future enhancement)

## Backward Compatibility

✅ **Fully backward compatible**

All changes use optional parameters with default values:
- `context: Optional[str] = None`
- `conversation_context: Optional[str] = None`

Existing code calling without context parameters continues to work unchanged.

## Future Enhancements

### Intelligent Context Detection

Only include context when follow-up is detected:
```python
def is_followup_question(query: str) -> bool:
    pronouns = ["it", "that", "this", "they", "those", "these"]
    return any(pronoun in query.lower().split() for pronoun in pronouns)
```

### Configurable Truncation

Add configuration options:
```python
CONTEXT_CONFIG = {
    "limit": 3,
    "max_question_length": 300,
    "max_answer_length": 500,
    "auto_detect_followup": True
}
```

### Semantic Context Selection

Use embeddings to select most relevant past exchanges instead of just last N.

### Context in Stage 2 & 3

Currently only Stage 1 receives context. Consider:
- Stage 2: Include context when ranking responses
- Stage 3: Explicitly mention context in chairman synthesis

## Architecture Diagram

```
User sends follow-up message
        ↓
GET conversation history (storage.py)
        ↓
Extract last 3 exchanges (get_conversation_context)
        ↓
Format as readable summary
        ↓
Pass to run_full_council(query, context)
        ↓
Stage 1: Prepend context to query → Models respond with awareness
        ↓
Stage 2: Rank responses (no context needed)
        ↓
Stage 3: Synthesize final answer (context implicit in Stage 1 responses)
        ↓
Return to user
```

## Summary of Changes

### Files Modified

1. **`backend/storage.py`**
   - Added `get_conversation_context()` function

2. **`backend/council.py`**
   - Modified `stage1_collect_responses()` to accept optional context
   - Modified `run_full_council()` to accept and pass conversation context

3. **`backend/main.py`**
   - Updated `send_message()` to retrieve and pass context
   - Updated `send_message_stream()` to retrieve and pass context

### Files Created

1. **`test_context_standalone.py`** - Standalone test suite
2. **`FOLLOW_UP_CONVERSATIONS.md`** - This documentation

### Lines of Code

- Storage layer: ~60 lines (new function)
- Council layer: ~10 lines (parameter additions)
- API layer: ~8 lines (context retrieval)
- Tests: ~170 lines
- **Total: ~250 lines of code**

## Conclusion

The follow-up conversation feature is now fully implemented and tested. Users can have natural multi-turn conversations where the council models maintain context and provide coherent, contextually-aware responses across multiple exchanges.
