# Finding Supabase Database Connection

## Alternative Locations in Supabase Dashboard:

### Option 1: Settings → Database → Connection Info
1. Go to: https://supabase.com/dashboard/project/rdjxqrrnhfbekpbsjgjk/settings/database
2. Look for:
   - **Host** (database hostname)
   - **Database name** (usually "postgres")
   - **Port** (usually 5432 or 6543 for pooler)
   - **User** (usually "postgres")

### Option 2: Connection Pooling
1. Same page: Settings → Database
2. Look for **Connection pooling** section
3. There might be a different hostname for pooled connections

### Option 3: Project Settings
1. Go to: https://supabase.com/dashboard/project/rdjxqrrnhfbekpbsjgjk/settings/general
2. Check for database connection details

### Option 4: API Settings
1. Go to: Settings → API
2. Sometimes database info is shown there

## What We Need:

Please provide:
1. **Database Host** (the hostname/IP)
2. **Port** (5432 for direct, 6543 for pooler)
3. **Database name** (usually "postgres")
4. **User** (usually "postgres")
5. **Password** (you already provided: 3yJ5$$J1vbZmqX$c)

Or if you see any of these formats, share them:
- `postgres://...`
- `postgresql://...`
- Host: `xxx.supabase.co`
- Pooler URL: `xxx.pooler.supabase.com`
