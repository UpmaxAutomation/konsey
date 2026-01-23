# SaaS Implementation Plan for LLM Council

## Overview
Transform LLM Council into a fully multi-tenant SaaS application where each user can:
- Register and authenticate
- Manage their own API keys (OpenRouter, OpenAI, Anthropic, Google, etc.)
- Have isolated conversations, settings, and data
- Use their own API keys for all council operations

## Current Status

### ✅ Already Implemented
1. **User Authentication System**
   - Registration (email/password, Google OAuth)
   - JWT-based authentication
   - User model in database

2. **Database Structure**
   - `User` model with relationships
   - `UserAPIKey` model (encrypted, per-user)
   - `UserSettings` model (per-user config)
   - `Conversation` model (user-scoped)
   - All data models support user isolation

3. **API Key Infrastructure**
   - Database CRUD operations for user API keys
   - Encryption/decryption functions
   - Key resolution priority: user → system → env

### ❌ Needs Implementation
1. **API Endpoints Not User-Scoped**
   - `/api/keys` - Currently uses global config
   - `/api/config` - Returns global config
   - `/api/conversations` - Not requiring auth
   - Council functions - Not using user API keys

2. **OpenRouter Integration**
   - `get_openrouter_api_key()` - Uses global config only
   - `query_model()` - Doesn't accept user_id
   - Council functions - Don't pass user context

3. **Storage Adapter**
   - `_get_user_id()` - Returns anonymous user
   - Needs to accept user_id from auth context

## Implementation Steps

### Phase 1: API Key Management (User-Scoped) ✅ DONE
- [x] Update `/api/keys` POST to store in database (user-specific)
- [x] Update `/api/keys` GET to return user-specific keys
- [x] Update `/api/keys/{provider}` DELETE to remove user keys
- [x] Add OpenRouter to valid providers list

### Phase 2: Config Endpoints (User-Scoped) ✅ DONE
- [x] Update `/api/config` GET to return user-specific settings
- [x] Update `/api/config` POST to save user-specific settings
- [x] Create default settings for new users

### Phase 3: Conversations (User-Scoped) 🔄 IN PROGRESS
- [x] Update `create_conversation` to accept user_id
- [ ] Update `get_conversation` to verify user ownership
- [ ] Update `list_conversations` to filter by user
- [ ] Update `send_message` to verify user ownership

### Phase 4: Council Functions (User API Keys) 🔄 IN PROGRESS
- [ ] Update `run_full_council` to accept user_id
- [ ] Update `query_model` to use user-specific API keys
- [ ] Update `get_openrouter_api_key` to accept user_id
- [ ] Update `has_direct_api_key` to check user keys

### Phase 5: Frontend Updates
- [ ] Ensure auth context is used in all API calls
- [ ] Update Settings UI to show user-specific keys
- [ ] Add registration/login flow if not present
- [ ] Handle authentication errors gracefully

## Key Changes Made

### 1. API Key Endpoints (backend/main.py)
```python
# Before: Global config
set_api_key(request.provider, request.api_key)

# After: User-specific database storage
if current_user:
    await db_crud.api_keys.set_user_key(db, current_user.id, request.provider, request.api_key)
```

### 2. Config Endpoints (backend/main.py)
```python
# Before: Global config
return {
    "council_models": get_council_models(),
    "chairman_model": get_chairman_model()
}

# After: User-specific from database
if current_user:
    settings = await db_crud.settings.get_by_user_id(db, current_user.id)
    council_models = settings.council_models
```

### 3. Conversations (backend/main.py)
```python
# Before: Anonymous user
conversation = await storage.create_conversation(conversation_id)

# After: User-scoped
conversation = await storage.create_conversation(conversation_id, user_id=current_user.id, db=db)
```

## Implementation Status

### ✅ Completed (Backend)

1. **API Key Endpoints - User-Scoped** ✅
   - `/api/keys` POST - Stores user-specific keys in database
   - `/api/keys` GET - Returns user-specific keys (masked)
   - `/api/keys/{provider}` DELETE - Removes user-specific keys
   - Added OpenRouter to valid providers list

2. **Config Endpoints - User-Scoped** ✅
   - `/api/config` GET - Returns user-specific settings from database
   - `/api/config` POST - Saves user-specific settings to database
   - Creates default settings for new users automatically

3. **Conversations - User-Scoped** ✅
   - `create_conversation` - Accepts user_id, stores in database
   - `get_conversation` - Verifies user ownership
   - `list_conversations` - Filters by user_id
   - `send_message` - Passes user_id to council functions

4. **Council Functions - User API Keys** ✅
   - `run_full_council` - Accepts user_id and db
   - `stage1_collect_responses` - Uses user-specific API keys
   - `stage2_collect_rankings` - Uses user-specific API keys
   - `stage3_synthesize_final` - Uses user-specific API keys
   - All stages use user-specific council models and chairman model

5. **OpenRouter Integration** ✅
   - `query_model` - Accepts user_id and db
   - `query_models_parallel` - Accepts user_id and db
   - Uses `resolve_api_key()` from database CRUD
   - Fallback chain: user key → system key → env var
   - Direct provider API keys also user-specific

### 🔄 Remaining (Frontend)

1. **Frontend Authentication Flow**
   - ✅ AuthContext exists and handles login/register
   - ✅ ProtectedRoute component exists
   - ⚠️ Need to verify all API calls include auth token
   - ⚠️ Need to handle 401 errors gracefully
   - ⚠️ Need to redirect to login when token expires

2. **Settings UI Updates**
   - ✅ Settings component exists
   - ⚠️ Verify it shows user-specific API keys
   - ⚠️ Verify it saves to user-specific endpoints
   - ⚠️ Add OpenRouter to the API keys section

3. **User Experience**
   - ⚠️ Show login/register buttons if not authenticated
   - ⚠️ Display user email/name when logged in
   - ⚠️ Handle "no API keys" state gracefully

## Testing Checklist

- [ ] User can register and login
- [ ] User can add their own OpenRouter API key
- [ ] User can add provider API keys (OpenAI, Anthropic, etc.)
- [ ] User's conversations are isolated
- [ ] User's settings are isolated
- [ ] Council uses user's API keys
- [ ] Multiple users can use the system simultaneously
- [ ] Anonymous users fall back to global config (if allowed)

## Deployment Notes

1. **Environment Variables**
   ```bash
   USE_DATABASE=true
   DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
   SECRET_KEY=your-secret-key
   ```

2. **Database Migration**
   ```bash
   alembic upgrade head
   ```

3. **Optional: Disable Anonymous Access**
   - Make all endpoints require authentication
   - Remove `get_current_user_optional` usage
   - Force login for all operations

## Benefits

1. **True Multi-Tenancy**: Each user has isolated data
2. **User API Keys**: Users bring their own API keys
3. **Cost Control**: Users pay for their own API usage
4. **Scalability**: Can support unlimited users
5. **Security**: Encrypted API keys, user isolation
6. **SaaS Ready**: Can be deployed as a service
