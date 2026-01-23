# 🔧 AI Council Loading/Reset Issue - Debug Guide

## Problem

AI Council shows "loading" then resets without showing an error message.

## Possible Causes

### 1. Missing API Key (Most Likely)
- User doesn't have OpenRouter API key set
- All models fail → Council returns error → Frontend resets

### 2. All Models Failed
- API key invalid or expired
- Network issues
- Rate limiting

### 3. Database Connection Issue
- Database session expired during council process
- Transaction rollback

### 4. Streaming Error
- SSE connection dropped
- Error not properly sent to frontend

## Debug Steps

### Step 1: Check API Key

1. Go to Settings → API Keys
2. Verify OpenRouter API key is set
3. If not set, add your OpenRouter API key
4. Save and try again

### Step 2: Check Browser Console

1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for error messages:
   - "Stream error: ..."
   - "Failed to send message: ..."
   - "No OpenRouter API key available..."

### Step 3: Check Backend Logs

**Local:**
```bash
# Check backend terminal output
# Look for:
# - "No OpenRouter API key available"
# - "Error querying model"
# - "All models failed to respond"
```

**Railway (Production):**
1. Go to Railway dashboard
2. Click on your service
3. Go to "Logs" tab
4. Look for error messages

### Step 4: Check Debug Logs

```bash
# Check debug log file
cat /Users/sezars/llm-council/.cursor/debug.log | tail -50

# Look for:
# - "no_openrouter_key"
# - "all_models_failed"
# - "query_model_exception"
# - "council_stream_exception"
```

## Quick Fixes

### Fix 1: Set API Key

1. Go to Settings → API Keys
2. Enter your OpenRouter API key
3. Click "Save"
4. Try sending a message again

### Fix 2: Check API Key Validity

1. Test your API key at https://openrouter.ai/keys
2. Verify it's active and has credits
3. If invalid, generate a new key

### Fix 3: Check Network

1. Verify internet connection
2. Check if OpenRouter API is accessible
3. Try again after a few seconds

## Error Messages

### "All models failed to respond"
- **Cause**: No API key or all models failed
- **Fix**: Set OpenRouter API key in Settings

### "No OpenRouter API key available"
- **Cause**: API key not set
- **Fix**: Go to Settings → API Keys → Set OpenRouter key

### "Stream error: ..."
- **Cause**: Various (network, API, database)
- **Fix**: Check error message details in console

## What I've Added

1. **Better Error Messages**: More descriptive error messages
2. **Error Display**: Errors now show in the chat instead of just resetting
3. **Debug Logging**: Comprehensive logging to track issues
4. **API Key Detection**: Logs when API key is missing

## Next Steps

1. **Reproduce the issue** (send a message in Council mode)
2. **Check the logs** (browser console + backend logs)
3. **Share the error message** you see
4. **I'll fix the specific issue** based on the logs

## Test After Fix

1. Set your OpenRouter API key in Settings
2. Create a new conversation
3. Send a message
4. Verify it works
