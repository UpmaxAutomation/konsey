# 🔐 Deployment Environment Variables

## Backend (Railway) - Required Variables

Copy these into Railway → Your Service → Variables:

```bash
# Required - JWT Secret (already generated for you)
SECRET_KEY=7bd5cee9815233d5d787fd288d343fdf84a95bc5d523e3157d5f71a2ca97d20d

# Required - Enable database
USE_DATABASE=true

# Required - Your Supabase connection (use the pooler URL!)
DATABASE_URL=postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5$$J1vbZmqX$c@aws-0-us-west-2.pooler.supabase.com:6543/postgres

# Recommended - Set to production
ENVIRONMENT=production

# Will update after Vercel deploy (leave empty for now, add after Step 3)
CORS_ORIGINS=
```

**Note**: `OPENROUTER_API_KEY` is **NOT required** - users will set their own keys!

---

## Frontend (Vercel) - Required Variables

After Railway deployment, copy this into Vercel → Your Project → Settings → Environment Variables:

```bash
# Replace with your actual Railway URL after Step 2
VITE_API_URL=https://your-railway-url.up.railway.app
```

---

## After Both Deployments

1. **Get your Vercel URL** (e.g., `https://llm-council.vercel.app`)
2. **Go back to Railway** → Variables
3. **Update CORS_ORIGINS**:
   ```
   CORS_ORIGINS=https://your-vercel-app.vercel.app
   ```
4. **Railway will auto-redeploy** with new CORS settings

---

## Quick Reference

- **Railway URL**: Get from Railway → Service → Settings → Domains
- **Vercel URL**: Get from Vercel → Project → Overview
- **SECRET_KEY**: Already generated above ✅
- **DATABASE_URL**: Your Supabase pooler URL ✅
