# 🚀 Deploy LLM Council to Internet - Step by Step

Follow these steps to deploy your app live on the internet!

---

## 📦 What You Need

1. ✅ **GitHub account** (free)
2. ✅ **OpenRouter API key** (you already have this)
3. ✅ **Supabase database** (you already have this set up!)

---

## 🎯 Quick Deploy: Vercel (Frontend) + Railway (Backend)

This is the **easiest and fastest** way to deploy.

### Step 1: Push Your Code to GitHub

```bash
# Check if you're already on GitHub
git remote -v

# If not, create a GitHub repo and push:
git init  # if not already initialized
git add .
git commit -m "Ready for deployment"

# Create repo on GitHub (or use existing)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/llm-council.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy Backend to Railway (5 minutes)

1. **Go to Railway**: https://railway.app
2. **Sign up** with your GitHub account
3. **Click "New Project"** → **"Deploy from GitHub repo"**
4. **Select your repository**: `llm-council`
5. **Railway will auto-detect Python** ✅

6. **Configure Settings** (click on the service):
   - **Root Directory**: `/` (default is fine)
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

7. **Add Environment Variables** (click "Variables" tab):

   Click "New Variable" and add these one by one:

   ```bash
   # Required - Generate a secret key
   SECRET_KEY=your-32-character-secret-here
   
   # Required - Enable database
   USE_DATABASE=true
   
   # Required - Your Supabase connection (use the pooler URL!)
   DATABASE_URL=postgresql://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5$$J1vbZmqX$c@aws-0-us-west-2.pooler.supabase.com:6543/postgres
   
   # Recommended - Set to production
   ENVIRONMENT=production
   
   # Recommended - Will update after Vercel deploy
   CORS_ORIGINS=https://your-app.vercel.app
   ```
   
   **Note**: `OPENROUTER_API_KEY` is **NOT required** here! 
   - Users will set their own API keys in Settings
   - OR you can set a system-wide key later in the Admin Panel

   **Generate SECRET_KEY:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

8. **Deploy**: Railway will automatically start deploying
9. **Wait for deployment** (2-3 minutes)
10. **Copy your Railway URL**: 
    - Click on your service → Settings → Domains
    - Copy the URL (e.g., `https://llm-council-production.up.railway.app`)

### Step 3: Deploy Frontend to Vercel (3 minutes)

1. **Go to Vercel**: https://vercel.com
2. **Sign up** with your GitHub account
3. **Click "Add New"** → **"Project"**
4. **Import your repository**: Select `llm-council`
5. **Configure Project**:
   - **Framework Preset**: Vite (auto-detected) ✅
   - **Root Directory**: `frontend` (IMPORTANT!)
   - **Build Command**: `npm run build` (auto-detected) ✅
   - **Output Directory**: `dist` (auto-detected) ✅

6. **Add Environment Variable**:
   - Click "Environment Variables"
   - Add:
     ```
     VITE_API_URL=https://your-railway-url.up.railway.app
     ```
     (Use the Railway URL from Step 2)

7. **Click "Deploy"**
8. **Wait for deployment** (1-2 minutes)
9. **Copy your Vercel URL**: 
    - You'll see it after deployment (e.g., `https://llm-council.vercel.app`)

### Step 4: Update CORS (1 minute)

1. **Go back to Railway** → Your service → Variables
2. **Update CORS_ORIGINS**:
   ```
   CORS_ORIGINS=https://your-vercel-app.vercel.app
   ```
   (Use your actual Vercel URL from Step 3)
3. **Railway will automatically redeploy** with new CORS settings

### Step 5: Test Your Deployment! 🎉

1. **Visit your Vercel URL** (e.g., `https://llm-council.vercel.app`)
2. **Register a new account**
3. **Create a conversation**
4. **Test the council system**

**You're live! 🚀**

---

## 🔧 Alternative: Render (Free Tier)

If you prefer Render over Railway:

### Backend on Render

