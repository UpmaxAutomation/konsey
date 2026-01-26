# LLM Council - True 10/10 Roadmap

> Based on comprehensive audit dated 2026-01-23
> Starting point: 6/10 → Target: 10/10

## 🚀 CORE PRINCIPLES: FAST + FUNCTIONAL

**Speed is non-negotiable. Every phase must:**
- Optimize for perceived performance
- Minimize API calls (batch, parallelize)
- Use optimistic UI updates
- Lazy load everything possible
- Cache aggressively
- No blocking operations on main thread

---

## Phase 1: Critical Security Fixes 🔴
**Priority**: IMMEDIATE | **Impact**: Security | **Effort**: 2 hours

### 1.1 Remove External Telemetry
**Files**: `frontend/src/App.jsx`
- [ ] Delete all `#region agent log` blocks (lines 68-70, 81-83, ~179, ~197)
- [ ] Search entire frontend for `127.0.0.1:7242` and remove
- [ ] Verify no data leaking to external services

### 1.2 Remove Hardcoded Debug Paths
**Files**: `backend/openrouter.py`, `backend/council.py`, `backend/middleware.py`, `backend/auth.py`
- [ ] Remove all `/Users/sezars/llm-council/.cursor/debug.log` references
- [ ] Replace with proper Python logging module
- [ ] Create `backend/logging_config.py` with structured logging
- [ ] Configure log level via environment variable

### 1.3 Stop Logging API Keys
**Files**: `backend/openrouter.py:201`
- [ ] Remove `key_prefix:openrouter_key[:10]` logging
- [ ] Audit all files for key logging patterns
- [ ] Add redaction utility for sensitive data

**Verification**:
```bash
grep -r "127.0.0.1:7242" frontend/
grep -r "/Users/" backend/
grep -r "api_key\|apikey\|API_KEY" backend/ | grep -v ".pyc"
```

---

## Phase 2: Backend Exception Handling 🟡
**Priority**: HIGH | **Impact**: Reliability | **Effort**: 3 hours

### 2.1 Create Custom Exceptions
**File**: `backend/exceptions.py` (new)
- [ ] Create `CouncilError` base exception
- [ ] Create `ModelQueryError(model, reason)`
- [ ] Create `RateLimitError(retry_after)`
- [ ] Create `ValidationError(field, message)`
- [ ] Create `StorageError(operation, details)`

### 2.2 Replace None Returns with Exceptions
**File**: `backend/openrouter.py`
- [ ] Line 254: Raise `ConfigurationError` instead of return None
- [ ] Lines 376-377: Raise `ModelQueryError` instead of return None
- [ ] Add context to all exceptions (model name, attempt count)

### 2.3 Add Global Exception Handler
**File**: `backend/main.py`
- [ ] Add `@app.exception_handler(CouncilError)`
- [ ] Return proper HTTP status codes (400, 429, 500, 503)
- [ ] Include error code and user-friendly message
- [ ] Log full exception with traceback

### 2.4 Add Input Validation
**Files**: `backend/voting.py`, `backend/council.py`
- [ ] Add bounds checking to voting option index (voting.py:114)
- [ ] Add max length validation on user inputs
- [ ] Validate option count (2-26) before processing

**Verification**:
```bash
grep -r "return None" backend/ | grep -v test | grep -v ".pyc"
# Should return 0 results in core modules
```

---

## Phase 3: Frontend State Refactor 🟡
**Priority**: HIGH | **Impact**: Maintainability | **Effort**: 4 hours

### 3.1 Refactor Sidebar State
**File**: `frontend/src/components/Sidebar.jsx`
- [ ] Create `sidebarReducer` with action types
- [ ] Replace 26+ useState with single useReducer
- [ ] Group related state: folders, tags, UI, drag-drop
- [ ] Extract state logic to `useSidebarState` hook

### 3.2 Fix useEffect Dependencies
**File**: `frontend/src/components/Sidebar.jsx:170-178`
- [ ] Add `loadFolders` to dependency array
- [ ] Wrap functions in useCallback where needed
- [ ] Fix all missing dependency warnings

### 3.3 Parallelize Stage1 API Calls
**File**: `frontend/src/components/Stage1.jsx:32-60`
- [ ] Replace serial `for await` with `Promise.all()`
- [ ] Add loading state per model
- [ ] Handle partial failures gracefully

### 3.4 Replace alert() with Toast
**Files**: `Stage1.jsx`, `Sidebar.jsx`, `CompareView.jsx`
- [ ] Replace all `alert()` calls with `toast.error()` or `toast.success()`
- [ ] Ensure toast import exists in each file

**Verification**:
```bash
grep -r "useState" frontend/src/components/Sidebar.jsx | wc -l
# Should be < 5 after refactor
grep -r "alert(" frontend/src/
# Should return 0 results
```

---

## Phase 4: Error Boundaries & Resilience 🟡
**Priority**: HIGH | **Impact**: UX | **Effort**: 2 hours

### 4.1 Create Error Boundary Component
**File**: `frontend/src/components/ErrorBoundary.jsx` (new)
- [ ] Implement React Error Boundary
- [ ] Show user-friendly error message
- [ ] Add "Try Again" button
- [ ] Log error to console (or future monitoring)

