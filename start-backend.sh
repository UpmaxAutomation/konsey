#!/bin/bash

# Start backend server with proper environment loading
cd "$(dirname "$0")"

# Load .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start server
uv run uvicorn backend.main:app --reload --port 8001 --host 127.0.0.1
