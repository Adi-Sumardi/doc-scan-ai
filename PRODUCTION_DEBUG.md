# 🐛 Production Debug: Batch ID Not Showing

## 📋 **ISSUE DESCRIPTION**

**Symptom:** Batch IDs tidak muncul di Dashboard, History, dan Documents page di production
**Environment:** Production (docscan.adilabs.id)
**Severity:** High - Core functionality broken

---

## 🔍 **ROOT CAUSE ANALYSIS**

### Possible Causes:

#### 1. **API Endpoint Issues** (Most Likely)
```
Frontend calls: GET /api/batches
Backend response: Empty array [] or error
```

**Debug Steps:**
```bash
# SSH to production server
ssh user@docscan.adilabs.id

# Check API response
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://docscan.adilabs.id/api/batches

# Expected: Array of batches
# Actual: Check what's returned
```

#### 2. **Database Connection Issues**
```python
# Backend may not connecting to database
# Check backend logs for database errors
```

**Debug Steps:**
```bash
# Check backend logs
tail -f /path/to/backend/server.log

# Check database connection
# Look for errors like:
# - "Connection refused"
# - "Authentication failed"
# - "Database not found"
```

#### 3. **File Permission Issues**
```bash
# Database file or uploads folder may have wrong permissions
```

**Check Permissions:**
```bash
# Check database file (if using SQLite)
ls -la backend/*.db
# Should be: -rw-r--r-- or -rw-rw-r--

# Check uploads folder
ls -la backend/uploads/
# Should be: drwxrwxr-x or drwxr-xr-x

# Check results folder
ls -la backend/results/
# Should be: drwxrwxr-x or drwxr-xr-x
```

#### 4. **User Authentication Issues**
```
User may not have proper permissions
Or batches belong to different user
```

**Debug Steps:**
```bash
# Check user ID in token
# vs user ID in database batches table
```

#### 5. **CORS or Nginx Configuration**
```nginx
# API requests may be blocked or misconfigured
```

**Check Nginx:**
```bash
# Check nginx config
cat /etc/nginx/sites-available/docscan

# Check nginx error log
tail -f /var/log/nginx/error.log
```

---

## 🔧 **DEBUGGING COMMANDS**

### Step 1: Check Frontend Console

Open browser DevTools (F12) and check:

```javascript
// 1. Check API calls
// Network tab > Filter: /api/batches
// Click on request > Check:
// - Status: Should be 200
// - Response: Should be array of batches

// 2. Check console errors
// Console tab > Look for errors:
// - "Failed to load data"
// - Network errors
// - CORS errors

// 3. Check token
localStorage.getItem('token')
// Should return JWT token

// 4. Manually test API
fetch('https://docscan.adilabs.id/api/batches', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
})
.then(r => r.json())
.then(d => console.log('Batches:', d))
.catch(e => console.error('Error:', e))
```

### Step 2: Check Backend Logs

```bash
# SSH to server
ssh user@docscan.adilabs.id

# Navigate to backend
cd /path/to/backend

# Check logs
tail -n 100 server.log

# Look for:
# - Database errors
# - Permission errors
# - API request logs
# - Authentication errors
```

### Step 3: Check Database

```bash
# If using SQLite
sqlite3 backend/database.db

# Check batches table
SELECT * FROM batches ORDER BY created_at DESC LIMIT 5;

# Check if batches exist
SELECT COUNT(*) FROM batches;

# Check user ownership
SELECT batch.*, user.username
FROM batches batch
JOIN users user ON batch.user_id = user.id
ORDER BY batch.created_at DESC LIMIT 5;

# Exit
.quit
```

### Step 4: Check Permissions

```bash
# Check folder permissions
ls -la backend/

# Should see:
# drwxr-xr-x uploads/
# drwxr-xr-x results/
# drwxr-xr-x exports/
# -rw-r--r-- database.db (if SQLite)

# Fix if needed:
chmod 755 backend/uploads backend/results backend/exports
chmod 644 backend/database.db  # If SQLite

# Check ownership
ls -la backend/
# Should be owned by: www-data or nginx user

# Fix if needed:
sudo chown -R www-data:www-data backend/uploads backend/results
sudo chown www-data:www-data backend/database.db  # If SQLite
```

### Step 5: Restart Services

```bash
# Restart backend (if using systemd)
sudo systemctl restart docscan-backend

# Or if using PM2
pm2 restart docscan-backend

# Or if using supervisor
sudo supervisorctl restart docscan-backend

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status docscan-backend
sudo systemctl status nginx
```

---

## 🩹 **QUICK FIXES**

### Fix 1: Permission Issues

```bash
cd /path/to/doc-scan-ai

# Set correct permissions
sudo chown -R www-data:www-data backend/
sudo chmod -R 755 backend/
sudo chmod 644 backend/database.db  # If using SQLite

# Or if using different user
sudo chown -R youruser:youruser backend/
```

### Fix 2: Database Connection

```bash
# Check if database file exists
ls -la backend/*.db

# If missing, recreate
cd backend
python -c "
from database import init_db
init_db()
print('Database initialized')
"
```

### Fix 3: Backend Not Running

```bash
# Check if backend is running
ps aux | grep python
ps aux | grep uvicorn

# If not running, start it
cd backend
source doc_scan_env/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Or use PM2
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name docscan-backend
```

### Fix 4: Nginx Configuration

```bash
# Check nginx config
sudo nginx -t

# If errors, check config
sudo nano /etc/nginx/sites-available/docscan

# Ensure API proxy is correct:
location /api/ {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# Reload nginx
sudo systemctl reload nginx
```

### Fix 5: Clear Cache & Restart