### 4.2 Wrap Route Components
**File**: `frontend/src/App.jsx`
- [ ] Wrap `<MainApp>` with ErrorBoundary
- [ ] Wrap each major route with ErrorBoundary
- [ ] Add fallback UI for each boundary

### 4.3 Add Request Timeouts
**File**: `frontend/src/components/Stage1.jsx:40-42`
- [ ] Add AbortController with 30s timeout
- [ ] Show timeout error to user
- [ ] Allow retry on timeout

### 4.4 Add Retry Logic to Critical Fetches
**Files**: Various API calls
- [ ] Ensure retry utility from previous work is used
- [ ] Add retry to council query calls
- [ ] Add retry to rating submission

---

## Phase 5: Accessibility (a11y) 🟢
**Priority**: MEDIUM | **Impact**: Inclusivity | **Effort**: 3 hours

### 5.1 Fix Star Rating Accessibility
**File**: `frontend/src/components/Stage1.jsx:182+`
- [ ] Use semantic radio group for stars
- [ ] Add proper ARIA labels
- [ ] Support keyboard navigation (arrow keys)
- [ ] Add visible focus indicators

### 5.2 Fix Tag Navigation
**File**: `frontend/src/components/Sidebar.jsx:368-375`
- [ ] Add `role="button"` and `tabIndex={0}`
- [ ] Support Enter/Space to activate
- [ ] Add ARIA labels for tags

### 5.3 Add Form Labels
**Files**: Various forms
- [ ] Associate all inputs with labels
- [ ] Add `aria-describedby` for error messages
- [ ] Add `aria-required` for required fields

### 5.4 Add Skip Navigation
**File**: `frontend/src/App.jsx`
- [ ] Add "Skip to main content" link
- [ ] Ensure proper heading hierarchy

**Verification**:
```bash
# Run axe accessibility audit
npx axe-cli http://localhost:5173
```

---

## Phase 6: Testing Hardening 🟢
**Priority**: MEDIUM | **Impact**: Reliability | **Effort**: 3 hours

### 6.1 Increase Coverage Threshold
**File**: `pyproject.toml`
- [ ] Increase pytest-cov threshold from 50% to 80%
- [ ] Add coverage for auth, middleware, storage modules

### 6.2 Fix CI continue-on-error
**File**: `.github/workflows/*.yml`
- [ ] Remove `continue-on-error: true` from lint checks
- [ ] Remove `continue-on-error: true` from security scans
- [ ] Make E2E test failures block deployment

### 6.3 Add Missing Tests
**Files**: `tests/`
- [ ] Add tests for exception handling paths
- [ ] Add tests for input validation
- [ ] Add tests for edge cases in voting

### 6.4 Add Type Checking to CI
**File**: `.github/workflows/test.yml`
- [ ] Add mypy step
- [ ] Configure stricter mypy settings in pyproject.toml

---

## Phase 7: Performance Optimization 🟢
**Priority**: MEDIUM | **Impact**: Speed | **Effort**: 2 hours

### 7.1 Add Memoization
**Files**: `Stage1.jsx`, `Sidebar.jsx`, `CompareView.jsx`
- [ ] Add `useMemo` for expensive computations
- [ ] Add `React.memo` for list items
- [ ] Add `useCallback` for handlers passed to children

### 7.2 Lazy Load Heavy Components
**File**: `frontend/src/App.jsx`
- [ ] Lazy load `AnalyticsDashboard`
- [ ] Lazy load `TeamManager`
- [ ] Lazy load `APIKeysManager`
- [ ] Add Suspense with loading fallback

### 7.3 Fix Memory Leaks
**File**: `frontend/src/components/Sidebar.jsx:139-141`
- [ ] Use refs for event listener flags
- [ ] Reduce listener re-registration frequency

---

## Phase 8: TypeScript Migration (Progressive) 🟢
**Priority**: LOW | **Impact**: Maintainability | **Effort**: 4 hours

### 8.1 Setup TypeScript
**Files**: `frontend/tsconfig.json`, `frontend/vite.config.ts`
- [ ] Add TypeScript dependencies
- [ ] Configure tsconfig for gradual adoption
- [ ] Allow JS files initially

### 8.2 Convert Core Types
**File**: `frontend/src/types/` (new)
- [ ] Define `Conversation` type
- [ ] Define `CouncilResponse` type
- [ ] Define `VotingResult` type
- [ ] Define `Model` and `Preset` types

### 8.3 Convert New Files to TypeScript
- [ ] New components should be `.tsx`
- [ ] New utilities should be `.ts`
- [ ] Gradually convert existing files

---

## Phase 9: Structured Logging 🟢
**Priority**: LOW | **Impact**: Observability | **Effort**: 2 hours

### 9.1 Create Logging Module
**File**: `backend/logging_config.py`
- [ ] Configure structlog or python-json-logger
- [ ] Add request ID to all logs
- [ ] Add user ID (if authenticated)
- [ ] Configure log level from env

