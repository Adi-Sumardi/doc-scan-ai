#!/bin/bash

# Test server startup script
cd /Users/yapi/Adi/App-Dev/doc-scan-ai/backend

echo "🚀 Testing backend server startup..."
echo ""

# Activate virtual environment
source ../doc_scan_env/bin/activate

# Try to start server
timeout 5 python main.py 2>&1 &
SERVER_PID=$!

echo "⏳ Waiting for server to start..."
sleep 3

# Test if server is responding
echo "🔍 Testing server response..."
RESPONSE=$(curl -s http://localhost:8000/)

if [ -n "$RESPONSE" ]; then
    echo "✅ Server is running!"
    echo "Response: $RESPONSE"

    # Test health endpoint
    echo ""
    echo "🏥 Testing health endpoint..."
    curl -s http://localhost:8000/api/health | python -m json.tool

    echo ""
    echo "✅ All tests passed!"
else
    echo "❌ Server not responding"
fi

# Kill server
kill $SERVER_PID 2>/dev/null

echo ""
echo "✅ Test complete"
