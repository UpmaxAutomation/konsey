# ✅ Deployment Checklist - Copy/Paste Ready

## Railway Variables (Copy All At Once)

```
SECRET_KEY=7bd5cee9815233d5d787fd288d343fdf84a95bc5d523e3157d5f71a2ca97d20d
USE_DATABASE=true
DATABASE_URL=postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5$$J1vbZmqX$c@aws-0-us-west-2.pooler.supabase.com:6543/postgres
ENVIRONMENT=production
CORS_ORIGINS=
```

**Note:** Leave `CORS_ORIGINS` empty, add Vercel URL after frontend deploy.

---

## Vercel Environment Variable

After Railway gives you a URL, use it here:

```
VITE_API_URL=https://your-railway-url.up.railway.app
```

---

## Quick Test Commands

**Test Railway:**
```bash
curl https://your-railway-url.up.railway.app/docs
```

**Test Vercel:**
Just visit the URL in browser!

---

## If Something Fails

1. Check Railway logs: Dashboard → Service → Logs
2. Check Vercel logs: Dashboard → Project → Deployments → Click latest → View Function Logs
3. Verify all environment variables are set correctly
