# Production URLs - SINGLE SOURCE OF TRUTH

## Live URLs (DO NOT CHANGE)

| Service | URL |
|---------|-----|
| **Frontend** | https://konsey-eight.vercel.app |
| **Backend** | https://konsey-production.up.railway.app |

## Configuration Files

- Frontend API URL: `frontend/.env.production` → `VITE_API_URL=https://konsey-production.up.railway.app`
- Backend CORS: `.env` → `CORS_ORIGINS` includes `https://konsey-eight.vercel.app`

## Vercel Project

- **Project Name**: konsey-eight
- **Scope**: sezginbozdag
- **Only deploy to this project**

## Railway Project

- **Service**: konsey-production
- **URL**: https://konsey-production.up.railway.app

## WRONG URLs (DO NOT USE)

These URLs are invalid or old - never use them:
- ~~konsey-production-b999.up.railway.app~~ (returns 404)
- ~~llm-council-backend-production.up.railway.app~~ (doesn't exist)
- ~~llm-council-neon.vercel.app~~ (wrong project)
- ~~llm-council-frontend.vercel.app~~ (wrong project)

---
*Last updated: 2026-01-25*
