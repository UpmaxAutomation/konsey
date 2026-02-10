# Supabase Connection Setup

## Your Supabase Project
- **Project URL**: https://rdjxqrrnhfbekpbsjgjk.supabase.co
- **Project Reference**: `rdjxqrrnhfbekpbsjgjk`
- **API Key**: `sb_publishable_33onKUKJRyqB4QgnazFAlg_KRUu5KGz` (publishable key)

## Important: Database Password Needed

The API key you provided is a **publishable key** for Supabase client SDK. However, for direct PostgreSQL connections (which this project uses), we need the **database password**.

### How to Find Your Database Password

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project: `rdjxqrrnhfbekpbsjgjk`
3. Go to **Settings** → **Database**
4. Scroll down to **Connection string** section
5. Look for **URI** or **Connection pooling** tab
6. The password is shown in the connection string, or you can:
   - Click **Reset database password** if you don't remember it
   - Copy the connection string and extract the password

### Connection String Format

Once you have the password, the connection string will be:

```
postgresql+asyncpg://postgres:[YOUR-DATABASE-PASSWORD]@db.rdjxqrrnhfbekpbsjgjk.supabase.co:5432/postgres
```

## Update Your .env File

After getting the database password, update your `.env` file:

```bash
USE_DATABASE=true
DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.rdjxqrrnhfbekpbsjgjk.supabase.co:5432/postgres
```

## Alternative: Connection Pooling (Recommended for Production)

Supabase also offers connection pooling. Use port `6543` instead of `5432`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

For your project:
```bash
DATABASE_URL=postgresql+asyncpg://postgres.rdjxqrrnhfbekpbsjgjk:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

(Check your Supabase dashboard for the exact pooler URL)

## After Updating .env

1. Restart your backend server
2. The database tables will be created automatically on first connection
3. Verify connection by checking backend logs

## Note About API Keys

The publishable key (`sb_publishable_...`) is for:
- Supabase client SDK (JavaScript/TypeScript)
- Frontend authentication
- Real-time subscriptions

This project doesn't use the Supabase client SDK, so you don't need to configure the API key in the frontend. We only need the database password for the PostgreSQL connection.
