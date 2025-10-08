# 🚨 CORS Error - Solution Guide

## Problem
```
Access to XMLHttpRequest at 'http://localhost:8000/api/login' from origin 'http://localhost:5173' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Root Cause
Backend server tidak running atau crash karena bcrypt compatibility issue.

## ✅ Solution - Start Backend Server

### Method 1: Gunakan Script Startup (RECOMMENDED)

```bash
cd backend
./start_backend.sh
```

Script ini akan:
1. Kill semua process lama
2. Clear port 8000
3. Start backend dengan konfigurasi yang benar

### Method 2: Manual Start

```bash
cd backend

# Kill existing processes
pkill -9 uvicorn
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Wait
sleep 3

# Start backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: Background Mode

```bash
cd backend
nohup ./start_backend.sh > backend.log 2>&1 &
```

## ✅ Verify Backend is Running

### 1. Check Port
```bash
lsof -i:8000
```

Should show Python/uvicorn process listening on port 8000.

### 2. Test Health Endpoint
```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "status": "healthy",
  "service": "doc-scan-ai",
  "database": "connected",
  "cache": {"redis_connected": true}
}
```

### 3. Test CORS
```bash
curl -X OPTIONS http://localhost:8000/api/login \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -i | grep -i "access-control"
```

Should show:
```
access-control-allow-origin: http://localhost:5173
access-control-allow-methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
access-control-allow-credentials: true
```

## 🔐 Test Login

### Via curl:
```bash
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Should return access_token.

### Via Browser:
1. Open http://localhost:5173
2. Login with:
   - Username: `admin`
   - Password: `admin123`

## 🐛 Troubleshooting

### Backend Won't Start

**Error: "Address already in use"**
```bash
# Force kill all processes
pkill -9 python
pkill -9 uvicorn
lsof -ti:8000 | xargs kill -9

# Try again
./start_backend.sh
```

**Error: "Could not import module main"**
```bash
# Check you're in backend directory
cd /Users/yapi/Adi/App-Dev/doc-scan-ai/backend
pwd

# Verify Python environment
which python
python --version  # Should be 3.10.13

# Try again
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### CORS Still Not Working

1. **Hard reload browser**: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

2. **Clear browser cache completely**:
   - Chrome: Settings → Privacy → Clear browsing data
   - Select: Cookies, Cache, Site data
   - Time range: All time

3. **Disable browser extensions** (especially ad blockers)

4. **Try incognito/private mode**

5. **Try different browser**

### Login Returns 500 Error

This is usually bcrypt password hashing issue.

**Check backend logs**:
```bash
tail -50 backend/backend.log
```

Look for bcrypt errors.

**Solution**: Backend already updated with fix. Just restart:
```bash
cd backend
./start_backend.sh
```

## 📋 Complete Testing Checklist

- [ ] Backend running (check with `lsof -i:8000`)
- [ ] Health endpoint OK (`curl http://localhost:8000/api/health`)
- [ ] CORS headers present (check with curl OPTIONS request)
- [ ] Login endpoint works (test with curl)
- [ ] Frontend can connect (open http://localhost:5173)
- [ ] Can login with admin credentials
- [ ] No CORS errors in browser console

## 🎯 Quick Commands

```bash
# Check backend status
lsof -i:8000

# Check frontend status  
lsof -i:5173

# Kill and restart backend
cd backend
pkill -9 uvicorn && sleep 2 && ./start_backend.sh

# Kill and restart frontend
pkill -9 node && sleep 2 && npm run dev

# View backend logs
tail -f backend/backend.log

# Test all endpoints
curl http://localhost:8000/docs
```

## 🔧 Files Modified

1. `/backend/auth.py` - Fixed bcrypt password truncation
2. `/backend/start_backend.sh` - New robust startup script
3. `/backend/main.py` - CORS middleware properly configured

## ⚠️ Important Notes

- Default port: `8000` (backend), `5173` (frontend)
- Admin credentials: `admin` / `admin123`
- Always start backend BEFORE frontend
- Backend must bind to `0.0.0.0` (not `127.0.0.1`) for proper CORS
- CORS origins include both `localhost:5173` and `127.0.0.1:5173`

---

Last Updated: October 8, 2025
