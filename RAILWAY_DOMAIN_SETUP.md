# 🌐 Railway Domain Setup

## Generate Public Domain

1. **Go to Railway Dashboard** → Your Service
2. **Click on "Settings"** tab
3. **Scroll down to "Networking"** section
4. **Click "Generate Domain"** button
5. **Copy the generated URL** (e.g., `https://konsey-production.up.railway.app`)

This URL will be your backend API URL!

---

## Verify Environment Variables

Go to Railway → Your Service → **Variables** tab and verify you have:

✅ **Required:**
- `SECRET_KEY=7bd5cee9815233d5d787fd288d343fdf84a95bc5d523e3157d5f71a2ca97d20d`
- `USE_DATABASE=true`
- `DATABASE_URL=postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5$$J1vbZmqX$c@aws-0-us-west-2.pooler.supabase.com:6543/postgres`
- `ENVIRONMENT=production`

⏳ **To Update After Vercel:**
- `CORS_ORIGINS=` (leave empty for now, will add Vercel URL later)

---

## Test Backend is Running

1. **Visit your Railway domain** + `/docs`
   - Example: `https://konsey-production.up.railway.app/docs`
2. **You should see the FastAPI Swagger UI** ✅
3. **If you see it, backend is working!**

---

## Next Steps

After Railway domain is set up:
1. ✅ Copy your Railway URL
2. ✅ Deploy frontend to Vercel (use Railway URL for `VITE_API_URL`)
3. ✅ Update `CORS_ORIGINS` in Railway with Vercel URL
