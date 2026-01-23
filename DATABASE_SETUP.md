# Database Setup Guide

## Database Type

**This project uses PostgreSQL directly, NOT Supabase.**

The project uses:
- **SQLAlchemy** (ORM)
- **asyncpg** (PostgreSQL async driver)
- **PostgreSQL** database

## Setup Instructions

### 1. Enable Database Mode

Set the following environment variable in your `.env` file:

```bash
USE_DATABASE=true
```

### 2. Configure Database URL

Set your PostgreSQL connection string:

```bash
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database_name
```

#### Examples:

**Local PostgreSQL:**
```bash
DATABASE_URL=postgresql+asyncpg://council:council@localhost:5432/llm_council
```

**Supabase PostgreSQL:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres
```

**Railway PostgreSQL:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@containers-us-west-xxx.railway.app:5432/railway
```

**Render PostgreSQL:**
```bash
DATABASE_URL=postgresql+asyncpg://user:password@dpg-xxxxx-a.oregon-postgres.render.com:5432/dbname
```

### 3. Initialize Database

The database tables are automatically created on first startup if `USE_DATABASE=true` is set.

### 4. Run Migrations (if needed)

```bash
cd backend
alembic upgrade head
```

## Using Supabase

If you want to use Supabase's PostgreSQL database:

1. Create a Supabase project at https://supabase.com
2. Go to Settings → Database
3. Copy the connection string
4. Update it to use `asyncpg` driver:
   ```
   postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
5. Set it in your `.env`:
   ```bash
   USE_DATABASE=true
   DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres
   ```

**Note:** This project does NOT use Supabase's client SDK or features like Row Level Security (RLS). It only uses Supabase's PostgreSQL database as a regular PostgreSQL database.

## Environment Variables

Required in `.env`:

```bash
# Enable database mode
USE_DATABASE=true

# Database connection string
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Optional: Enable SQL query logging
DB_ECHO=false
```

## Verification

After setting up, start the backend:

```bash
cd backend
python -m uvicorn main:app --reload
```

Check the logs - you should see:
```
Database tables initialized
```

If you see errors, check:
1. `USE_DATABASE=true` is set
2. `DATABASE_URL` is correct
3. Database server is accessible
4. Credentials are correct
