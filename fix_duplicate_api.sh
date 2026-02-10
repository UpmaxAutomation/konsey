#!/bin/bash
# Fix duplicate /api/ prefix in all API files
# API_BASE already includes /api, so ${API_BASE}/api/... becomes /api/api/...

cd frontend/src/api

# List of files to fix
files=(
  "templates.js"
  "projects.js"
  "ratings.js"
  "batch.js"
  "export.js"
  "config.js"
  "analytics.js"
  "integrations.js"
  "agents.js"
  "voice.js"
  "images.js"
  "tools.js"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "Fixing $file..."
    # Replace ${API_BASE}/api/ with ${API_BASE}/
    sed -i '' 's|${API_BASE}/api/|${API_BASE}/|g' "$file"
  fi
done

echo "Done! All files fixed."
