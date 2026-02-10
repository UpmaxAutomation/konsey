# Quick Start Guide

## Starting the Backend Server

### Option 1: Using the Startup Script (Recommended)

```bash
# Make the script executable (first time only)
chmod +x start-backend.sh

# Start the backend
./start-backend.sh
```

### Option 2: Manual Start

```bash
# Navigate to project root
cd /path/to/llm-council

# Activate virtual environment (if using one)
# source venv/bin/activate  # or your venv path

# Start the server
uvicorn backend.main:app --reload --port 8001 --host 127.0.0.1
```

### Option 3: Using Python directly

```bash
cd backend
python -m uvicorn main:app --reload --port 8001 --host 127.0.0.1
```

### Option 4: Using `uv` (if installed)

```bash
uv run uvicorn backend.main:app --reload --port 8001 --host 127.0.0.1
```

## Required Environment Variables

Create a `.env` file in the project root with:

```bash
# Required: OpenRouter API Key
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional: Database (if you want to use PostgreSQL)
USE_DATABASE=false
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/llm_council

# Optional: JWT Secret (for production)
SECRET_KEY=your-secret-key-here
```

## Verify Backend is Running

Once started, you should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8001
INFO:     Application startup complete.
```

Test it in your browser:
- Health check: http://127.0.0.1:8001/
- API docs: http://127.0.0.1:8001/docs

## Starting the Frontend

In a **separate terminal**:

```bash
cd frontend
npm install  # First time only
npm run dev
```

Frontend will run on: http://localhost:5173

## Troubleshooting

### Port 8001 already in use?
```bash
# Find what's using the port
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows

# Kill the process or use a different port
uvicorn backend.main:app --reload --port 8002 --host 127.0.0.1
```

Then update frontend `.env`:
```bash
VITE_API_URL=http://127.0.0.1:8002
```

### Backend won't start?
1. Check Python version: `python --version` (needs 3.10+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check for errors in the terminal output

### Database errors?
If you see database errors but don't need a database:
- Set `USE_DATABASE=false` in `.env`
- Or remove the `USE_DATABASE` variable entirely
