# API Key Policy - User-Owned Keys

## Current System Behavior

### ✅ What Changed

1. **Removed Environment Variable Fallback**
   - `OPENROUTER_API_KEY` in Railway/Render is **NO LONGER REQUIRED**
   - System no longer falls back to environment variables automatically

2. **Users Must Set Their Own Keys**
   - Each user sets their API keys in Settings
   - Users pay for their own usage
   - No automatic fallback to system key

3. **Admin Can Set System Key (Optional)**
   - Admin can set system-wide keys in Admin Panel
   - System key is ONLY used if:
     - User doesn't have their own key set
     - AND admin has explicitly set a system key
   - This allows you to offer a "free tier" if you want

### 🔄 API Key Resolution Flow

```
User makes request
    ↓
1. Check user's own key ✅ (if set, use it - user pays)
    ↓ (if not found)
2. Check system key (admin-set) ✅ (if admin set it, use it - you pay)
    ↓ (if not found)
3. Request fails ❌ (user must set their own key)
```

## Deployment

### Railway Environment Variables

**Required:**
- `SECRET_KEY` - JWT secret
- `USE_DATABASE=true` - Enable database
- `DATABASE_URL` - Supabase connection string
- `ENVIRONMENT=production`
- `CORS_ORIGINS` - Your Vercel URL

**NOT Required:**
- ~~`OPENROUTER_API_KEY`~~ - **Removed!** Set in Admin Panel if needed

### After Deployment

1. **Users**: Must set their own API keys in Settings
2. **Admin**: Can optionally set system-wide key in Admin Panel → System API Keys tab

## Admin Panel Features

### System API Keys Tab

- View all system API keys (masked)
- Set system-wide keys for any provider
- Delete system keys
- Keys are encrypted in database

### When System Key is Used

- User doesn't have their own key
- AND admin has set a system key
- System key is used as fallback
- **You pay** for that usage

## User Experience

### New User Flow

1. User registers
2. User tries to create conversation
3. **If no API key set**: Error message prompts user to set key in Settings
4. User goes to Settings → API Keys → Sets their OpenRouter key
5. User can now use the app (they pay for usage)

### User With Key

1. User has set their API key in Settings
2. All requests use **their key** (they pay)
3. System key is never used

## Benefits

✅ **Cost Control**: Users pay for their own usage
✅ **No Surprises**: You only pay if you explicitly set a system key
✅ **Flexibility**: Admin can optionally offer "free tier" by setting system key
✅ **Transparency**: Users know they're using their own keys

## Future: Billing System

When you're ready to charge users for using your system key:

1. Track usage when system key is used
2. Implement billing/subscription system
3. Charge users for system key usage
4. Keep user-owned keys free (they pay providers directly)

## Summary

- ✅ Users set their own keys (required)
- ✅ Admin can set system key (optional, in Admin Panel)
- ✅ No environment variable fallback
- ✅ Clear cost attribution (user pays or you pay)
