# Supabase Connection Issue

## Problem
The hostname `db.rdjxqrrnhfbekpbsjgjk.supabase.co` is not resolving.

## Solution: Get the Correct Connection String

The hostname format might be different. Please get the exact connection string from your Supabase dashboard:

### Steps:
1. Go to: https://supabase.com/dashboard/project/rdjxqrrnhfbekpbsjgjk
2. Click **Settings** → **Database**
3. Scroll to **Connection string** section
4. Select **URI** tab (not Session mode)
5. Copy the connection string - it should look like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@[HOSTNAME]:5432/postgres
   ```

### Common Supabase Hostname Formats:
- Direct: `db.[project-ref].supabase.co` (port 5432)
- Pooler: `aws-0-[region].pooler.supabase.com` (port 6543)
- Sometimes: `[project-ref].supabase.co` (without `db.` prefix)

### Alternative: Use Connection Pooling (Recommended)

In Supabase dashboard → Settings → Database → Connection string:
- Select **Transaction** mode (connection pooling)
- Copy that connection string
- It will use port 6543 and a different hostname

## Once You Have the Correct Connection String:

Update your `.env` file:
```bash
DATABASE_URL=postgresql+asyncpg://[THE-EXACT-CONNECTION-STRING-FROM-SUPABASE]
```

Make sure to:
1. Replace `postgresql://` with `postgresql+asyncpg://` (for asyncpg driver)
2. Keep the password as-is (or URL-encode special characters)
3. Use the exact hostname from Supabase dashboard
