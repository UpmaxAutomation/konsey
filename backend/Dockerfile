# Backend Dockerfile for LLM Council
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install --no-cache-dir uv

# Copy dependency files from root context
COPY pyproject.toml /pyproject.toml

# Install Python dependencies
RUN uv pip install --system -e /

# Copy application code from backend directory
COPY backend/ .

# Create data directories
RUN mkdir -p /app/data/uploads /app/data/conversations

# Expose port
EXPOSE 8001

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
