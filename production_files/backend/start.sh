#!/bin/bash
# Simple startup script for Doc-Scan-AI Backend

echo "🚀 Starting Doc-Scan-AI Backend..."

# Check if virtual environment exists
if [ ! -d "doc_scan_env" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv doc_scan_env && source doc_scan_env/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Start server using Python script
python3 start_with_env.py