1. Go to https://render.com
2. Sign up with GitHub
3. Click **"New"** → **"Web Service"**
4. Connect your GitHub repo
5. Configure:
   - **Name**: `llm-council-api`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
6. Add the same environment variables as Railway
7. Deploy!

**Note**: Render free tier spins down after 15 min of inactivity. Upgrade to "Starter" ($7/mo) for always-on.

---

## 📋 Environment Variables Checklist

Make sure you have ALL of these in Railway/Render:

- [ ] `SECRET_KEY` - 32+ character secret (generate with Python)
- [ ] `USE_DATABASE=true` - Enable database
- [ ] `DATABASE_URL` - Your Supabase pooler URL
- [ ] `ENVIRONMENT=production` - Production mode
- [ ] `CORS_ORIGINS` - Your Vercel URL (after frontend deploy)

**Note**: `OPENROUTER_API_KEY` is **NOT required** in environment variables!
- Users will set their own API keys in Settings
- OR you can optionally set a system-wide key in Admin Panel after deployment

---

## 🐛 Common Issues & Fixes

### Backend won't start?

**Check logs**: Railway → Service → Logs tab

**Common fixes**:
- ✅ Verify `DATABASE_URL` uses **pooler** URL (port 6543)
- ✅ Check `SECRET_KEY` is set (required in production)
- ✅ Verify `OPENROUTER_API_KEY` is valid

### Frontend can't connect?

**Check**:
- ✅ `VITE_API_URL` matches your Railway URL exactly
- ✅ `CORS_ORIGINS` includes your Vercel URL
- ✅ Backend is running (check Railway logs)

### Database connection fails?

**Check**:
- ✅ Using **pooler URL** (not direct connection)
- ✅ Password is correct
- ✅ Supabase project is active
- ✅ URL format: `postgresql://postgres.[ref]:[PASSWORD]@aws-0-us-west-2.pooler.supabase.com:6543/postgres`

### 401 Unauthorized?

**Fix**:
- ✅ Set `SECRET_KEY` in production
- ✅ Clear browser localStorage
- ✅ Re-register account

---

## 🔐 Security Reminders

- ✅ Never commit `.env` files to git
- ✅ Use strong `SECRET_KEY` (32+ characters)
- ✅ Set `CORS_ORIGINS` to only your domain
- ✅ Keep `OPENROUTER_API_KEY` secret

---

## 📊 Monitoring Your Deployment

### Railway
- **Logs**: Dashboard → Service → Logs
- **Metrics**: Dashboard → Service → Metrics
- **Deployments**: Dashboard → Service → Deployments

### Vercel
- **Logs**: Dashboard → Project → Functions → Logs
- **Analytics**: Dashboard → Project → Analytics
- **Deployments**: Dashboard → Project → Deployments

---

## 🎯 Next Steps After Deployment

1. **Custom Domain**: Add your domain in Vercel settings
2. **Google OAuth**: Set up for easier login
3. **Monitoring**: Add error tracking (optional)
4. **Backups**: Configure Supabase backups

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Backend deployed (Railway/Render)
- [ ] Frontend deployed (Vercel)
- [ ] All environment variables set
- [ ] CORS configured correctly
- [ ] Database connected
- [ ] Tested registration
- [ ] Tested conversation creation
- [ ] Everything works! 🎉

---

## 💰 Cost Estimate

**Free Tier**:
- Vercel: Free (generous limits)
- Railway: $5 credit/month (usually enough)
- Render: Free (with limitations)
- Supabase: Free tier (500MB database)

**Total**: $0-7/month depending on usage

---

## 🆘 Need Help?

1. **Check logs** in Railway/Render dashboard
2. **Check browser console** for frontend errors
3. **Verify environment variables** are all set
4. **Test backend directly**: Visit `https://your-backend-url/docs`

---

**You're ready to deploy! Follow the steps above and you'll be live in 15 minutes! 🚀**
