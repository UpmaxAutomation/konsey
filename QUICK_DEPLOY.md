# 🚀 Quick Deploy - 5 Minutes

## Step 1: Railway Backend (2 min)

1. Go to https://railway.app → New Project → Deploy from GitHub
2. Select repo: `UpmaxAutomation/konsey`
3. Branch: `feature/deploy-vercel-railway`
4. **Add these 4 variables** (Variables tab):
   ```
   SECRET_KEY=7bd5cee9815233d5d787fd288d343fdf84a95bc5d523e3157d5f71a2ca97d20d
   USE_DATABASE=true
   DATABASE_URL=postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5$$J1vbZmqX$c@aws-0-us-west-2.pooler.supabase.com:6543/postgres
   ENVIRONMENT=production
   ```
5. Settings → Networking → Generate Domain
6. Copy the URL (e.g., `https://xxx.up.railway.app`)

## Step 2: Vercel Frontend (2 min)

1. Go to https://vercel.com → Add New → Project
2. Import: `UpmaxAutomation/konsey`
3. **Settings:**
   - Root Directory: `frontend`
   - Framework: Vite (auto)
4. **Environment Variable:**
   ```
   VITE_API_URL=https://xxx.up.railway.app
   ```
   (Use your Railway URL from Step 1)
5. Deploy

## Step 3: Update CORS (30 sec)

1. Railway → Variables
2. Add: `CORS_ORIGINS=https://your-vercel-url.vercel.app`
3. Done!

## Test

Visit your Vercel URL → Register → Set API key in Settings → Use app!

---

**That's it! 3 steps, 5 minutes.**
