# 🔍 Production Login Debug

## Issue
- **CORS preflight (OPTIONS)**: ✅ Working (200 OK)
- **Login POST request**: ❌ Returning HTTP 500 (Internal Server Error)

## Possible Causes

1. **Missing SECRET_KEY** - JWT token generation requires SECRET_KEY
2. **Database connection issue** - Can't query users table
3. **Missing dependencies** - Some import or module not available
4. **Environment variable issue** - Required env vars not set in Railway

## Debug Steps Added

Added logging to login endpoint to capture:
- Entry point (email received)
- Database query errors
- Token generation errors
- Token storage errors

## Check Railway Logs

Go to **Railway Dashboard** → Your Service → **Logs** tab

Look for:
- Error messages when login is attempted
- Stack traces
- Missing environment variable warnings
- Database connection errors

## Quick Checks

### 1. Verify SECRET_KEY is set in Railway
```bash
# Should be set in Railway environment variables
SECRET_KEY=your-secret-key-here
```

### 2. Test login endpoint directly
```bash
curl -X POST https://konsey-production-b999.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

### 3. Check Railway environment variables
Required variables:
- `SECRET_KEY` - For JWT tokens
- `DATABASE_URL` - Database connection
- `CORS_ORIGINS` - CORS configuration

## Next Steps

After checking Railway logs, share:
1. The error message from logs
2. Any stack trace
3. Which environment variables are set

This will help identify the exact cause of the 500 error.
