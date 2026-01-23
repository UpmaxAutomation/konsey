# Quick Mode Implementation

Quick Mode is a new feature that allows single-model chat without the 3-stage council deliberation process. This provides a faster, ChatGPT-like experience when you don't need the full council workflow.

## Overview

Quick Mode enables:
- Direct queries to a single LLM model
- Real-time streaming responses (Server-Sent Events)
- Conversation context for follow-up questions
- Support for reasoning models with thinking display
- Token usage tracking
- Automatic title generation for new conversations

## Architecture

### Backend Components

#### 1. Storage (`backend/storage.py`)

**New Function: `add_quick_message()`**
```python
def add_quick_message(
    conversation_id: str,
    content: str,
    model: str,
    thinking: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None
)
```

Stores quick mode messages with:
- `type: "quick"` (vs `type: "council"` for council messages)
- `content`: The model's response
- `model`: Which model generated the response
- `thinking`: Optional reasoning content for reasoning models
- `usage`: Token usage statistics

**Message Structure:**
```json
{
  "role": "assistant",
  "type": "quick",
  "content": "The response text...",
  "model": "openai/gpt-4o",
  "thinking": "Optional reasoning content...",
  "usage": {
    "input_tokens": 150,
    "output_tokens": 200,
    "cost": 0.00035
  }
}
```

#### 2. API Endpoints (`backend/main.py`)

**POST `/api/conversations/{id}/quick-message`**

Streams a single model's response in real-time.

Request Body:
```json
{
  "content": "Your question here",
  "model": "openai/gpt-4o"  // Optional, defaults to chairman model
}
```

Response Events (SSE):
- `chunk`: Incremental text as it's generated
  ```json
  {"type": "chunk", "data": "partial text"}
  ```
- `title_complete`: Generated conversation title (first message only)
  ```json
  {"type": "title_complete", "data": {"title": "Generated Title"}}
  ```
- `complete`: Final response with metadata
  ```json
  {
    "type": "complete",
    "data": {
      "content": "Full response text",
      "model": "openai/gpt-4o",
      "thinking": "Reasoning content (if available)",
      "usage": {
        "input_tokens": 150,
        "output_tokens": 200,
        "cost": 0.00035
      }
    }
  }
  ```
- `error`: Error occurred
  ```json
  {"type": "error", "message": "Error description"}
  ```

**GET `/api/chat/models`**

Returns available models for Quick Mode.

Response:
```json
{
  "models": [
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4o",
      "input_cost": 2.50,
      "output_cost": 10.00
    },
    ...
  ],
  "default_model": "google/gemini-2.5-flash",
  "count": 50
}
```

### Streaming Implementation

Quick Mode uses the existing `query_model_stream()` function from `openrouter.py`:

```python
async for chunk in query_model_stream(model_to_use, messages):
    if chunk.get("chunk"):
        # Stream incremental text to frontend
        yield f"data: {json.dumps({'type': 'chunk', 'data': chunk['chunk']})}\n\n"

    if chunk.get("done"):
        # Final metadata available
        usage_info = chunk.get("usage")
        thinking = chunk.get("thinking")
```

## Features

### 1. Real-time Streaming
- Text streams token-by-token as the model generates it
- Provides immediate feedback to users
- Uses Server-Sent Events (SSE) for reliable streaming

### 2. Conversation Context
- Maintains conversation history (last 3 exchanges)
- Enables coherent follow-up questions
- Reuses existing `get_conversation_context()` function

### 3. Reasoning Model Support
- Automatically detects reasoning models (O1, O3, R1, QwQ, etc.)
- Captures internal "thinking" process
- Returns thinking content in the response

### 4. Token Tracking
- Tracks input/output tokens per request
- Calculates costs based on model pricing
- Updates global session usage statistics

### 5. Automatic Title Generation
- Generates conversation title from first message
- Runs in parallel with response generation
- Uses same logic as council mode

## Usage Examples

### Python (using httpx)

