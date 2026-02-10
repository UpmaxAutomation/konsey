# 🧪 Test CORS Locally

## Step 1: Start Backend Server

```bash
cd /Users/sezars/llm-council
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

## Step 2: Test CORS with curl

### Test OPTIONS (preflight):
```bash
curl -v -X OPTIONS \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  http://localhost:8001/api/auth/login
```

**Expected:**
- Status: `200 OK`
- Header: `access-control-allow-origin: http://localhost:5173`
- Header: `access-control-allow-methods: POST, ...`

### Test POST (actual request):
```bash
curl -v -X POST \
  -H "Origin: http://localhost:5173" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}' \
  http://localhost:8001/api/auth/login
```

**Expected:**
- Status: `400` or `401` (not CORS error)
- Header: `access-control-allow-origin: http://localhost:5173`

## Step 3: Check Debug Endpoint

```bash
curl http://localhost:8001/api/debug/cors
```

Should show:
```json
{
  "cors_origins": ["http://localhost:5173", ...],
  "env_origins": "",
  "default_origins": [...],
  "allow_credentials": true
}
```

## Step 4: Test from Browser

1. Start frontend: `cd frontend && npm run dev`
2. Open: `http://localhost:5173`
3. Open DevTools (F12) → Network tab
4. Try to login
5. Check the `/api/auth/login` request:
   - **Request Headers** → `Origin: http://localhost:5173`
   - **Response Headers** → `Access-Control-Allow-Origin: http://localhost:5173`
   - **Status Code**: Should be 200, 400, or 401 (NOT CORS error)

## If CORS Still Fails

Check the debug log:
```bash
cat /Users/sezars/llm-council/.cursor/debug.log | tail -20
```

Look for:
- `cors_config` - What origins are configured
- `cors_middleware:config` - Middleware configuration
- `cors_request:entry` - What origin the request has
- `cors_request:response` - What CORS headers were sent
