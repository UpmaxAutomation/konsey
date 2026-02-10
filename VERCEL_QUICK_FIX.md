# ⚡ Vercel Quick Fix - Copy This

## Exact Vercel Settings

When importing project in Vercel:

### Project Settings:
- **Framework Preset**: `Vite` (auto-detected)
- **Root Directory**: `frontend` ⚠️ **MUST BE EXACTLY THIS**
- **Build Command**: `npm run build` (auto)
- **Output Directory**: `dist` (auto)
- **Install Command**: `npm install` (auto)

### Environment Variables:
```
VITE_API_URL=https://your-railway-url.up.railway.app
```
(Replace with your actual Railway URL)

---

## If It Still Fails

**Share the error message** from Vercel build logs:
1. Vercel → Your Project → Deployments
2. Click failed deployment
3. Click "View Build Logs"
4. Copy the red error message

I'll fix it immediately!

---

## Most Common Issues:

❌ **"Root Directory not found"**
→ Set Root Directory to: `frontend`

❌ **"Cannot find module"**
→ Root Directory must be `frontend`

❌ **"Build failed"**
→ Check build logs for specific error

❌ **"404 on routes"**
→ Already fixed with rewrites in vercel.json ✅
