# LLM Council Deployment Guide

Deploy LLM Council to the cloud or your own server.

## Quick Deploy Options

| Frontend | Backend | Cost | Best For |
|----------|---------|------|----------|
| Vercel | Railway | Free-$5/mo | Quickest setup |
| Vercel | Render | Free | Budget-friendly |
| Vercel | Fly.io | Free tier | Global edge |
| Docker | Docker | Self-hosted | Full control |

---

## Option 1: Vercel + Railway (Recommended)

### Step 1: Push to GitHub

```bash
# Initialize git if needed
git init
git add .
git commit -m "Initial commit"

# Create GitHub repo and push
gh repo create llm-council --public --push
# Or manually: create repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/llm-council.git
git push -u origin main
```

### Step 2: Deploy Backend to Railway

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `llm-council` repo
4. Railway auto-detects Python, configure:
   - **Root Directory**: `/` (project root)
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   ```
   OPENROUTER_API_KEY=sk-or-v1-your-key
   SECRET_KEY=generate-32-char-secret
   ENVIRONMENT=production
   CORS_ORIGINS=https://your-vercel-app.vercel.app
   # ALLOWED_ORIGINS works as an alternative to CORS_ORIGINS
   ```
6. Deploy and copy your Railway URL (e.g., `https://llm-council-production.up.railway.app`)

### Step 3: Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) and sign up with GitHub
2. Click **"Add New"** → **"Project"**
3. Import your `llm-council` repo
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Add environment variable:
   ```
   VITE_API_URL=https://llm-council-production.up.railway.app
   ```
6. Deploy!

### Step 4: Update CORS

Go back to Railway and update:
```
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
# Or set ALLOWED_ORIGINS if you prefer that variable name
```

---

## Option 2: Vercel + Render (Free Tier)

### Backend on Render

1. Go to [render.com](https://render.com) and sign up
2. Click **"New"** → **"Web Service"**
3. Connect your GitHub repo
4. Configure:
   - **Name**: llm-council-api
   - **Root Directory**: (leave empty)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (same as Railway)
6. Deploy and copy your Render URL

### Frontend on Vercel

Same as Option 1, Step 3.

---

## Option 3: Docker Self-Hosted (Proxmox/VPS)

## Prerequisites

1. **Proxmox Server** with Docker installed (LXC or VM)
2. **Domain name** pointing to your server (e.g., `council.yourdomain.com`)
3. **Cloudflare account** (optional, for tunnel/HTTPS)
4. **Google Cloud Console access** (for OAuth)

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-council.git
cd llm-council

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Required Environment Variables

Edit `.env` and set these values:

```bash
# Generate a secure secret key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Database (keep defaults for Docker)
DB_USER=council
DB_PASSWORD=your_secure_password
DB_NAME=llm_council

# Your OpenRouter API key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Google OAuth (see setup below)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
```

### 3. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project: "LLM Council"
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized JavaScript origins:
   - `https://council.yourdomain.com`
   - `http://localhost:3000` (for development)
7. Authorized redirect URIs:
   - `https://council.yourdomain.com`
8. Copy **Client ID** and **Client Secret** to `.env`

### 4. Deploy with Docker

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Access the App

- **With Cloudflare Tunnel**: `https://council.yourdomain.com`
- **Direct (local)**: `http://your-server-ip:80`

Default admin credentials (created during first run):
- Email: `admin@example.com`
- Password: `admin123`

**Change the admin password immediately after first login!**

## Cloudflare Tunnel Setup

For HTTPS without port forwarding:

### 1. Create Tunnel

1. Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com)
2. **Access** → **Tunnels** → **Create a tunnel**
3. Name: `llm-council`
4. Copy the **Tunnel Token**

### 2. Configure Tunnel

Add to your `.env`:
```bash
CLOUDFLARE_TUNNEL_TOKEN=eyJxxxxx
```

Edit `docker-compose.yml` and uncomment the `cloudflared` service:
```yaml
cloudflared:
  image: cloudflare/cloudflared:latest
  command: tunnel --no-autoupdate run
  environment:
    - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
  # ...
```

### 3. Configure Route

In Cloudflare Dashboard:
- Public hostname: `council.yourdomain.com`
- Service: `http://nginx:80`
- Enable SSL/TLS: Full (strict)

## Data Migration

If you have existing JSON data from a local installation:

```bash
# Run migration script
docker-compose exec backend python /app/../scripts/migrate_json_to_postgres.py \
  --admin-email your@email.com \
  --admin-password your_secure_password
```

## Maintenance

### Backup Database

```bash
# Backup
docker-compose exec postgres pg_dump -U council llm_council > backup.sql

# Restore
docker-compose exec -T postgres psql -U council llm_council < backup.sql
```

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Reset Database

```bash
# Warning: This deletes all data!
docker-compose down -v
docker-compose up -d
```

## Troubleshooting

### Can't Login

1. Check backend logs: `docker-compose logs backend`
2. Verify database is running: `docker-compose ps postgres`
3. Check CORS settings in `.env`

### Google OAuth Fails

1. Verify `GOOGLE_CLIENT_ID` matches your OAuth app
2. Check authorized origins include your domain
3. Ensure callback URL is correct

### API Returns 401

1. Access token may be expired
2. Try logging out and back in
3. Clear browser localStorage

### Database Connection Failed

1. Check PostgreSQL is running: `docker-compose ps`
2. Verify `DATABASE_URL` in environment
3. Check postgres logs: `docker-compose logs postgres`

## Architecture

```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │     Tunnel      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │      Nginx      │
                    │  (Reverse Proxy)│
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│    Frontend     │ │    Backend      │ │   PostgreSQL    │
│  (React + Vite) │ │   (FastAPI)     │ │   (Database)    │
└─────────────────┘ └────────┬────────┘ └─────────────────┘
                             │
                    ┌────────▼────────┐
                    │   OpenRouter    │
                    │    (LLM API)    │
                    └─────────────────┘
```

## Security Checklist

- [ ] Changed default admin password
- [ ] Set strong `SECRET_KEY`
- [ ] Set strong `DB_PASSWORD`
- [ ] Enabled HTTPS (via Cloudflare or SSL cert)
- [ ] Updated CORS_ORIGINS to only allow your domain
- [ ] Set up Cloudflare firewall rules (optional)
- [ ] Enabled Cloudflare bot protection (optional)

## Support

- Create an issue on GitHub for bugs
- Check logs first: `docker-compose logs`
- Include error messages in issue reports
