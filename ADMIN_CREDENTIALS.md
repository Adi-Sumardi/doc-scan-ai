# 🔐 Doc Scan AI - Admin Credentials

## Default Admin User

**Username:** `admin`  
**Email:** `admin@docscan.ai`  
**Password:** `admin123`

---

## Backend Status

✅ **Running**: Port 8000  
✅ **Host**: 127.0.0.1  
✅ **Status**: healthy  

---

## Quick Access Links

### Backend
- **Health Check**: http://127.0.0.1:8000/api/health
- **API Docs**: http://127.0.0.1:8000/docs
- **Root**: http://127.0.0.1:8000/

### Frontend
- **App**: http://localhost:5173

---

## Testing Steps

### 1. Open Frontend
```
http://localhost:5173
```

### 2. Login dengan credentials di atas
- Username: `admin`
- Password: `admin123`

### 3. Jika masih "Failed to fetch":

**a) Clear Browser Cache:**
- Mac: `Cmd + Shift + Delete`
- Windows: `Ctrl + Shift + Delete`
- Pilih: Cookies, Cache, dan Site Data
- Time range: All time

**b) Hard Reload:**
- Mac: `Cmd + Shift + R`
- Windows: `Ctrl + Shift + R`

**c) Disable Browser Extensions:**
- Matikan semua extensions (terutama ad blockers, security extensions)

**d) Try Incognito/Private Mode:**
- Buka window baru dalam mode incognito
- Akses http://localhost:5173

**e) Try Different Browser:**
- Chrome, Firefox, Safari, Edge

**f) Check Browser Console:**
- Open DevTools (F12)
- Tab Console - lihat error messages
- Tab Network - cek request status

---

## Troubleshooting

### Backend Not Responding
```bash
# Check if running
lsof -i:8000

# Kill and restart
lsof -ti:8000 | xargs kill -9
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Not Running
```bash
# Check if running  
lsof -i:5173

# Kill and restart
lsof -ti:5173 | xargs kill -9
npm run dev
```

### Port Already in Use
```bash
# Kill specific port
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

---

## Development Mode Checklist

- [x] Backend running on 127.0.0.1:8000
- [x] Frontend running on localhost:5173
- [x] Admin user exists in database
- [x] CORS configured for localhost:5173
- [x] Database connected (MySQL)
- [x] Redis cache connected
- [x] All endpoints registered

---

## Common Issues & Solutions

### 1. "Failed to fetch" in Browser
**Cause:** Browser cache, service worker, or security policy  
**Solution:** Clear cache, hard reload, try incognito mode

### 2. "Network Error"
**Cause:** Backend not running or wrong port  
**Solution:** Check backend status, restart if needed

### 3. "401 Unauthorized"
**Cause:** Not logged in or token expired  
**Solution:** Login with admin credentials

### 4. "500 Internal Server Error"
**Cause:** Backend error (check logs)  
**Solution:** Check `backend/backend.log` for details

### 5. CORS Error
**Cause:** Frontend origin not in CORS whitelist  
**Solution:** Check config.py CORS settings

---

## Notes

⚠️ **IMPORTANT**: Change admin password after first login!

🔒 **Security**: Default credentials are for development only.

📝 **Logs**: Backend logs are in `backend/backend.log`

🐛 **Debug**: Set `DEBUG=True` in config.py for detailed logs

---

Last Updated: October 8, 2025
