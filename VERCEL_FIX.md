# 🔧 Vercel Deployment Fix

## Common Issues & Quick Fixes

### Issue 1: "Root Directory Not Found"
**Fix:** In Vercel project settings:
- **Root Directory**: `frontend` (must be exactly this)
- **Framework Preset**: Vite (auto-detected is fine)

### Issue 2: "Build Failed"
**Fix:** Check these settings:
- **Build Command**: `npm run build` (should auto-detect)
- **Output Directory**: `dist` (should auto-detect)
- **Install Command**: `npm install` (should auto-detect)

### Issue 3: "Environment Variable Missing"
**Fix:** Add this in Vercel → Settings → Environment Variables:
```
VITE_API_URL=https://your-railway-url.up.railway.app
```
**Important:** Replace with your actual Railway URL!

### Issue 4: "Cannot find module"
**Fix:** Make sure `package.json` is in the `frontend` folder (it is ✅)

---

## Step-by-Step Vercel Setup

1. **Go to Vercel Dashboard** → Add New → Project

2. **Import Repository:**
   - Select: `UpmaxAutomation/konsey`
   - Branch: `feature/deploy-vercel-railway`

3. **Configure Project:**
   - **Framework Preset**: Vite (auto-detected)
   - **Root Directory**: `frontend` ⚠️ **CRITICAL - Must be exactly "frontend"**
   - **Build Command**: `npm run build` (auto)
   - **Output Directory**: `dist` (auto)
   - **Install Command**: `npm install` (auto)

4. **Environment Variables:**
   - Click "Environment Variables"
   - Add:
     ```
     Name: VITE_API_URL
     Value: https://your-railway-url.up.railway.app
     ```
   - **Replace** `your-railway-url` with your actual Railway URL!

5. **Deploy:**
   - Click "Deploy"
   - Wait 1-2 minutes
   - Check build logs if it fails

---

## If Build Still Fails

### Check Build Logs:
1. Go to Vercel → Your Project → Deployments
2. Click on the failed deployment
3. Click "View Function Logs" or "Build Logs"
4. Copy the error message

### Common Errors:

**"Cannot find module 'react'"**
→ Make sure Root Directory is `frontend`

**"VITE_API_URL is undefined"**
→ Add environment variable in Vercel settings

**"Build command failed"**
→ Check that `package.json` exists in `frontend/` folder

**"404 on routes"**
→ This is normal for SPA, Vercel handles it automatically

---

## Quick Test After Deploy

1. Visit your Vercel URL
2. Open browser console (F12)
3. Check for errors
4. If you see "Cannot connect to server" → Check `VITE_API_URL` is correct

---

## Still Having Issues?

Share the error message from Vercel build logs and I'll fix it!
