# Testing Reasoning Models - Quick Guide

## Quick Start

### 1. Start the Backend
```bash
cd /Users/sezars/llm-council
python -m backend.main
```

Backend will start on http://localhost:8001

### 2. Start the Frontend
```bash
cd /Users/sezars/llm-council/frontend
npm run dev
```

Frontend will start on http://localhost:5173

### 3. Configure Reasoning Council

**Option A: Use Preset (Recommended)**
1. Open http://localhost:5173
2. Click Settings icon
3. Select "Reasoning Council" from preset dropdown (if implemented)
4. Click Apply

**Option B: Manual Selection**
1. Open Settings
2. Select reasoning models individually:
   - openai/o3
   - deepseek/deepseek-r1
   - qwen/qwq-32b
   - openai/o4-mini
3. Save configuration

### 4. Test Questions

Try these to see reasoning in action:

**Mathematics:**
```
What is the sum of all prime numbers less than 100?
Show your reasoning step by step.
```

**Logic:**
```
If all bloops are razzles and all razzles are lazzles,
are all bloops definitely lazzles? Explain your reasoning.
```

**Complex Problem:**
```
A farmer has 17 sheep, all but 9 die. How many are left?
Think through this carefully.
```

**Coding Challenge:**
```
Write a function to find the longest palindromic substring.
Explain your approach and reasoning.
```

## What to Look For

### Visual Indicators
- **Brain emoji (🧠)** on tabs → Model has thinking tokens
- **"Show Reasoning" button** → Click to expand thinking process
- **Gray background box** → Thinking content displayed in monospace
- **Regular response below** → Final answer after thinking

### Expected Behavior

**Reasoning Models (O3, R1, QwQ):**
- Longer response time (up to 2 minutes)
- Brain emoji visible on tab
- Thinking block available
- Detailed step-by-step reasoning visible

**Standard Models (GPT-4o, Claude, Gemini):**
- Normal response time
- No brain emoji
- No thinking block
- Direct answer only

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend displays correctly
- [ ] Can select reasoning models in Settings
- [ ] Reasoning models show brain emoji on tabs
- [ ] "Show Reasoning" button appears when thinking available
- [ ] Clicking toggle shows/hides thinking block
- [ ] Thinking block has gray background and monospace font
- [ ] Thinking content is scrollable if long
- [ ] Final answer appears below thinking
- [ ] Can switch between tabs while keeping thinking state
- [ ] Standard models still work normally (no thinking)

## Debugging

### No Thinking Displayed
1. Check browser console for errors
2. Verify model is in `REASONING_MODELS` list in `backend/config.py`
3. Check API response in Network tab for `thinking` field
4. Verify `REASONING_MODEL_CONFIG.show_thinking = True`

### Timeout Errors
1. Check timeout is 120s for reasoning models (auto-applied)
2. Increase `REASONING_MODEL_CONFIG.extended_timeout` if needed
3. Monitor backend logs for timeout errors

### Missing Brain Emoji
1. Verify response has `thinking` field (check network tab)
2. Check `currentResponse.thinking` is not empty string
3. Verify emoji character renders in browser

## API Response Format

### Standard Model Response
```json
{
  "model": "openai/gpt-4o",
  "response": "The answer is 42.",
  "usage": {...}
}
```

### Reasoning Model Response
```json
{
  "model": "openai/o3",
  "response": "The answer is 42.",
  "thinking": "Step 1: Analyze the question...\nStep 2: Consider...",
  "usage": {...}
}
```

## Performance Expectations

| Model | Typical Response Time | Thinking Length |
|-------|----------------------|-----------------|
| O3 | 30-90 seconds | 1000-5000 tokens |
| O3 Pro | 60-120 seconds | 3000-10000 tokens |
| DeepSeek R1 | 20-60 seconds | 500-3000 tokens |
| QwQ 32B | 15-45 seconds | 300-2000 tokens |
| O4 Mini | 10-30 seconds | 200-1000 tokens |

Times vary based on query complexity.

## Common Issues

**Issue: Thinking shows "[Reasoning performed: N tokens]"**
- Cause: API reports reasoning_tokens count but doesn't expose content
- Solution: Normal behavior for some models/providers

**Issue: Thinking block overlaps response**
- Cause: CSS styling issue
- Solution: Check `margin-bottom: 16px` on `.thinking-block`

**Issue: Can't scroll long thinking**
- Cause: Missing overflow style
- Solution: Verify `max-height: 400px; overflow-y: auto` on `.thinking-content`

**Issue: Thinking persists when switching models**
- Cause: State management bug
- Solution: Check `showThinking` state uses `activeTab` as key

## Cost Considerations

Reasoning models are typically more expensive:
- O3: $2.00 input / $8.00 output per 1M tokens
- O3 Pro: $20.00 input / $80.00 output per 1M tokens
- DeepSeek R1: $0.55 input / $2.19 output per 1M tokens
- QwQ 32B: $0.20 input / $0.20 output per 1M tokens

Thinking tokens count toward total token usage.

## Next Steps

After verifying basic functionality:
1. Test with "Reasoning Council" preset (4 reasoning models)
2. Compare thinking approaches across different models
3. Try increasingly complex problems
4. Monitor token usage and costs
5. Provide feedback on UX improvements

## Support

If issues persist:
1. Check `REASONING_MODELS_IMPLEMENTATION.md` for full technical details
2. Review browser console and network tab
3. Check backend logs for API errors
4. Verify OpenRouter API key is valid
5. Test with non-reasoning models to isolate issue
