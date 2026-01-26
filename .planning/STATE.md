# Project State - LLM Council TRUE 10/10 Refactor

## Last Updated
2026-01-23 (Full independent audit completed)

## Current Phase
- Phase: 1 (Critical Security Fixes)
- Name: Remove telemetry, hardcoded paths, key logging
- Status: READY TO EXECUTE
- Audit Date: 2026-01-23
- Actual Score: **6/10** (not 10/10 as previously claimed)

## Audit Summary (2026-01-23)
Previous phases claimed 10/10 but independent audit found critical issues:

### 🔴 CRITICAL (Security)
1. External telemetry in `App.jsx:69-83` leaking data to unknown service
2. Hardcoded `/Users/sezars/...` debug paths in backend
3. API keys partially logged in `openrouter.py:201`

### 🟡 HIGH (Code Quality)
4. Silent `return None` in `openrouter.py` instead of exceptions
5. 26+ `useState` hooks in `Sidebar.jsx` - unmaintainable
6. N+1 API calls in `Stage1.jsx` - serial fetches
7. No Error Boundaries - app crashes on errors

### 🟢 MEDIUM (Polish)
8. Missing accessibility (star ratings, tags)
9. 50% test coverage (should be 80%)
10. No TypeScript

## Score Breakdown (Audit 2026-01-23)
| Category | Score |
|----------|-------|
| Concept/Innovation | 9/10 |
| Architecture | 7/10 |
| Backend Code | 5/10 |
| Frontend Code | 5/10 |
| Security | 3/10 |
| Testing | 6/10 |
| Deployment | 8/10 |
| Documentation | 6/10 |
| **Overall** | **6/10** |

## New Roadmap (v2) - 10 Phases to TRUE 10/10

| Phase | Status | Priority | Est. Hours |
|-------|--------|----------|------------|
| 1. Critical Security | ⏳ Ready | 🔴 IMMEDIATE | 2h |
| 2. Exception Handling | ⏳ Pending | 🟡 HIGH | 3h |
| 3. State Refactor | ⏳ Pending | 🟡 HIGH | 4h |
| 4. Error Boundaries | ⏳ Pending | 🟡 HIGH | 2h |
| 5. Accessibility | ⏳ Pending | 🟢 MEDIUM | 3h |
| 6. Testing | ⏳ Pending | 🟢 MEDIUM | 3h |
| 7. Performance | ⏳ Pending | 🟢 MEDIUM | 2h |
| 8. TypeScript | ⏳ Pending | 🟢 LOW | 4h |
| 9. Logging | ⏳ Pending | 🟢 LOW | 2h |
| 10. Cleanup | ⏳ Pending | 🟢 LOW | 2h |

**Total Estimated: ~27 hours**

## Hot Files (Need Immediate Attention)
- `frontend/src/App.jsx` - Remove telemetry (lines 68-83)
- `backend/openrouter.py` - Remove hardcoded paths, fix None returns
- `backend/council.py` - Remove debug logging
- `frontend/src/components/Sidebar.jsx` - State refactor (26+ useState)
- `frontend/src/components/Stage1.jsx` - Fix N+1 API calls

## Key Decisions
- Keep Supabase as database (already configured)
- Keep GitHub as repo (CI/CD exists)
- Progressive TypeScript adoption (not full rewrite)
- Priority: Security → Reliability → UX → Polish

## GSD Files Created
- `.planning/PROJECT-v2.md` - New project vision
- `.planning/ROADMAP-v2.md` - New 10-phase roadmap
- `.planning/PLAN-phase1.md` - Detailed Phase 1 tasks

## Blockers
- None

## Environment
- Database: Supabase (PostgreSQL)
- Backend: FastAPI (port 8001)
- Frontend: React 19 + Vite (port 5173)
- Deployment: Vercel (frontend), Railway (backend)

## Context for Next Session
1. Full audit completed 2026-01-23 - actual score is 6/10
2. Created new ROADMAP-v2.md with honest assessment
3. Phase 1 PLAN ready - start with removing telemetry from App.jsx
4. Run: `grep -r "127.0.0.1:7242" frontend/` to find telemetry
5. Then fix backend hardcoded paths
6. ~27 hours total to reach true 10/10