```python
import httpx
import json

async def quick_chat(conversation_id: str, message: str, model: str = None):
    url = f"http://localhost:8001/api/conversations/{conversation_id}/quick-message"

    payload = {"content": message}
    if model:
        payload["model"] = model

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])

                    if data["type"] == "chunk":
                        print(data["data"], end="", flush=True)

                    elif data["type"] == "complete":
                        print(f"\n\nCost: ${data['data']['usage']['cost']:.6f}")
                        if "thinking" in data["data"]:
                            print(f"Thinking: {data['data']['thinking'][:100]}...")
```

### JavaScript (using fetch)

```javascript
async function quickChat(conversationId, message, model = null) {
  const response = await fetch(
    `/api/conversations/${conversationId}/quick-message`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: message, model })
    }
  );

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6));

        if (event.type === 'chunk') {
          console.log(event.data); // Stream to UI
        } else if (event.type === 'complete') {
          console.log('Done:', event.data);
        } else if (event.type === 'error') {
          console.error('Error:', event.message);
        }
      }
    }
  }
}
```

## Comparison: Quick Mode vs Council Mode

| Feature | Quick Mode | Council Mode |
|---------|-----------|--------------|
| Models | Single model | 3-4 models + chairman |
| Response Time | ~2-5 seconds | ~10-30 seconds |
| Streaming | ✅ Real-time | ✅ Per-stage |
| Cost | $0.001-0.01/query | $0.005-0.05/query |
| Reasoning | Available for reasoning models | Available in Stage 1 |
| Use Cases | Quick questions, coding, chat | Complex decisions, research |

## Integration with Frontend

The frontend should:

1. **Add a mode toggle** to switch between Council and Quick Mode
2. **Display streaming text** as chunks arrive
3. **Show model selector** to choose which model to use
4. **Handle thinking display** for reasoning models
5. **Update UI instantly** as text streams in

Example React component structure:
```jsx
<QuickModeChat>
  <ModelSelector models={availableModels} />
  <MessageList messages={messages} />
  <StreamingResponse chunks={currentChunks} />
  <InputBox onSend={sendQuickMessage} />
</QuickModeChat>
```

## Performance Considerations

### Advantages
- **3-10x faster** than council mode for simple queries
- **Lower cost** - only one model query instead of 4-5
- **Better UX** - streaming provides immediate feedback
- **Scalable** - can handle high-frequency chat interactions

### Trade-offs
- **Single perspective** - no peer review or ranking
- **Less robust** - no fallback if model fails
- **No synthesis** - what you get is what the model says

## Error Handling

Quick Mode handles errors gracefully:

1. **Invalid model**: Returns 400 with error message
2. **Conversation not found**: Returns 404
3. **Streaming error**: Sends error event via SSE
4. **Model timeout**: Returns after timeout with partial response

All errors are sent as SSE events:
```json
{"type": "error", "message": "Detailed error description"}
```

## Future Enhancements

Potential improvements:
- [ ] Multi-turn conversation with conversation memory
- [ ] Model auto-selection based on query type
- [ ] Hybrid mode: Quick mode with optional peer review
- [ ] Response caching for repeated queries
- [ ] Custom system prompts per conversation
- [ ] Temperature/sampling controls
- [ ] Token budget limits per conversation

## Testing

Test the endpoints:

```bash
# 1. Create a conversation
curl -X POST http://localhost:8001/api/conversations

# 2. Get available models
curl http://localhost:8001/api/chat/models

# 3. Send a quick message (streaming)
curl -X POST http://localhost:8001/api/conversations/{id}/quick-message \
  -H "Content-Type: application/json" \
  -d '{"content": "What is 2+2?", "model": "openai/gpt-4o"}' \
  --no-buffer

# 4. Verify message was saved
curl http://localhost:8001/api/conversations/{id}
```

## Summary

Quick Mode provides a lightweight, fast alternative to council deliberation when you need:
- Rapid responses
- Simple queries
- Lower costs
- ChatGPT-like interaction

It integrates seamlessly with the existing conversation system while maintaining all the benefits of streaming, context awareness, and reasoning model support.
