# 🚀 Production Update Guide - NGINX Setup

## Quick Update Commands (Copy-Paste Ready)

```bash
# Connect to server
ssh docScan@your-server-ip

# Navigate to project
cd ~/doc-scan-ai

# Run automated update script (RECOMMENDED)
./update-production.sh
```

---

## 📋 Manual Update Steps (If Script Doesn't Work)

### Step 1: Backup

```bash
cd ~/doc-scan-ai
backup_dir=~/backups/doc-scan-ai-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $backup_dir
cp -r backend/ $backup_dir/
cp -r src/ $backup_dir/
cp -r dist/ $backup_dir/ 2>/dev/null || true
echo "✅ Backup: $backup_dir"
```

### Step 2: Pull Latest Code

```bash
git stash  # if you have local changes
git pull origin master
git log -1 --oneline  # verify new commit
```

### Step 3: Update Python Dependencies

```bash
cd ~/doc-scan-ai/backend

# Activate venv if you use it
source venv/bin/activate

# Update packages
pip install -r requirements.txt

cd ..
```

### Step 4: Build Frontend (CRITICAL for Nginx!)

```bash
cd ~/doc-scan-ai

# Install/update Node packages
npm install

# Build frontend with Vite
npm run build

# Verify dist/ folder exists
ls -la dist/
du -sh dist/  # Check size

# You should see:
# dist/
# ├── index.html
# ├── assets/
# │   ├── index-xxxxx.js
# │   └── index-xxxxx.css
# └── ...
```

### Step 5: Reload Nginx

```bash
# Test Nginx config first
sudo nginx -t

# If OK, reload
sudo nginx -s reload

# Verify Nginx is running
sudo systemctl status nginx
```

### Step 6: Restart Backend

```bash
# If using PM2
pm2 restart doc-scan-backend
pm2 status

# Or if using systemd
sudo systemctl restart doc-scan-backend
sudo systemctl status doc-scan-backend
```

### Step 7: Verify Everything Works

```bash
# 1. Check backend API
curl http://localhost:8000/api/health

# Should return: {"status":"healthy"}

# 2. Check frontend (replace with your domain)
curl -I https://your-domain.com

# Should return: HTTP/1.1 200 OK

# 3. Check logs
pm2 logs doc-scan-backend --lines 20
sudo tail -f /var/log/nginx/error.log
```

---

## 🧪 Testing After Update

### 1. Open browser and test:
- Go to your domain: `https://your-domain.com`
- **Clear browser cache**: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)

### 2. Upload Rekening Koran
- [ ] Upload rekening koran from any bank (BCA, Mandiri, BNI, etc)
- [ ] Export to Excel - verify ALL transactions appear
- [ ] Export to PDF - verify complete data

### 3. Upload Invoice
- [ ] Upload any invoice (commercial, service, etc)
- [ ] Export to Excel - verify vendor, customer, items
- [ ] Export to PDF - verify complete details

### 4. Upload Faktur Pajak
- [ ] Upload faktur pajak
- [ ] Export to PDF
- [ ] Check page 2 (Faktur Masukan)
- [ ] Verify "Email" field shows buyer email

---

## 🔧 Troubleshooting

### Issue: Frontend shows OLD version after update

**Cause**: Browser cache or Nginx cache

**Solution**:
```bash
# 1. Rebuild frontend
cd ~/doc-scan-ai
npm run build

# 2. Clear Nginx cache (if configured)
sudo rm -rf /var/cache/nginx/*

# 3. Reload Nginx
sudo nginx -s reload

# 4. In browser: Hard refresh (Ctrl+F5 or Cmd+Shift+R)
```

### Issue: "dist" folder not found

**Cause**: Build failed

**Solution**:
```bash
# Check Node version (should be >= 16)
node --version

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Try build again
npm run build

# Check for errors
```

### Issue: Nginx serves 404 or 403

**Cause**: Wrong root path in Nginx config

**Solution**:
```bash
# 1. Check Nginx config
sudo nano /etc/nginx/sites-available/doc-scan-ai

# 2. Verify root path points to dist/
# Should have:
server {
    ...
    root /home/docScan/doc-scan-ai/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
    ...
}

# 3. Test config
sudo nginx -t

# 4. Reload if OK
sudo nginx -s reload

# 5. Check permissions
ls -la ~/doc-scan-ai/dist/
# Should be readable by nginx user (usually www-data)

# Fix permissions if needed
sudo chmod -R 755 ~/doc-scan-ai/dist/
```

### Issue: Backend not responding

**Cause**: Backend service crashed or not started

**Solution**:
```bash
# Check if backend is running
pm2 list

# If not running, start it
cd ~/doc-scan-ai/backend
pm2 start main.py --name doc-scan-backend --interpreter python3

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Check logs
pm2 logs doc-scan-backend --lines 50

# Common fixes:
# - Missing .env file
# - Missing dependencies
# - Port 8000 already in use
```

### Issue: Smart Mapper not working

**Cause**: OPENAI_API_KEY not set or wrong

**Solution**:
```bash
# Check .env file
cat ~/doc-scan-ai/backend/.env | grep OPENAI

# Should have:
# OPENAI_API_KEY=sk-proj-...
# ENABLE_SMART_MAPPER=true

# If missing, add it:
nano ~/doc-scan-ai/backend/.env

# Restart backend
pm2 restart doc-scan-backend
```

---

## 🔄 Rollback Plan

If something goes wrong, rollback:

```bash
# 1. Stop services
pm2 stop doc-scan-backend

# 2. Restore from backup
cd ~/doc-scan-ai
backup_dir=~/backups/doc-scan-ai-backup-YYYYMMDD-HHMMSS  # your backup folder
cp -r $backup_dir/backend/* backend/
cp -r $backup_dir/src/* src/
cp -r $backup_dir/dist/* dist/ 2>/dev/null || true

# 3. Reload Nginx
sudo nginx -s reload

# 4. Restart backend
pm2 restart doc-scan-backend

# Or rollback git commit
git reset --hard HEAD~1
npm run build
sudo nginx -s reload
pm2 restart all
```

---

## 📊 Nginx Configuration Reference

**Example Nginx config for doc-scan-ai:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend (Vite build output)
    root /home/docScan/doc-scan-ai/dist;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend routes (SPA)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for large file uploads
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # Static assets caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # File upload size limit
    client_max_body_size 50M;
}
```

**Save to**: `/etc/nginx/sites-available/doc-scan-ai`

**Enable**:
```bash
sudo ln -s /etc/nginx/sites-available/doc-scan-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo nginx -s reload
```

---

## ✅ Success Checklist

Update is successful when:

- ✅ `npm run build` completes without errors
- ✅ `dist/` folder contains index.html and assets/
- ✅ Nginx reloaded without errors
- ✅ Backend responding at http://localhost:8000/api/health
- ✅ Frontend accessible at https://your-domain.com
- ✅ Can upload and process documents
- ✅ Excel and PDF exports working
- ✅ Smart Mapper AI working (check logs)

---

## 📞 Quick Reference Commands

```bash
# Check services status
pm2 status
sudo systemctl status nginx

# View logs
pm2 logs doc-scan-backend
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Restart services
pm2 restart doc-scan-backend
sudo nginx -s reload

# Test endpoints
curl http://localhost:8000/api/health
curl -I https://your-domain.com

# Check disk space
df -h
du -sh ~/doc-scan-ai/dist

# Check running processes
ps aux | grep uvicorn
ps aux | grep nginx
```

---

**Last Updated**: October 11, 2025
**For**: Nginx + PM2 + Python Backend Setup
