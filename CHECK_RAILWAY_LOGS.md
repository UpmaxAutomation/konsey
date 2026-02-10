# 🔍 Check Railway Logs for Login Error

## The Problem

Backend is returning **HTTP 500** on login POST request (not CORS - CORS preflight works).

## What to Check

### 1. Railway Logs

Go to **Railway Dashboard** → Your Service → **Logs** tab

Look for error messages when you try to login. Common issues:

#### Missing SECRET_KEY
```
FATAL: SECRET_KEY environment variable is required in production.
```

**Fix:** Add `SECRET_KEY` to Railway environment variables

#### Database Error
```
Database connection error
sqlalchemy.exc.OperationalError
```

**Fix:** Check `DATABASE_URL` is set correctly

#### Import Error
```
ModuleNotFoundError: No module named 'X'
```

**Fix:** Check `requirements.txt` includes all dependencies

### 2. Environment Variables in Railway

**Required:**
- `SECRET_KEY` - For JWT tokens (generate with: `python -c "import secrets; print(secrets.token_urlsafe(64))"`)
- `DATABASE_URL` - Your Supabase connection string
- `CORS_ORIGINS` - Your Vercel URLs
- `ENVIRONMENT` - Should be `production` (optional, but recommended)

### 3. Test Endpoint Directly

```bash
curl -X POST https://konsey-production-b999.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

**Expected:**
- If user doesn't exist: `401 Unauthorized` with "Invalid email or password"
- If credentials wrong: `401 Unauthorized` with "Invalid email or password"  
- If server error: `500 Internal Server Error` with error details

## Share the Error

After checking Railway logs, share:
1. **The exact error message** from logs
2. **Stack trace** (if any)
3. **Which environment variables are set** in Railway

This will help identify the exact cause of the 500 error.
