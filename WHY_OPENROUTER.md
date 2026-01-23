# Why Do You Need OpenRouter API Key?

## What is OpenRouter?

**OpenRouter** is a service that provides **unified access to 100+ AI models** from different providers through a single API. Instead of managing separate API keys for OpenAI, Anthropic, Google, xAI, etc., you use one OpenRouter key to access all of them.

## Why Your App Needs It

LLM Council queries multiple AI models simultaneously. Here's what happens:

```
User asks a question
    ↓
Backend (on Railway) needs to call:
    - OpenAI (GPT-4o)
    - Anthropic (Claude)
    - Google (Gemini)
    - xAI (Grok)
    - DeepSeek
    - etc.
    ↓
OpenRouter provides access to ALL of these
    ↓
Your app gets responses from multiple models
```

## How It Works in Your App

1. **User creates a conversation** → Frontend sends request to Railway backend
2. **Backend queries models** → Uses OpenRouter API key to call multiple models
3. **Models respond** → Backend processes and returns results
4. **User sees the council deliberation** → Multiple AI responses combined

## Why on Railway (Backend)?

The **backend runs on Railway** and makes the API calls to OpenRouter. That's why you need the key there:

- ✅ Frontend (Vercel) → Just displays the UI
- ✅ Backend (Railway) → Makes API calls to OpenRouter → **Needs the key!**

## Can You Use Your Own API Keys Instead?

**Yes!** You have two options:

### Option 1: Use OpenRouter (Easiest)
- One key for all models
- Simple setup
- Pay per use through OpenRouter

### Option 2: Use Your Own Provider Keys (Advanced)
Users can add their own API keys in Settings:
- OpenAI key → Uses OpenAI directly
- Anthropic key → Uses Anthropic directly
- Google key → Uses Google directly
- etc.

**But you still need OpenRouter key as a fallback** for:
- Models where user doesn't have a key
- Default system behavior
- Accessing models not available via direct APIs

## Cost

- **OpenRouter**: Pay per use (you pay for what you use)
- **Free tier**: $5 credit to start
- **Pricing**: Same as direct provider pricing (OpenRouter doesn't add markup)

## How to Get OpenRouter Key

1. Go to https://openrouter.ai
2. Sign up (free)
3. Go to Keys → Create Key
4. Copy your key: `sk-or-v1-...`
5. Add it to Railway environment variables

## Summary

**You need OpenRouter API key because:**
- ✅ Your app queries multiple AI models
- ✅ OpenRouter provides unified access to 100+ models
- ✅ Backend (Railway) makes the API calls
- ✅ Without it, the app can't query any AI models

**It's like a universal key** that unlocks access to all major AI providers!
