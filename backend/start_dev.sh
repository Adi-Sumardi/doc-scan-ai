#!/bin/bash

# Development Server Startup Script
cd "$(dirname "$0")"
# Bind explicitly to 127.0.0.1 (IPv4) instead of 0.0.0.0 to avoid IPv6 conflicts
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 --log-level info
