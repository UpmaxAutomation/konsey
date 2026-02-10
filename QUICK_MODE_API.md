# Quick Mode API Reference

Complete API documentation for the Quick Mode feature.

## Table of Contents

- [Overview](#overview)
- [Endpoints](#endpoints)
  - [POST /api/conversations/{id}/quick-message](#post-quick-message)
  - [GET /api/chat/models](#get-chat-models)
- [Data Structures](#data-structures)
- [Event Stream Format](#event-stream-format)
- [Error Handling](#error-handling)
- [Code Examples](#code-examples)

---

## Overview

Quick Mode provides a streamlined chat interface that queries a single LLM model directly, bypassing the 3-stage council deliberation. Responses are streamed in real-time using Server-Sent Events (SSE).

**Base URL:** `http://localhost:8001`

**Authentication:** Currently not required (API keys stored server-side)

---

## Endpoints

### POST /api/conversations/{id}/quick-message

Stream a single model's response to a user message.

**URL:** `/api/conversations/{conversation_id}/quick-message`

**Method:** `POST`

**Content-Type:** `application/json`

**Response Type:** `text/event-stream`

#### Request Parameters

**Path Parameters:**
- `conversation_id` (string, required): The conversation ID

**Request Body:**
```json
{
  "content": "Your message here",
  "model": "openai/gpt-4o"  // Optional
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | The user's message/question |
| model | string | No | Model ID to use. Defaults to chairman model if not provided |

#### Response

Returns a stream of Server-Sent Events with the following event types:

**Event: chunk**
```
data: {"type": "chunk", "data": "incremental text"}
```

**Event: title_complete** (only on first message)
```
data: {"type": "title_complete", "data": {"title": "Generated Title"}}
```

**Event: complete**
```json
data: {
  "type": "complete",
  "data": {
    "content": "Full response text",
    "model": "openai/gpt-4o",
    "usage": {
      "input_tokens": 150,
      "output_tokens": 200,
      "cost": 0.00035
    },
    "thinking": "Reasoning content (optional, for reasoning models)"
  }
}
```

**Event: error**
```
data: {"type": "error", "message": "Error description"}
```

#### Status Codes

- `200 OK`: Stream started successfully
- `400 Bad Request`: Invalid model ID
- `404 Not Found`: Conversation not found
- `500 Internal Server Error`: Server error during processing

#### Example Request

```bash
curl -X POST http://localhost:8001/api/conversations/abc123/quick-message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Explain quantum computing in simple terms",
    "model": "anthropic/claude-sonnet-4"
  }' \
  --no-buffer
```

---

### GET /api/chat/models

Retrieve all available models for Quick Mode.

**URL:** `/api/chat/models`

**Method:** `GET`

**Content-Type:** `application/json`

#### Response

```json
{
  "models": [
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4o",
      "input_cost": 2.50,
      "output_cost": 10.00
    },
    {
      "id": "anthropic/claude-sonnet-4",
      "name": "Claude Sonnet 4",
      "input_cost": 3.00,
      "output_cost": 15.00
    }
    // ... more models
  ],
  "default_model": "google/gemini-2.5-flash",
  "count": 50
}
```

| Field | Type | Description |
|-------|------|-------------|
| models | array | List of available model objects |
| models[].id | string | Model identifier for API requests |
| models[].name | string | Human-readable model name |
| models[].input_cost | number | Cost per 1M input tokens (USD) |
| models[].output_cost | number | Cost per 1M output tokens (USD) |
| default_model | string | Model ID used when no model is specified |
| count | number | Total number of available models |

#### Status Codes

- `200 OK`: Successfully retrieved models list

#### Example Request

```bash
curl http://localhost:8001/api/chat/models
```

#### Example Response

```json
{
  "models": [
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4o",
      "input_cost": 2.5,
      "output_cost": 10.0
    },
    {
      "id": "anthropic/claude-sonnet-4",
      "name": "Claude Sonnet 4",
      "input_cost": 3.0,
      "output_cost": 15.0
    },
    {
      "id": "google/gemini-2.5-flash",
      "name": "Gemini 2.5 Flash",
      "input_cost": 0.15,
      "output_cost": 0.6
    }
  ],
  "default_model": "google/gemini-2.5-flash",
  "count": 50
}
```

---

## Data Structures

### QuickMessageRequest

Request payload for sending a quick message.

```typescript
interface QuickMessageRequest {
  content: string;      // User's message
  model?: string;       // Optional model ID
}
```

### QuickMessageResponse

Stored message format in the conversation.

```typescript
interface QuickMessage {
  role: "assistant";
  type: "quick";
  content: string;           // Model's response
  model: string;             // Model ID used
  thinking?: string;         // Reasoning content (for reasoning models)
  usage?: {
    input_tokens: number;
    output_tokens: number;
    cost: number;
  };
}
```

### ModelInfo

Information about an available model.

```typescript
interface ModelInfo {
  id: string;           // Model identifier (e.g., "openai/gpt-4o")
  name: string;         // Display name (e.g., "GPT-4o")
  input_cost: number;   // USD per 1M input tokens
  output_cost: number;  // USD per 1M output tokens
}
```

---

## Event Stream Format

Quick Mode uses Server-Sent Events (SSE) for streaming responses.

### Event Types

#### 1. chunk
Incremental text as it's generated.

```
data: {"type": "chunk", "data": "Hello"}
data: {"type": "chunk", "data": " world"}
data: {"type": "chunk", "data": "!"}
```

**Fields:**
- `type`: Always "chunk"
- `data`: String fragment to append to the response

#### 2. title_complete
Generated title for the conversation (first message only).

```
data: {"type": "title_complete", "data": {"title": "Discussion about AI"}}
```

**Fields:**
- `type`: Always "title_complete"
- `data.title`: Generated conversation title

#### 3. complete
Final response with full metadata.

```json
data: {
  "type": "complete",
  "data": {
    "content": "Complete response text...",
    "model": "openai/gpt-4o",
    "usage": {
      "input_tokens": 150,
      "output_tokens": 200,
      "cost": 0.00035
    },
    "thinking": "For reasoning models only..."
  }
}
```

**Fields:**
- `type`: Always "complete"
- `data.content`: Full response text
- `data.model`: Model ID that generated the response
- `data.usage`: Token usage and cost information
- `data.thinking`: Optional reasoning content

#### 4. error
Error occurred during processing.

```
data: {"type": "error", "message": "Model timeout"}
```

**Fields:**
- `type`: Always "error"
- `message`: Error description

### Event Stream Example

```
data: {"type": "chunk", "data": "The"}

data: {"type": "chunk", "data": " capital"}

data: {"type": "chunk", "data": " of"}

data: {"type": "chunk", "data": " France"}

data: {"type": "chunk", "data": " is"}

data: {"type": "chunk", "data": " Paris"}

data: {"type": "chunk", "data": "."}

data: {"type": "complete", "data": {"content": "The capital of France is Paris.", "model": "openai/gpt-4o", "usage": {"input_tokens": 10, "output_tokens": 8, "cost": 0.00013}}}
```

---

## Error Handling

### HTTP Errors

| Status Code | Description | Cause |
|-------------|-------------|-------|
| 400 | Bad Request | Invalid model ID or malformed request |
| 404 | Not Found | Conversation doesn't exist |
| 500 | Internal Server Error | Server-side processing error |

### Stream Errors

Errors during streaming are sent as SSE events:

```
data: {"type": "error", "message": "Connection timeout"}
```

Common error scenarios:
- **Model timeout**: Model took too long to respond
- **API key missing**: No API key configured for the provider
- **Rate limit**: Exceeded API rate limits
- **Invalid response**: Model returned malformed data

**Client Handling:**
```javascript
if (event.type === 'error') {
  console.error('Stream error:', event.message);
  // Display error to user
  // Optionally retry or fall back to different model
}
```

---

## Code Examples

### Python (using httpx)

```python
import httpx
import json

async def send_quick_message(conversation_id: str, message: str, model: str = None):
    """Send a message in Quick Mode with streaming."""
    url = f"http://localhost:8001/api/conversations/{conversation_id}/quick-message"

    payload = {"content": message}
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()

            full_response = ""

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue

                event = json.loads(line[6:])

                if event["type"] == "chunk":
                    chunk_text = event["data"]
                    print(chunk_text, end="", flush=True)
                    full_response += chunk_text

                elif event["type"] == "title_complete":
                    print(f"\nTitle: {event['data']['title']}")

                elif event["type"] == "complete":
                    data = event["data"]
                    print(f"\n\nModel: {data['model']}")
                    print(f"Tokens: {data['usage']['input_tokens']} in, {data['usage']['output_tokens']} out")
                    print(f"Cost: ${data['usage']['cost']:.6f}")

                    if "thinking" in data:
                        print(f"\nThinking:\n{data['thinking'][:200]}...")

                elif event["type"] == "error":
                    print(f"\nError: {event['message']}")
                    break

            return full_response

# Usage
import asyncio
response = asyncio.run(send_quick_message(
    "conv-123",
    "Explain the Big O notation",
    model="anthropic/claude-sonnet-4"
))
```

### JavaScript (Browser)

```javascript
async function sendQuickMessage(conversationId, message, model = null) {
  const url = `/api/conversations/${conversationId}/quick-message`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: message, model })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let fullResponse = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;

      const event = JSON.parse(line.slice(6));

      switch (event.type) {
        case 'chunk':
          // Append to UI in real-time
          appendToMessageUI(event.data);
          fullResponse += event.data;
          break;

        case 'title_complete':
          // Update conversation title
          updateConversationTitle(event.data.title);
          break;

        case 'complete':
          // Show metadata
          console.log('Usage:', event.data.usage);
          if (event.data.thinking) {
            showThinkingPanel(event.data.thinking);
          }
          break;

        case 'error':
          console.error('Error:', event.message);
          showErrorMessage(event.message);
          break;
      }
    }
  }

  return fullResponse;
}

// Usage
sendQuickMessage('conv-123', 'What is React?', 'openai/gpt-4o')
  .then(response => console.log('Done:', response))
  .catch(err => console.error('Error:', err));
```

### React Hook

```jsx
import { useState } from 'react';

function useQuickMode(conversationId) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentChunks, setCurrentChunks] = useState([]);
  const [error, setError] = useState(null);

  const sendMessage = async (message, model = null) => {
    setIsStreaming(true);
    setCurrentChunks([]);
    setError(null);

    try {
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
          if (!line.startsWith('data: ')) continue;

          const event = JSON.parse(line.slice(6));

          if (event.type === 'chunk') {
            setCurrentChunks(prev => [...prev, event.data]);
          } else if (event.type === 'error') {
            setError(event.message);
          }
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStreaming(false);
    }
  };

  return {
    isStreaming,
    currentChunks,
    error,
    sendMessage
  };
}

