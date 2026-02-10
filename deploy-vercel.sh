#!/bin/bash
# Vercel Deployment Script
# Run this from the project root

set -e

echo "🚀 Deploying to Vercel..."
echo ""

# Check if logged in
if ! vercel whoami &>/dev/null; then
    echo "❌ Not logged in to Vercel"
    echo "📝 Please run: vercel login"
    echo "   Then run this script again"
    exit 1
fi

# Get Railway URL from user
read -p "Enter your Railway URL (e.g., https://xxx.up.railway.app): " RAILWAY_URL

if [ -z "$RAILWAY_URL" ]; then
    echo "❌ Railway URL is required"
    exit 1
fi

echo ""
echo "📦 Deploying frontend to Vercel..."
echo "   Railway URL: $RAILWAY_URL"
echo ""

cd frontend

# Deploy with environment variable
vercel \
    --yes \
    --prod \
    --env VITE_API_URL="$RAILWAY_URL" \
    --force

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Copy your Vercel URL from above"
echo "2. Go to Railway → Variables"
echo "3. Add: CORS_ORIGINS=https://your-vercel-url.vercel.app"
echo "4. Test your app!"
