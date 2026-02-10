# 🔧 Fix: "Tenant or user not found" Database Error

## The Problem

The error **"Tenant or user not found"** is a Supabase authentication error. This means the database connection string is incorrect.

## Common Causes

1. **Wrong DATABASE_URL format** - Using direct connection instead of pooler
2. **Incorrect password** - Password in connection string doesn't match Supabase
3. **Wrong user** - Database user doesn't exist
4. **Missing USE_DATABASE** - Database mode not enabled

## Fix Steps

### 1. Check Railway Environment Variables

Go to **Railway Dashboard** → Your Service → **Variables** tab

**Required variables:**
- `USE_DATABASE=true` (must be set to "true")
- `DATABASE_URL` - Must use the **Connection Pooler** URL from Supabase

### 2. Get Correct Supabase Connection String

1. Go to **Supabase Dashboard** → Your Project → **Settings** → **Database**
2. Find **Connection Pooling** section
3. Copy the **Connection Pooler** URL (NOT the direct connection)
4. Format should be:
   ```
   postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
   Example:
   ```
   postgresql://postgres.rdjxqrrnhfbekpbsjgjk:YOUR_PASSWORD@aws-0-us-west-2.pooler.supabase.com:6543/postgres
   ```

### 3. Update Railway DATABASE_URL

1. In Railway, set `DATABASE_URL` to the pooler URL from step 2
2. Make sure password is correct (no special character encoding issues)
3. Ensure `USE_DATABASE=true` is set

### 4. Verify Connection String Format

**Correct format (pooler):**
```
postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

**Wrong format (direct connection - will fail):**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

### 5. Test Connection

After updating, Railway will auto-redeploy. Check logs for:
- ✅ "Database tables initialized" - Success
- ❌ "Tenant or user not found" - Still wrong credentials

## Quick Checklist

- [ ] `USE_DATABASE=true` in Railway
- [ ] `DATABASE_URL` uses pooler URL (contains "pooler.supabase.com")
- [ ] Password is correct (no typos)
- [ ] URL format: `postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`

## Still Not Working?

If you still get the error after fixing the connection string:

1. **Double-check password** - Copy directly from Supabase (no manual typing)
2. **Verify project reference** - Make sure `[PROJECT_REF]` matches your Supabase project
3. **Check region** - Make sure region matches (e.g., `us-west-2`, `us-east-1`)
4. **Test with psql** - Try connecting with `psql` to verify credentials work

Share the error message from Railway logs if it persists!
