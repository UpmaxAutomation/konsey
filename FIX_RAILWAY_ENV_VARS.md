# 🔧 Fix Railway Environment Variables

## Critical Issues Found

### 1. ❌ DATABASE_URL - Password Not URL-Encoded
**Current (WRONG):**
```
DATABASE_URL="postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5$$J1vbZmqX$c@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

**Fix (CORRECT):**
```
DATABASE_URL="postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:3yJ5%24%24J1vbZmqX%24c@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```
Replace `$$` with `%24%24` and `$` with `%24`

### 2. ❌ SECRET_KEY - Placeholder Value
**Current (WRONG):**
```
SECRET_KEY="your_secret_key_minimum_32_characters_here"
```

**Fix (CORRECT):**
Generate a real secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```
Or use any random 32+ character string.

### 3. ❌ ENVIRONMENT - Should be "production"
**Current:**
```
ENVIRONMENT="development"
```

**Fix:**
```
ENVIRONMENT="production"
```

### 4. ❌ SUPABASE_URL - Has Placeholder
**Current (WRONG):**
```
SUPABASE_URL="https://[PROJECT_REF].supabase.co"
```

**Fix (CORRECT):**
```
SUPABASE_URL="https://rdjxqrrnhfbekpbsjgjk.supabase.co"
```

## Quick Fix Checklist

Update these in Railway Variables:

1. ✅ `DATABASE_URL` - URL-encode password: `3yJ5%24%24J1vbZmqX%24c`
2. ✅ `SECRET_KEY` - Generate real key (32+ chars)
3. ✅ `ENVIRONMENT` - Change to `production`
4. ✅ `SUPABASE_URL` - Replace `[PROJECT_REF]` with `rdjxqrrnhfbekpbsjgjk`

## Optional (Can Keep Placeholders)

These can stay as placeholders for now:
- `GOOGLE_CLIENT_ID` - Only needed for Google OAuth
- `GOOGLE_CLIENT_SECRET` - Only needed for Google OAuth
- `OPENROUTER_API_KEY` - Users set their own keys
- `SUPABASE_ANON_KEY` - Not used by backend
- `DB_NAME`, `DB_PASSWORD`, `DB_USER` - Not used (using DATABASE_URL instead)
- `FRONTEND_URL` - Not critical
- `HTTP_PORT` - Railway sets this automatically

## After Fixing

1. Railway will auto-redeploy
2. Check logs for "Database tables initialized"
3. Try logging in