// Usage in component
function QuickChat({ conversationId }) {
  const { isStreaming, currentChunks, error, sendMessage } = useQuickMode(conversationId);

  return (
    <div>
      {currentChunks.join('')}
      {isStreaming && <LoadingSpinner />}
      {error && <ErrorMessage error={error} />}
      <button onClick={() => sendMessage('Hello!')}>Send</button>
    </div>
  );
}
```

### cURL

```bash
# Send a quick message
curl -N -X POST http://localhost:8001/api/conversations/abc123/quick-message \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What is the meaning of life?",
    "model": "anthropic/claude-sonnet-4"
  }'

# Get available models
curl http://localhost:8001/api/chat/models | jq '.models[] | {id, name, input_cost, output_cost}'

# Create conversation, then send quick message
CONV_ID=$(curl -s -X POST http://localhost:8001/api/conversations | jq -r '.id')
echo "Conversation ID: $CONV_ID"

curl -N -X POST http://localhost:8001/api/conversations/$CONV_ID/quick-message \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello!"}'
```

---

## Performance Characteristics

### Response Times

| Model Type | Typical Latency | Notes |
|------------|-----------------|-------|
| Fast models (Gemini Flash) | 0.5-2s | First token ~500ms |
| Standard models (GPT-4o) | 1-3s | First token ~1s |
| Reasoning models (O3, R1) | 5-15s | Extended thinking time |

### Throughput

- **Concurrent requests**: Handles multiple streams simultaneously
- **Token streaming rate**: ~100-200 tokens/second
- **Memory usage**: ~10-50MB per active stream

### Cost Comparison

| Scenario | Quick Mode | Council Mode | Savings |
|----------|-----------|--------------|---------|
| Simple query | $0.001 | $0.008 | 87% |
| Medium query | $0.005 | $0.025 | 80% |
| Complex query | $0.015 | $0.060 | 75% |

---

## Best Practices

1. **Model Selection**
   - Use fast models (Gemini Flash, GPT-4o-mini) for simple queries
   - Use reasoning models (O3, R1) for math/logic problems
   - Use flagship models (GPT-4o, Claude Sonnet 4) for complex tasks

2. **Error Handling**
   - Always handle stream errors gracefully
   - Implement retry logic for transient failures
   - Fall back to council mode for critical queries

3. **Performance**
   - Close streams when user navigates away
   - Cancel pending requests on new user input
   - Cache model list to reduce API calls

4. **User Experience**
   - Show loading indicator while streaming
   - Display chunks incrementally for real-time feel
   - Provide model selector for power users

---

## Changelog

### v1.0.0 (2025-12-26)
- Initial implementation of Quick Mode
- Support for real-time streaming via SSE
- Integration with conversation system
- Reasoning model support
- Token usage tracking
