# Reasoning Models Implementation Summary

## Overview
Added special support for reasoning models (O1, O3, R1, QwQ) that display their internal thinking process to users.

## Changes Made

### 1. Backend Configuration (`backend/config.py`)

**Added:**
- `REASONING_MODELS` list containing all reasoning model identifiers:
  - OpenAI: o1, o1-mini, o1-pro, o3, o3-mini, o3-pro, o3-deep-research, o4-mini, o4-mini-deep-research
  - DeepSeek: deepseek-r1, deepseek-r1-0528
  - Qwen: qwq-32b
  - Anthropic: claude-3.7-sonnet:thinking

- `REASONING_MODEL_CONFIG` dictionary:
  ```python
  {
      "extended_timeout": 120,  # 2 minutes for reasoning
      "show_thinking": True,
      "max_thinking_tokens": 10000
  }
  ```

- `is_reasoning_model(model: str) -> bool` helper function to check if a model is a reasoning model

### 2. OpenRouter API Client (`backend/openrouter.py`)

**Modified `query_model()` function:**
- Auto-detects reasoning models using `is_reasoning_model()`
- Applies extended timeout (120 seconds) for reasoning models automatically
- Extracts thinking tokens from response in multiple possible fields:
  - `reasoning_content` (DeepSeek R1 format)
  - `thinking` (OpenAI O-series format)
  - Fallback: Token count indicator if reasoning performed but content not exposed
- Returns response with optional `thinking` field alongside `content`

**Updated imports:**
- Added `is_reasoning_model` and `REASONING_MODEL_CONFIG` from config

### 3. Council Orchestration (`backend/council.py`)

**Modified `stage1_collect_responses()`:**
- Now captures and passes through `thinking` field from OpenRouter responses
- Stage 1 results include:
  ```python
  {
      "model": "openai/o3",
      "response": "Final answer text",
      "thinking": "Internal reasoning process..."  # Optional, only for reasoning models
  }
  ```

### 4. Frontend Display (`frontend/src/components/Stage1.jsx`)

**Added features:**
- Brain emoji (🧠) indicator on tabs for models with thinking tokens
- "Show Reasoning" / "Hide Reasoning" toggle button
- Collapsible thinking block with distinct visual styling
- Thinking section appears above final response when expanded
- State management for per-tab thinking visibility

**Component structure:**
```jsx
- Tab buttons with thinking indicator
- Toggle button (when thinking available)
- Thinking block (collapsible)
  - Header: "REASONING PROCESS:"
  - Content: ReactMarkdown rendering
- Final response (always visible)
```

### 5. Styling (`frontend/src/components/Stage1.css`)

**Added styles:**
- `.thinking-indicator` - Brain emoji styling in tabs
- `.thinking-controls` - Container for toggle button
- `.toggle-thinking-btn` - Toggle button with hover states
- `.thinking-block` - Gray background container with left border accent
- `.thinking-header` - Uppercase label "REASONING PROCESS:"
- `.thinking-content` - Monospace font, scrollable (max 400px), pre-wrap formatting

**Design choices:**
- Light gray background (#f8f9fa) to distinguish from main response
- Monospace font for technical reasoning content
- Max height with scroll for long reasoning chains
- Left border accent (#6c757d) for visual hierarchy
- Responsive hover states on toggle button

## Usage

### For Users
1. Select a reasoning model in council configuration (e.g., "openai/o3", "deepseek/deepseek-r1", "qwen/qwq-32b")
2. Ask a question requiring complex reasoning
3. Look for brain emoji (🧠) on response tabs
4. Click "Show Reasoning" to view internal thinking process
5. Compare thinking process across different reasoning models

### For Developers
```python
# Check if a model is a reasoning model
from backend.config import is_reasoning_model

if is_reasoning_model("openai/o3"):
    # Extended timeout will be applied automatically
    # Thinking tokens will be extracted if available
```

## API Response Format

### Before (Standard Models)
```json
{
  "content": "Final answer",
  "usage": {...}
}
```

### After (Reasoning Models)
```json
{
  "content": "Final answer",
  "thinking": "Step 1: Analyze...\nStep 2: Consider...",
  "usage": {...}
}
```

## Technical Notes

### Timeout Handling
- Standard models: 120s default timeout
- Reasoning models: 120s extended timeout (configured, can be adjusted)
- Timeout is applied automatically based on model identifier

### Thinking Extraction
The implementation checks multiple possible fields where thinking tokens might appear:
1. `message.reasoning_content` (DeepSeek R1)
2. `message.thinking` (OpenAI O-series)
3. `usage.reasoning_tokens` (fallback - shows count only)

This ensures compatibility with different API response formats from various providers.

### Frontend State Management
- Each tab has independent thinking visibility state
- State persists when switching between tabs
- Brain emoji always visible when thinking available
- Toggle button only appears for current tab with thinking

## Testing

To test the implementation:

1. **Backend Test:**
```bash
cd /Users/sezars/llm-council
python -m backend.main
```

2. **Frontend Test:**
```bash
cd /Users/sezars/llm-council/frontend
npm run dev
```

3. **Test with Reasoning Council Preset:**
- Open Settings in UI
- Select "Reasoning Council" preset
- Ask a complex reasoning question
- Verify thinking tokens display correctly

## Future Enhancements

Potential improvements:
1. Add reasoning token count display in UI
2. Export thinking process to markdown
3. Compare thinking approaches across models
4. Highlight key reasoning steps
5. Allow hiding/showing thinking by default in settings
6. Add syntax highlighting for code in thinking
7. Track thinking token costs separately

## Files Modified

1. `/Users/sezars/llm-council/backend/config.py` - Added reasoning model configuration
2. `/Users/sezars/llm-council/backend/openrouter.py` - Extended timeout and thinking extraction
3. `/Users/sezars/llm-council/backend/council.py` - Pass through thinking tokens
4. `/Users/sezars/llm-council/frontend/src/components/Stage1.jsx` - Display thinking with toggle
5. `/Users/sezars/llm-council/frontend/src/components/Stage1.css` - Thinking block styles

## Backward Compatibility

- All changes are backward compatible
- Standard models continue to work without modification
- `thinking` field is optional and only added when available
- UI gracefully handles responses without thinking tokens
- No database schema changes required
