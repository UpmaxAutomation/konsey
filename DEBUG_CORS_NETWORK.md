# 🔍 Debug CORS - Check Network Tab

## What to Check in Browser

1. **Open Developer Tools** (F12)
2. **Go to Network tab**
3. **Try to login** (trigger the error)
4. **Find the failed request** to `/api/auth/login`
5. **Click on it** to see details

## Check These Headers

### Request Headers (what browser sends):
- **Origin**: Should be `https://konsey-eight.vercel.app`
- **Method**: Should be `POST` (or `OPTIONS` for preflight)

### Response Headers (what server returns):
- **Access-Control-Allow-Origin**: Should be `https://konsey-eight.vercel.app`
- **Access-Control-Allow-Credentials**: Should be `true`
- **Status Code**: What HTTP status? (200, 400, 500?)

## What to Share

1. **Request URL**: Full URL being called
2. **Request Method**: POST or OPTIONS?
3. **Status Code**: HTTP status (200, 400, 500, etc.)
4. **Response Headers**: Especially `Access-Control-Allow-Origin`
5. **Error Message**: Exact error from console

## Possible Issues

- **Preflight (OPTIONS) fails**: CORS headers missing on OPTIONS
- **Actual request fails**: CORS headers missing on POST
- **Wrong origin**: Browser sending different origin than expected
- **Cached preflight**: Browser cached a failed preflight response
