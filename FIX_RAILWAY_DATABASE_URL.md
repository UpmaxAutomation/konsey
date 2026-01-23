# 🔧 Fix Railway DATABASE_URL - Replace Placeholders

## The Problem

Your Railway `DATABASE_URL` contains **literal placeholders** that need to be replaced:

**Current (WRONG):**
```
postgresql+asyncpg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Should be (CORRECT):**
```
postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:YOUR_ACTUAL_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

## Step-by-Step Fix

### 1. Get Your Supabase Project Reference

From your previous messages, your project reference is: **`rdjxqrrnhfbekpbsjgjk`**

### 2. Get Your Database Password

1. Go to **Supabase Dashboard**: https://supabase.com/dashboard
2. Select your project: `rdjxqrrnhfbekpbsjgjk`
3. Go to **Settings** → **Database**
4. Scroll to **Connection string** section
5. Find the **Connection Pooling** tab
6. Copy the connection string - it will show the password
7. **OR** if you don't see it, click **Reset database password** to set a new one

### 3. Update Railway DATABASE_URL

1. Go to **Railway Dashboard** → Your Service → **Variables** tab
2. Find `DATABASE_URL`
3. Replace it with:

```
postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:YOUR_ACTUAL_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Replace `YOUR_ACTUAL_PASSWORD`** with the actual password from Supabase.

### 4. Verify Format

The correct format should be:
- ✅ `postgresql+asyncpg://` (protocol)
- ✅ `postgres.rdjxqrrnhfbekpbsjgjk` (user with project ref, NO brackets)
- ✅ `:YOUR_PASSWORD@` (password, NO brackets)
- ✅ `aws-0-us-east-1.pooler.supabase.com:6543` (pooler host and port)
- ✅ `/postgres` (database name)

### 5. Important Notes

- **NO brackets** `[` `]` in the actual URL
- **NO placeholders** - use real values
- Password may contain special characters - copy it exactly from Supabase
- If password has special characters, they might need URL encoding (but usually Supabase provides it already encoded)

### 6. After Updating

1. Railway will auto-redeploy (1-2 minutes)
2. Check Railway logs for "Database tables initialized"
3. Try logging in again

## Quick Checklist

- [ ] `USE_DATABASE=true` is set in Railway
- [ ] `DATABASE_URL` has **real project reference** (rdjxqrrnhfbekpbsjgjk, not [PROJECT_REF])
- [ ] `DATABASE_URL` has **real password** (not [PASSWORD])
- [ ] URL uses pooler (contains `pooler.supabase.com:6543`)
- [ ] No brackets `[` `]` in the URL

## Still Not Working?

If you still get errors after fixing:
1. Double-check the password is correct (copy directly from Supabase)
2. Make sure there are no extra spaces in the Railway variable
3. Check Railway logs for the exact error message
