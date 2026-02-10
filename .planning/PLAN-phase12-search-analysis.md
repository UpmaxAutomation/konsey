# Phase 12: Search & Analysis Improvements

## Objective
Improve search functionality visibility, add image analysis with data visualization, and fix existing search reliability issues.

## Scope
- **3 Sub-phases**: UI Visibility, Image Analysis, Bug Fixes
- **Estimated Effort**: ~8 hours total
- **Priority**: Medium (UX improvement)

---

## Sub-Phase 12.1: Improve Search UI Visibility

### Problem
- Search options hidden behind gear/options icon
- No visual indication when search is active
- Users don't discover the feature
- No feedback during search operations

### Tasks

#### Task 12.1.1: Add Search Badge to Chat Input
**File**: `frontend/src/components/ChatInterface.jsx`

Add a visible badge/indicator next to the send button showing current search mode:
```jsx
// Near send button area
{(features.web_search || features.deep_search) && (
  <span className="search-badge">
    {features.deep_search ? '🔍 Deep' : '🌐 Online'}
  </span>
)}
```

#### Task 12.1.2: Add Search Toggle to Main UI
**File**: `frontend/src/components/ChatInterface.jsx`

Add prominent search toggle buttons in the chat header or input area (not hidden in options):
- Three-state toggle: Off / Online / Deep
- Clear visual distinction between states
- Tooltip explaining each mode

#### Task 12.1.3: Add Search Loading Indicator
**File**: `frontend/src/components/ChatInterface.jsx`

Show animated indicator when web search is in progress:
```jsx
{isSearching && (
  <div className="search-loading">
    <span className="spinner" />
    Searching the web...
  </div>
)}
```

#### Task 12.1.4: Display Search Results Summary
**File**: `frontend/src/components/Stage1.jsx` or new `SearchResults.jsx`

When web search is used, show collapsible panel with:
- Number of sources found
- Source links with titles
- Brief snippet from each source
- "Powered by Perplexity" attribution

#### Task 12.1.5: Add Search Keyboard Shortcut
**File**: `frontend/src/components/ChatInterface.jsx`

Add `Ctrl+Shift+S` keyboard shortcut to toggle search mode:
```javascript
useEffect(() => {
  const handleKeyboard = (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'S') {
      cycleSearchMode(); // Off -> Online -> Deep -> Off
    }
  };
  window.addEventListener('keydown', handleKeyboard);
  return () => window.removeEventListener('keydown', handleKeyboard);
}, []);
```

### Verification 12.1
- [ ] Search badge visible when search enabled
- [ ] Toggle accessible without opening options
- [ ] Loading indicator shows during search
- [ ] Search results visible in response
- [ ] Keyboard shortcut works

---

## Sub-Phase 12.2: Image Analysis & Data Visualization

### Problem
- System can receive images but has limited analysis capabilities
- No data visualization for structured data
- Charts/graphs would help present numerical information

### Tasks

#### Task 12.2.1: Enhance Image Analysis Prompting
**File**: `backend/council.py`

When images are attached, add analysis prompt:
```python
if has_image_attachment:
    enhanced_prompt = """
    [Image Analysis Request]
    Please analyze the attached image(s) and describe:
    - What you see in the image
    - Any text, numbers, or data visible
    - Key patterns or notable elements

    """ + user_prompt
```

#### Task 12.2.2: Add Vision Model Detection
**File**: `backend/config.py`

Add function to detect vision-capable models:
```python
VISION_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4-turbo",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-opus",
    "google/gemini-2.0-flash",
    "google/gemini-pro-vision",
]

def is_vision_model(model: str) -> bool:
    return any(v in model for v in VISION_MODELS)
```

#### Task 12.2.3: Install Chart Library
**Command**: `cd frontend && npm install recharts`

Recharts is lightweight and React-friendly for data visualization.

#### Task 12.2.4: Create Chart Renderer Component
**File**: `frontend/src/components/ChartRenderer.jsx` (new)

Component that detects chart data in responses and renders:
```jsx
import { LineChart, BarChart, PieChart } from 'recharts';

// Detect JSON data blocks in markdown
// ```chart:bar { data: [...], xKey: "name", yKey: "value" }
// ```

