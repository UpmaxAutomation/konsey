# 🚀 Vercel Deployment - Exact Steps

## Step 1: Go to Vercel
https://vercel.com → Sign in with GitHub

## Step 2: Import Project
1. Click **"Add New"** → **"Project"**
2. Find repository: `UpmaxAutomation/konsey`
3. Click **"Import"**

## Step 3: Configure (CRITICAL - Copy Exactly)

### Framework Preset:
- Select: **"Vite"** (or leave auto-detected)

### Root Directory:
- Click **"Edit"** next to Root Directory
- Type exactly: **`frontend`**
- Click **"Continue"**

### Build and Output Settings:
- **Build Command**: `npm run build` (should auto-fill)
- **Output Directory**: `dist` (should auto-fill)
- **Install Command**: `npm install` (should auto-fill)

### Environment Variables:
Click **"Environment Variables"** → Add:

**Name:** `VITE_API_URL`  
**Value:** `https://your-railway-url.up.railway.app`

⚠️ **Replace `your-railway-url` with your actual Railway URL!**

## Step 4: Deploy
Click **"Deploy"** button

## Step 5: Wait
- Build takes 1-2 minutes
- Watch the build logs
- If it fails, check the error message

---

## If Build Fails

### Error: "Root Directory not found"
→ You didn't set Root Directory to `frontend`

### Error: "Cannot find module"
→ Root Directory must be `frontend`

### Error: "VITE_API_URL is undefined"
→ Add environment variable `VITE_API_URL`

### Error: "Build command failed"
→ Check build logs for specific error

---

## After Successful Deploy

1. Copy your Vercel URL (e.g., `https://konsey.vercel.app`)
2. Go to Railway → Variables
3. Add: `CORS_ORIGINS=https://your-vercel-url.vercel.app`
4. Railway will auto-redeploy
5. Test your app!

---

## Quick Test

Visit: `https://your-vercel-url.vercel.app`

If you see the login page → ✅ Success!
If you see errors → Check browser console (F12)
