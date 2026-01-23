# 🔧 Fix Password URL Encoding

## The Issue

Your password `3yJ5$$J1vbZmqX$c` contains `$` characters which are special in URLs. These need to be URL-encoded.

## Solution: URL-Encode the Password

### Step 1: Encode the Password

**Original password**: `3yJ5$$J1vbZmqX$c`  
**URL-encoded**: `3yJ5%24%24J1vbZmqX%24c`

Each `$` becomes `%24`:
- `$$` → `%24%24`
- `$` → `%24`

### Step 2: Update Railway DATABASE_URL

Go to **Railway Dashboard** → Your Service → **Variables** tab

**Replace the current DATABASE_URL with:**

```
postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5%24%24J1vbZmqX%24c@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Key changes:**
- `3yJ5$$J1vbZmqX$c` → `3yJ5%24%24J1vbZmqX%24c`

### Step 3: Verify

1. Make sure `USE_DATABASE=true` is set
2. Save the variable
3. Wait for Railway to redeploy (1-2 minutes)
4. Check Railway logs for "Database tables initialized"
5. Try logging in

## Why This Is Needed

URLs have special characters that must be encoded:
- `$` → `%24`
- `@` → `%40` (but this is already in the host part, so it's fine)
- `#` → `%23`
- `%` → `%25`
- `&` → `%26`
- `+` → `%2B`
- `=` → `%3D`

The `$` in your password is being interpreted as a URL special character, causing authentication to fail.

## Alternative: Reset Password in Supabase

If URL encoding doesn't work, you can reset your database password in Supabase to one without special characters:

1. Go to Supabase Dashboard → Settings → Database
2. Click "Reset database password"
3. Generate a new password (copy it)
4. Update Railway DATABASE_URL with the new password
