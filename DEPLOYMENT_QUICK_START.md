# 🚀 Quick Deployment Guide - LLM Council

Deploy your LLM Council app to the internet in 15 minutes!

## 📋 Prerequisites

1. **GitHub Account** - Free
2. **OpenRouter API Key** - Get from [openrouter.ai](https://openrouter.ai)
3. **Supabase Account** (for database) - Free tier available at [supabase.com](https://supabase.com)

---

## 🎯 Option 1: Vercel + Railway (Easiest - Recommended)

### Step 1: Push Code to GitHub

```bash
# If not already on GitHub
git init
git add .
git commit -m "Ready for deployment"

# Create GitHub repo (or use existing)
gh repo create llm-council --public --push
# OR manually create on github.com and push
```

### Step 2: Deploy Backend to Railway

1. **Sign up**: Go to [railway.app](https://railway.app) → Sign up with GitHub
2. **New Project**: Click "New Project" → "Deploy from GitHub repo"
3. **Select Repo**: Choose your `llm-council` repository
4. **Configure**:
   - Railway auto-detects Python
   - **Root Directory**: `/` (leave as default)
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. **Add Environment Variables** (in Railway dashboard → Variables tab):

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SECRET_KEY=your-32-character-secret-key-here
USE_DATABASE=true
DATABASE_URL=postgresql://postgres.rdjxqrrnhfbekpbsjgjk:[YOUR-PASSWORD]@aws-0-us-west-2.pooler.supabase.com:6543/postgres

# Optional but recommended
ENVIRONMENT=production
CORS_ORIGINS=https://your-app.vercel.app
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

6. **Deploy**: Railway will automatically deploy
7. **Copy URL**: After deployment, copy your Railway URL (e.g., `https://llm-council-production.up.railway.app`)

### Step 3: Deploy Frontend to Vercel

1. **Sign up**: Go to [vercel.com](https://vercel.com) → Sign up with GitHub
2. **New Project**: Click "Add New" → "Project"
3. **Import Repo**: Select your `llm-council` repository
4. **Configure**:
   - **Framework Preset**: Vite (auto-detected)
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Output Directory**: `dist` (auto-detected)
5. **Add Environment Variable**:
   ```
   VITE_API_URL=https://your-railway-url.up.railway.app
   ```
   (Use the Railway URL from Step 2)
6. **Deploy**: Click "Deploy"
7. **Copy URL**: After deployment, copy your Vercel URL (e.g., `https://llm-council.vercel.app`)

### Step 4: Update CORS Settings

Go back to Railway → Variables tab and update:
```
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

### Step 5: Test Your Deployment

1. Visit your Vercel URL
2. Register a new account
3. Try creating a conversation
4. Check that everything works!

---

## 🎯 Option 2: Vercel + Render (Free Tier)

### Backend on Render

1. **Sign up**: Go to [render.com](https://render.com) → Sign up
2. **New Web Service**: Click "New" → "Web Service"
3. **Connect GitHub**: Link your repository
4. **Configure**:
   - **Name**: `llm-council-api`
   - **Root Directory**: (leave empty)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. **Add Environment Variables** (same as Railway above)
6. **Deploy**: Click "Create Web Service"
7. **Copy URL**: After deployment (e.g., `https://llm-council-api.onrender.com`)

### Frontend on Vercel

Same as Option 1, Step 3, but use your Render URL instead of Railway URL.

---

## 🔧 Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | `sk-or-v1-...` |
| `SECRET_KEY` | JWT secret (32+ chars) | Generate with Python |
| `USE_DATABASE` | Enable database | `true` |
| `DATABASE_URL` | Supabase connection string | `postgresql://...` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `production` or `development` | `development` |
| `CORS_ORIGINS` | Allowed frontend URLs | `*` (all) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry | `30` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | - |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | - |

---

## 🗄️ Database Setup (Supabase)

You're already using Supabase! Just make sure:

1. **Connection String**: Use the **Connection Pooler** URL (not direct)
   - Format: `postgresql://postgres.[ref]:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:6543/postgres`
2. **Password**: Use your Supabase database password
3. **Test Connection**: Railway/Render will test on deploy

---

## 🔐 Security Checklist

- [ ] Set strong `SECRET_KEY` (32+ characters)
- [ ] Set `CORS_ORIGINS` to only your Vercel domain
- [ ] Set `ENVIRONMENT=production`
- [ ] Use Supabase connection pooler (not direct connection)
- [ ] Keep `OPENROUTER_API_KEY` secret (never commit to git)

---

## 🐛 Troubleshooting

### Backend won't start?

1. **Check logs**: Railway/Render dashboard → Logs tab
2. **Verify DATABASE_URL**: Must use pooler URL for Supabase
3. **Check SECRET_KEY**: Must be set in production
4. **Verify OPENROUTER_API_KEY**: Must be valid

### Frontend can't connect to backend?

1. **Check VITE_API_URL**: Must match your backend URL exactly
2. **Check CORS_ORIGINS**: Must include your Vercel URL
3. **Check backend logs**: Look for CORS errors

### Database connection fails?

1. **Use Pooler URL**: Not the direct connection
2. **Check password**: Must be correct
3. **Check Supabase**: Project must be active
4. **Add `statement_cache_size=0`**: Already handled in code

### 401 Unauthorized errors?

1. **Check SECRET_KEY**: Must be set
2. **Clear browser localStorage**: Old tokens might be invalid
3. **Re-login**: Register a new account

---

## 📊 Monitoring

### Railway
- View logs: Dashboard → Service → Logs
- View metrics: Dashboard → Service → Metrics

### Vercel
- View logs: Dashboard → Project → Functions → Logs
- View analytics: Dashboard → Project → Analytics

---

## 🚀 Next Steps

1. **Custom Domain**: Add your domain in Vercel settings
2. **Google OAuth**: Set up Google OAuth for easier login
3. **Monitoring**: Set up error tracking (Sentry, etc.)
4. **Backups**: Configure Supabase backups

---

## 💡 Pro Tips

- **Railway**: Free tier includes $5 credit/month
- **Render**: Free tier spins down after 15 min inactivity (upgrade for always-on)
- **Vercel**: Free tier is generous for frontend hosting
- **Supabase**: Free tier includes 500MB database

---

## 📞 Need Help?

1. Check logs in Railway/Render dashboard
2. Check browser console for frontend errors
3. Verify all environment variables are set
4. Test backend directly: `https://your-backend-url/docs`

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Backend deployed (Railway/Render)
- [ ] Frontend deployed (Vercel)
- [ ] Environment variables set
- [ ] CORS configured
- [ ] Database connected
- [ ] Test registration works
- [ ] Test conversation creation works
- [ ] Custom domain added (optional)

**You're live! 🎉**
