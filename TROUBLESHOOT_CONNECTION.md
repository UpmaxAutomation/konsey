# 🔧 Troubleshooting "Failed to connect to server"

## What I Fixed

1. ✅ **Standardized API_BASE URL** - Now properly adds `/api` suffix
2. ✅ **Fixed Sidebar.jsx** - Now uses API_BASE from client.js instead of duplicating
3. ✅ **Set environment variable** for both Production and Preview
4. ✅ **Redeployed** with fixes

## New Deployment URL

**Test this URL:**
https://frontend-a5slhqljv-upmaxnow-4711s-projects.vercel.app

---

## If Still Not Working

### Check Browser Console (F12)

1. Open your Vercel URL
2. Press F12 → Console tab
3. Look for errors like:
   - `Failed to fetch`
   - `CORS error`
   - `Network error`
   - `VITE_API_URL is undefined`

### Verify Environment Variable

The environment variable should be:
```
VITE_API_URL=https://konsey-production-b999.up.railway.app
```

**Check in Vercel:**
1. Go to: https://vercel.com/upmaxnow-4711s-projects/frontend/settings/environment-variables
2. Verify `VITE_API_URL` is set correctly
3. Make sure it's set for **Production** environment

### Test Railway Backend Directly

```bash
curl https://konsey-production-b999.up.railway.app/
# Should return: {"status":"ok","service":"LLM Council API"}
```

### Check CORS

Make sure in Railway you have:
```
CORS_ORIGINS=https://frontend-a5slhqljv-upmaxnow-4711s-projects.vercel.app
```

**Note:** Use the latest Vercel URL (it changes with each deployment)

---

## Quick Fix: Hard Refresh

1. Open your Vercel URL
2. Press `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
3. This clears cache and reloads with new build

---

## Still Having Issues?

Share:
1. Browser console errors (F12 → Console)
2. Network tab errors (F12 → Network → Look for failed requests)
3. The exact error message you see
