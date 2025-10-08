#!/bin/bash

# Robust Backend Startup Script
set -e

cd "$(dirname "$0")"

echo "🔍 Checking for existing processes..."

# Kill all uvicorn processes
pkill -9 uvicorn 2>/dev/null || true

# Kill all processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait for port to be free
sleep 3

echo "🚀 Starting backend server..."

# Start with Python from pyenv
/Users/yapi/.pyenv/versions/3.10.13/bin/python -m uvicorn main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info

