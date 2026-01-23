# Troubleshooting "Cannot connect to server" Error

## ✅ Your Backend IS Running!

The backend server is running correctly on port 8001. The issue is likely a frontend configuration mismatch.

## Quick Fix

### 1. Restart Frontend Dev Server

The frontend needs to be restarted to pick up environment variables:

```bash
# Stop the current frontend (Ctrl+C in the terminal running it)
# Then restart:
cd frontend
npm run dev
```

### 2. Verify Configuration

**Frontend `.env` file** (`frontend/.env`):
```bash
VITE_API_URL=http://localhost:8001
```

**Backend is running on:**
- ✅ http://localhost:8001
- ✅ http://127.0.0.1:8001

### 3. Check Browser Console

Open browser DevTools (F12) → Console tab and look for:
- Network errors
- CORS errors
- The exact error message

### 4. Test Backend Directly

Open in browser: http://localhost:8001/

You should see:
```json
{"status":"ok","service":"LLM Council API"}
```

### 5. Test Registration Endpoint

```bash
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123456","name":"Test"}'
```

## Common Issues

### Issue: Frontend can't reach backend

**Solution:** Make sure both are running:
- Backend: `./start-backend.sh` or `uvicorn backend.main:app --reload --port 8001`
- Frontend: `cd frontend && npm run dev`

### Issue: CORS errors in browser console

**Solution:** Backend CORS is already configured for `localhost:5173`. If you're using a different port, add it to backend `.env`:
```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Issue: Port 8001 already in use

**Solution:** 
```bash
# Find and kill the process
lsof -ti:8001 | xargs kill -9

# Or use a different port
uvicorn backend.main:app --reload --port 8002
```

Then update `frontend/.env`:
```bash
VITE_API_URL=http://localhost:8002
```

### Issue: Environment variables not loading

**Solution:**
1. Make sure `.env` file is in `frontend/` directory
2. Restart the frontend dev server after changing `.env`
3. Vite only loads `.env` files on startup

## Still Not Working?

1. **Check backend logs** - Look for errors in the terminal running the backend
2. **Check frontend console** - Browser DevTools → Console
3. **Check network tab** - Browser DevTools → Network → Look for failed requests
4. **Verify URLs match** - Frontend `.env` URL must match where backend is running
