#!/bin/bash
# Enhanced startup script for the document scanner
echo "🚀 Starting Document Scanner..."

# Check if virtual environment exists
if [ ! -d "./backend/doc_scan_env" ]; then
    echo "❌ Virtual environment not found! Please run setup first."
    echo "Run: cd backend && python3 -m venv doc_scan_env && source doc_scan_env/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Start backend with virtual environment
echo "📦 Starting Backend (FastAPI) with virtual environment..."
cd backend && source doc_scan_env/bin/activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait a bit for backend to start
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start!"
    exit 1
fi

# Start frontend
echo "🌐 Starting Frontend (Vite)..."
cd .. && npm run dev &
FRONTEND_PID=$!

echo "✅ Both servers started!"
echo "🔗 Frontend: http://localhost:5173"
echo "🔗 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Features available:"
echo "  - PDF & Image OCR processing"
echo "  - Indonesian tax document parsing"
echo "  - Excel & PDF export"
echo "  - Real-time document scanning"
echo ""
echo "Press Ctrl+C to stop both servers..."

# Function to cleanup on exit
cleanup() {
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT

# Wait for processes
wait
