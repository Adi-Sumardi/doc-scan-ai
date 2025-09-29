# 🚀 Production Deployment Guide

## Quick Start Production

### 1. Frontend Setup
```bash
# Install dependencies
npm install

# Build for production
npm run build

# Serve production build
npm run serve
# or
npm start
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv doc_scan_env

# Activate virtual environment
source doc_scan_env/bin/activate  # Linux/Mac
# doc_scan_env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Environment Setup
Create `.env` file in backend directory:
```env
DATABASE_URL=sqlite:///./app.db
SECRET_KEY=your-secret-key-here
MAX_FILE_SIZE=10485760
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
```

## Production URLs
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Production Ready ✅
- Test files removed
- Development files cleaned
- Cache files cleared
- Package.json fixed
- Production scripts added
- Documentation updated

Ready for deployment! 🎉