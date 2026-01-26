# LLM Council - True 10/10 Implementation Project

## Vision
Transform LLM Council from a **6/10 prototype** to a **10/10 production-grade** application by fixing critical security issues, code quality problems, and adding production hardening.

## Honest Current State (6/10)

### What Works Well ✅
- 3-stage council deliberation (innovative concept)
- 100+ models, 9 providers
- Voting, debate, agents
- Supabase database
- GitHub CI/CD
- Docker deployment ready
- Dark mode, cost estimation (from previous work)

### Critical Issues Found 🔴
1. **External telemetry** in `App.jsx:69-83` leaking data to unknown service
2. **Hardcoded debug paths** (`/Users/sezars/...`) in backend files
3. **Silent failures** - `query_model()` returns None instead of exceptions
4. **26+ useState hooks** in `Sidebar.jsx` - unmaintainable state
5. **N+1 API calls** in `Stage1.jsx` - serial fetches
6. **No Error Boundaries** - app crashes on component errors
7. **Missing accessibility** - star ratings, tag navigation
8. **API keys partially logged** - security risk
9. **No input validation** - length limits, bounds checking
10. **50% test coverage** - should be 80%+

## Success Criteria for 10/10

### Security (Must Have)
- [ ] Zero external telemetry calls
- [ ] No hardcoded system paths
- [ ] No API key logging
- [ ] Input validation on all endpoints
- [ ] Rate limiting enforced

### Code Quality (Must Have)
- [ ] Proper exception handling (no silent None returns)
- [ ] Sidebar state refactored to useReducer
- [ ] Error Boundaries on all route components
- [ ] Parallel API calls where possible
- [ ] TypeScript on new code (progressive adoption)

### Testing (Must Have)
- [ ] 80%+ code coverage on core modules
- [ ] All CI checks pass (no continue-on-error)
- [ ] E2E tests for critical flows

### Accessibility (Should Have)
- [ ] WCAG 2.1 AA compliant
- [ ] Keyboard navigation working
- [ ] Screen reader compatible

### Performance (Should Have)
- [ ] Memoization on expensive components
- [ ] Lazy loading for heavy modules
- [ ] Bundle size optimized

## Tech Stack
- **Backend**: FastAPI, Python 3.10+, Supabase (PostgreSQL)
- **Frontend**: React 19, Vite, (adding TypeScript)
- **Testing**: pytest (80%+), Playwright
- **Deployment**: Vercel (frontend), Railway (backend)
- **Monitoring**: Structured logging (replacing debug logs)

## Constraints
- Database already on Supabase (no migration needed)
- Code on GitHub (CI/CD exists)
- Maintain backward API compatibility
- Progressive TypeScript adoption (not full rewrite)

## Definition of Done
Each phase is done when:
1. All tasks completed
2. Tests pass
3. No lint errors
4. Code reviewed (self-review checklist)
5. Committed with conventional commit message