### 9.2 Replace Debug Logging
**Files**: All backend files with debug logging
- [ ] Replace print statements with logger
- [ ] Use appropriate log levels (DEBUG, INFO, ERROR)
- [ ] Add context to log messages

### 9.3 Add Request/Response Logging
**File**: `backend/middleware.py`
- [ ] Log request method, path, duration
- [ ] Log response status code
- [ ] Redact sensitive headers

---

## Phase 10: Documentation & Cleanup 🟢
**Priority**: LOW | **Impact**: Maintainability | **Effort**: 2 hours

### 10.1 Organize Documentation
- [ ] Create `/docs/` directory
- [ ] Move troubleshooting notes out of root
- [ ] Update README with current architecture

### 10.2 Clean Up Loose Files
- [ ] Move `test_*.py` from backend root to `tests/`
- [ ] Remove duplicate CLAUDE.md/AGENTS.md/GEMINI.md
- [ ] Delete .env.bak files from repo history

### 10.3 Update API Documentation
- [ ] Ensure all endpoints have OpenAPI descriptions
- [ ] Add request/response examples
- [ ] Document error codes

---

## Phase 11: Claude-Like UX/UI Redesign 🟡
**Priority**: HIGH (User Requested) | **Impact**: Major UX | **Effort**: 8-12 hours

### 11.1 New Sidebar Structure (Claude-style)
```
┌─────────────────────────────┐
│ ✦ LLM Council          [☰] │
├─────────────────────────────┤
│ [+ New Council]             │
├─────────────────────────────┤
│ 🔍 Search              ⌘K  │
│ 💬 Councils                 │
│ 📁 Projects                 │
│ ⚙️ Presets                  │
├─────────────────────────────┤
│ ⭐ STARRED              ▼  │
│   ★ Important Query         │
├─────────────────────────────┤
│ 🕐 RECENTS              ▼  │
│   Code review...            │
│   API design...             │
├─────────────────────────────┤
│ [SA] Sezgin Arslan          │
│      Pro · $4.20 used       │
└─────────────────────────────┘
```

### 11.2 Projects Feature
- [ ] Projects list view (grid of cards)
- [ ] Project detail view with:
  - Memory (project context)
  - Instructions (custom prompts)
  - Files (attached documents)
  - Conversation list
- [ ] New project creation
- [ ] Project search & sort

### 11.3 Starred & Recents
- [ ] Star conversations and projects
- [ ] Starred section (collapsible)
- [ ] Recents section (last 15-20)
- [ ] Persist starred state

### 11.4 Global Search (⌘K)
- [ ] Search modal
- [ ] Search conversations + projects
- [ ] Recent searches
- [ ] Keyboard shortcut

### 11.5 User Profile Footer
- [ ] Avatar + name
- [ ] Plan/tier indicator
- [ ] Budget usage bar
- [ ] Settings dropdown

### 11.6 Performance (CRITICAL)
- [ ] Virtual scrolling for long lists
- [ ] Skeleton loading states
- [ ] Optimistic UI updates
- [ ] Debounced search
- [ ] Memoized list items

**See**: `.planning/PLAN-phase11-ux.md` for full details

---

## Progress Tracking

| Phase | Status | Priority | Est. Hours |
|-------|--------|----------|------------|
| 1. Critical Security | ⏳ Pending | 🔴 IMMEDIATE | 2h |
| 2. Exception Handling | ⏳ Pending | 🟡 HIGH | 3h |
| 3. State Refactor | ⏳ Pending | 🟡 HIGH | 4h |
| 4. Error Boundaries | ⏳ Pending | 🟡 HIGH | 2h |
| 5. Accessibility | ⏳ Pending | 🟢 MEDIUM | 3h |
| 6. Testing | ⏳ Pending | 🟢 MEDIUM | 3h |
| 7. Performance | ⏳ Pending | 🟢 MEDIUM | 2h |
| 8. TypeScript | ⏳ Pending | 🟢 LOW | 4h |
| 9. Logging | ⏳ Pending | 🟢 LOW | 2h |
| 10. Cleanup | ⏳ Pending | 🟢 LOW | 2h |
| **11. Claude UX/UI** | ⏳ Pending | 🟡 HIGH | 10h |

**Total Estimated: ~37 hours**

---

## Score Progression

| After Phase | Expected Score | Reason |
|-------------|----------------|--------|
| Phase 1 | 7/10 | Security fixed |
| Phase 2 | 7.5/10 | Reliable error handling |
| Phase 3 | 8/10 | Maintainable frontend |
| Phase 4 | 8.5/10 | Resilient UX |
| Phase 5-7 | 9/10 | Accessible + tested + fast |
| Phase 8-10 | 9.5/10 | Production polish |
| **Phase 11** | **10/10** | **Claude-like UX = Premium feel** |

---

## Definition of Done (Per Phase)

- [ ] All tasks checked off
- [ ] `npm run lint` passes
- [ ] `npm run build` succeeds
- [ ] `pytest` passes with coverage threshold
- [ ] No console errors in browser
- [ ] Committed with conventional commit message
- [ ] Manual smoke test completed