```bash
# Backend cache
cd backend
rm -rf __pycache__/
find . -type d -name "__pycache__" -exec rm -rf {} +

# Restart backend
sudo systemctl restart docscan-backend

# Frontend cache
# In browser: Ctrl+Shift+R (hard refresh)
# Or clear browser cache
```

---

## 📊 **DIAGNOSTIC SCRIPT**

Save this as `diagnose.sh`:

```bash
#!/bin/bash
echo "=== Doc Scan AI - Production Diagnostics ==="
echo ""

echo "1. Checking Backend Process..."
ps aux | grep -E "(uvicorn|python.*main)" | grep -v grep
echo ""

echo "2. Checking Nginx..."
sudo systemctl status nginx | grep -E "(Active|running)"
echo ""

echo "3. Checking Database..."
if [ -f "backend/database.db" ]; then
    echo "Database file exists"
    ls -lh backend/database.db
else
    echo "❌ Database file NOT found!"
fi
echo ""

echo "4. Checking Permissions..."
ls -la backend/uploads backend/results backend/exports 2>/dev/null || echo "Some folders missing"
echo ""

echo "5. Checking Logs (last 10 lines)..."
tail -n 10 backend/server.log 2>/dev/null || echo "No server.log found"
echo ""

echo "6. Testing API Endpoint..."
curl -I https://docscan.adilabs.id/api/health 2>/dev/null | head -n 1
echo ""

echo "7. Checking Disk Space..."
df -h | grep -E "(Filesystem|/$|/home)"
echo ""

echo "=== Diagnostics Complete ==="
```

Run with:
```bash
chmod +x diagnose.sh
./diagnose.sh
```

---

## 🎯 **MOST LIKELY CAUSES (Ranked)**

### 1. **Backend Not Running or Crashed** (80% likelihood)
- Service stopped
- Crashed due to error
- Not started after server reboot

**Fix:**
```bash
sudo systemctl restart docscan-backend
sudo systemctl enable docscan-backend  # Auto-start on boot
```

### 2. **Database Permission Error** (10% likelihood)
- www-data can't read database file
- Database file corrupted

**Fix:**
```bash
sudo chown www-data:www-data backend/database.db
sudo chmod 644 backend/database.db
```

### 3. **API Authentication Issue** (5% likelihood)
- Token expired
- Token format changed
- Backend JWT verification failing

**Fix:**
- Logout and login again
- Check backend logs for auth errors

### 4. **Database Empty** (3% likelihood)
- Batches were deleted
- Database was reset
- Using wrong database file

**Fix:**
- Check database has data
- Restore from backup if needed

### 5. **Network/CORS Issue** (2% likelihood)
- Nginx misconfigured
- CORS blocking requests

**Fix:**
- Check nginx config
- Check browser console for CORS errors

---

## 🚀 **QUICK DEPLOYMENT FIX**

If you need to quickly fix production:

```bash
# 1. SSH to server
ssh user@docscan.adilabs.id

# 2. Navigate to project
cd /path/to/doc-scan-ai

# 3. Quick fix commands
sudo systemctl restart docscan-backend
sudo systemctl restart nginx
sudo chown -R www-data:www-data backend/
sudo chmod -R 755 backend/
sudo chmod 644 backend/*.db  # If SQLite

# 4. Check status
sudo systemctl status docscan-backend
curl -H "Authorization: Bearer TOKEN" https://docscan.adilabs.id/api/batches

# 5. Check frontend
# Open browser: https://docscan.adilabs.id
# Press Ctrl+Shift+R (hard refresh)
# Check Dashboard
```

---

## 📝 **DEBUGGING CHECKLIST**

Use this checklist systematically:

- [ ] Check frontend console for errors
- [ ] Check Network tab for failed API calls
- [ ] Check backend is running: `ps aux | grep uvicorn`
- [ ] Check backend logs: `tail -f backend/server.log`
- [ ] Check database exists and has data
- [ ] Check folder permissions (755 for dirs, 644 for files)
- [ ] Check file ownership (www-data or nginx user)
- [ ] Check nginx is running: `systemctl status nginx`
- [ ] Check nginx logs: `tail -f /var/log/nginx/error.log`
- [ ] Test API manually with curl
- [ ] Check disk space: `df -h`
- [ ] Check memory: `free -h`
- [ ] Restart backend service
- [ ] Restart nginx
- [ ] Clear browser cache
- [ ] Test with different browser/incognito

---

## 🔄 **RECOVERY PROCEDURE**

If all else fails:

```bash
# 1. Backup current state
cd /path/to/doc-scan-ai
sudo tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz backend/

# 2. Stop services
sudo systemctl stop docscan-backend
sudo systemctl stop nginx

# 3. Fix permissions
sudo chown -R www-data:www-data backend/
sudo chmod -R 755 backend/
sudo chmod 644 backend/*.db

# 4. Restart services
sudo systemctl start docscan-backend
sudo systemctl start nginx

# 5. Check logs
tail -f backend/server.log &
tail -f /var/log/nginx/error.log &

# 6. Test
curl -I https://docscan.adilabs.id/api/health
```

---

## 📞 **NEED HELP?**

If issue persists after trying all fixes:

1. **Collect diagnostics:**
   ```bash
   ./diagnose.sh > diagnostics.txt
   tail -n 100 backend/server.log >> diagnostics.txt
   tail -n 100 /var/log/nginx/error.log >> diagnostics.txt
   ```

2. **Share diagnostics** with team

3. **Check database backup** and restore if needed

---

**Created:** 2025-10-11
**Status:** Troubleshooting Guide
**Priority:** High
