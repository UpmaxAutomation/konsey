# 🚀 Deploy to Vercel Using CLI (I Can Do This!)

## Quick Deploy - 2 Steps

### Step 1: Login to Vercel CLI

Run this command:
```bash
vercel login
```

This will open your browser to authenticate. Click "Authorize" and you're done!

### Step 2: Run Deployment Script

I've created a script that will deploy everything automatically. Just run:

```bash
./deploy-vercel.sh
```

The script will:
1. ✅ Check if you're logged in
2. ✅ Ask for your Railway URL
3. ✅ Deploy to Vercel with correct settings
4. ✅ Set environment variables automatically
5. ✅ Give you the deployment URL

---

## Manual Deploy (Alternative)

If you prefer to do it manually:

```bash
cd frontend
vercel --prod --env VITE_API_URL=https://your-railway-url.up.railway.app
```

Replace `your-railway-url` with your actual Railway URL.

---

## After Deployment

1. **Copy your Vercel URL** (shown after deployment)
2. **Go to Railway** → Variables
3. **Add**: `CORS_ORIGINS=https://your-vercel-url.vercel.app`
4. **Test your app!**

---

## Need Help?

If you get any errors, share them and I'll fix it!