function ChartRenderer({ type, data, config }) {
  switch(type) {
    case 'bar': return <BarChart data={data} {...config} />;
    case 'line': return <LineChart data={data} {...config} />;
    case 'pie': return <PieChart data={data} {...config} />;
  }
}
```

#### Task 12.2.5: Integrate Charts into Markdown
**File**: `frontend/src/components/SafeMarkdown.jsx` or CodeBlock

Extend markdown renderer to handle chart code blocks:
```jsx
// In CodeBlock component
if (language === 'chart:bar' || language === 'chart:line' || language === 'chart:pie') {
  const chartData = JSON.parse(children);
  return <ChartRenderer type={language.split(':')[1]} data={chartData} />;
}
```

#### Task 12.2.6: Add Image Analysis Button
**File**: `frontend/src/components/ChatInterface.jsx`

When image is attached, show "Analyze Image" quick action:
```jsx
{attachedFiles.some(f => f.type?.startsWith('image/')) && (
  <button onClick={() => setPromptPrefix("Analyze this image: ")}>
    🔍 Analyze Image
  </button>
)}
```

### Verification 12.2
- [ ] Vision models detected correctly
- [ ] Image analysis prompt injected
- [ ] Charts render from markdown
- [ ] Bar, line, pie charts work
- [ ] Analyze button appears for images

---

## Sub-Phase 12.3: Fix Existing Search Issues

### Problem
- DuckDuckGo HTML scraping is fragile
- No error handling for search failures
- No retry logic
- No graceful degradation

### Tasks

#### Task 12.3.1: Add Search Error Handling
**File**: `backend/tools.py`

Wrap search in try/catch with user-friendly errors:
```python
async def web_search(query: str, num_results: int = 5):
    try:
        results = await _duckduckgo_search(query, num_results)
        if not results:
            return {"error": False, "results": [], "message": "No results found"}
        return {"error": False, "results": results}
    except httpx.TimeoutException:
        return {"error": True, "message": "Search timed out. Please try again."}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"error": True, "message": "Search unavailable. Proceeding without web context."}
```

#### Task 12.3.2: Add Search Retry Logic
**File**: `backend/tools.py`

Implement exponential backoff for retries:
```python
async def _search_with_retry(search_fn, query, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await search_fn(query)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
```

#### Task 12.3.3: Improve DuckDuckGo Parsing
**File**: `backend/tools.py`

Make HTML parsing more robust:
```python
def _parse_ddg_results(html: str) -> List[dict]:
    # Use multiple parsing strategies
    # 1. Try structured data extraction
    # 2. Fallback to regex patterns
    # 3. Fallback to BeautifulSoup if available
    pass
```

#### Task 12.3.4: Add Perplexity Fallback
**File**: `backend/tools.py`

If DuckDuckGo fails and Perplexity key available, use it as fallback:
```python
async def web_search_with_fallback(query, use_deep=False):
    result = await web_search(query)
    if result.get("error") and has_perplexity_key():
        logger.info("DuckDuckGo failed, falling back to Perplexity")
        return await perplexity_search(query, deep=use_deep)
    return result
```

#### Task 12.3.5: Add Search Rate Limiting
**File**: `backend/tools.py`

Prevent abuse with rate limiting:
```python
from datetime import datetime, timedelta

_search_timestamps = []
SEARCH_RATE_LIMIT = 10  # per minute

def check_rate_limit():
    global _search_timestamps
    now = datetime.now()
    _search_timestamps = [t for t in _search_timestamps if now - t < timedelta(minutes=1)]
    if len(_search_timestamps) >= SEARCH_RATE_LIMIT:
        return False
    _search_timestamps.append(now)
    return True
```

#### Task 12.3.6: Display Search Errors in UI
**File**: `frontend/src/components/ChatInterface.jsx`

Show user-friendly error when search fails:
```jsx
{searchError && (
  <div className="search-error">
    ⚠️ {searchError}
    <button onClick={() => setSearchError(null)}>Dismiss</button>
  </div>
)}
```

### Verification 12.3
- [ ] Search timeout shows friendly message
- [ ] Retry logic works (test with mock failure)
- [ ] Perplexity fallback triggers when DDG fails
- [ ] Rate limiting prevents abuse
- [ ] Error messages display in UI

---

## Success Criteria

### Phase Complete When:
1. Search mode visible in main UI (not hidden in options)
2. Loading indicator during web search
3. Search results summary shown with sources
4. Image analysis works with vision models
5. Charts render from structured data in responses
6. Search errors handled gracefully with user feedback
7. Rate limiting prevents abuse

### Test Scenarios:
1. New user can discover and enable search without opening settings
2. User sees "Searching..." while web search runs
3. Response shows "Sources: [list of URLs]"
4. Attached image triggers vision model analysis
5. Response with chart data renders visual chart
6. Network failure shows friendly error, not crash

---

## Files to Modify

### Frontend
- `frontend/src/components/ChatInterface.jsx` - Search UI, toggles, loading
- `frontend/src/components/ChatInterface.css` - New styles
- `frontend/src/components/ChartRenderer.jsx` - New file
- `frontend/src/components/CodeBlock.jsx` - Chart integration
- `frontend/src/components/Stage1.jsx` - Search results display

### Backend
- `backend/tools.py` - Error handling, retry, rate limiting
- `backend/config.py` - Vision model detection
- `backend/council.py` - Image analysis prompting

---

## Execution Order

1. **12.3 First** (Bug fixes) - Fix reliability before adding features
2. **12.1 Second** (UI visibility) - Make existing features discoverable
3. **12.2 Last** (New features) - Add image analysis and charts

---

## Dependencies

- `recharts` npm package for charts
- Vision-capable models in council for image analysis
- Perplexity API key for deep search fallback
