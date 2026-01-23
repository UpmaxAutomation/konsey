# 🔍 CORS Debug Steps

## Step 1: Check Railway CORS Configuration

**Go to Railway Dashboard:**
1. Your Service → **Variables** tab
2. Find `CORS_ORIGINS`
3. **What value is it set to?** (Copy and share it)

## Step 2: Test Debug Endpoint

After Railway redeploys (1-2 minutes), test:

```bash
curl https://konsey-production-b999.up.railway.app/api/debug/cors
```

This will show what CORS origins the server thinks it's configured with.

## Step 3: Test Actual Request

Try to login from the browser, then check:

1. **Browser Console (F12)** → Network tab
2. Find the failed `/api/auth/login` request
3. Click on it → Headers tab
4. Share:
   - **Request Headers** → `Origin` value
   - **Response Headers** → `Access-Control-Allow-Origin` (if present)
   - **Status Code**

## Step 4: Compare

Compare:
- What Railway `CORS_ORIGINS` is set to
- What the debug endpoint shows
- What origin the browser is sending
- What origin the server is allowing

## Common Issues

1. **Missing trailing slash**: `https://konsey-eight.vercel.app` vs `https://konsey-eight.vercel.app/`
2. **HTTP vs HTTPS**: `http://` vs `https://`
3. **Wrong domain**: Deployment URL vs custom domain
4. **Environment variable not set**: Railway might not have `CORS_ORIGINS` set at all
