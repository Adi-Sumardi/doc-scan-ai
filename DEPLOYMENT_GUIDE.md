# 🚀 Deployment Guide - v2.0.0 to Production

## Overview
Guide lengkap untuk deploy AI DocScan v2.0.0 dari local → GitHub → Production Server

---

## 📋 **PRE-DEPLOYMENT CHECKLIST**

Sebelum deploy, pastikan:

- [x] Semua changes sudah di-commit
- [x] Build berhasil: `npm run build` ✅
- [x] No TypeScript errors ✅
- [x] Git status clean ✅
- [ ] Testing done locally
- [ ] Backup production database
- [ ] Inform team about deployment

---

## 🔄 **DEPLOYMENT STEPS**

### **PART 1: Push ke GitHub** (Di Local Mac)

```bash
# 1. Pastikan di directory project
cd /Users/yapi/Adi/App-Dev/doc-scan-ai

# 2. Check status
git status
# Output: "nothing to commit, working tree clean"

# 3. Check commit history
git log --oneline -5

# 4. Push ke GitHub
git push origin master

# atau jika branch main:
# git push origin main
```

**Expected output:**
```
Enumerating objects: 20, done.
Counting objects: 100% (20/20), done.
Delta compression using up to 8 threads
Compressing objects: 100% (15/15), done.
Writing objects: 100% (15/15), 25.45 KiB | 3.18 MiB/s, done.
Total 15 (delta 10), reused 0 (delta 0)
To github.com:username/doc-scan-ai.git
   45d90ce..c586bec  master -> master
```

✅ **Verify di GitHub:**
- Open: https://github.com/YOUR_USERNAME/doc-scan-ai
- Check latest commit ada
- Check files updated: PRODUCTION_DEBUG.md, diagnose.sh, dll

---

### **PART 2: Connect ke Production Server** (Via Termius/SSH)

#### Option A: Using Termius (Recommended)

1. **Buka Termius**
2. **Connect ke server:**
   - Host: `docscan.adilabs.id` atau IP server
   - Username: `yapi` atau username Anda
   - Password/SSH Key: sesuai setup

3. **Akan masuk ke terminal server**

#### Option B: Using Terminal SSH

```bash
# Di Mac Terminal
ssh yapi@docscan.adilabs.id
# Enter password

# Atau jika pakai SSH key:
ssh -i ~/.ssh/id_rsa yapi@docscan.adilabs.id
```

---

### **PART 3: Backup Production** (Di Server via Termius)

⚠️ **PENTING:** Selalu backup sebelum update!

```bash
# 1. Navigate ke project
cd /home/yapi/doc-scan-ai
# atau
cd ~/doc-scan-ai

# 2. Create backup directory
mkdir -p ~/backups

# 3. Backup database & backend
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
sudo tar -czf ~/backups/docscan_backup_$TIMESTAMP.tar.gz \
    backend/ \
    --exclude='backend/doc_scan_env' \
    --exclude='backend/__pycache__'

# 4. Verify backup created
ls -lh ~/backups/
```

✅ **Backup created:** `docscan_backup_20251011_140530.tar.gz`

---

### **PART 4: Pull Changes dari GitHub** (Di Server)

```bash
# 1. Make sure in project directory
cd ~/doc-scan-ai

# 2. Check current branch
git branch

# 3. Stash any local changes (jika ada)
git stash

# 4. Pull latest code
git pull origin master
# atau
git pull origin main
```

**Expected output:**
```
remote: Enumerating objects: 20, done.
remote: Counting objects: 100% (20/20), done.
remote: Compressing objects: 100% (15/15), done.
remote: Total 15 (delta 10), reused 15 (delta 10), pack-reused 0
Unpacking objects: 100% (15/15), done.
From github.com:username/doc-scan-ai
   45d90ce..c586bec  master     -> origin/master
Updating 45d90ce..c586bec
Fast-forward
 BUGFIXES.md              | 362 ++++++++++++++++++++++++
 PRODUCTION_DEBUG.md      | 450 ++++++++++++++++++++++++++++
 diagnose.sh              | 315 ++++++++++++++++++++
 src/context/AuthContext.tsx | 80 +++---
 ...
 16 files changed, 1861 insertions(+), 101 deletions(-)
```

✅ **Code updated!**

---

### **PART 5: Run Diagnostic First** (Sebelum Update)

```bash
# 1. Make script executable
chmod +x diagnose.sh

# 2. Run diagnostic
./diagnose.sh

# 3. Save output for comparison
./diagnose.sh > before_update.txt
```

Baca output dan catat masalah yang ada.

---

### **PART 6: Deploy Update** (Di Server)

#### Option A: Using Update Script (Recommended)

```bash
# 1. Make script executable
chmod +x update-production.sh

# 2. Run update script
sudo ./update-production.sh

# Script will:
# - Create backup (double backup!)
# - Pull latest code (already done)
# - Install dependencies
# - Build frontend
# - Fix permissions
# - Restart services
# - Run health checks
```

#### Option B: Manual Update (Step by Step)

```bash
# 1. Install frontend dependencies
npm install

# 2. Build frontend
npm run build

# 3. Update backend dependencies
cd backend
source doc_scan_env/bin/activate
pip install -r requirements.txt --quiet
cd ..

# 4. Fix permissions
sudo chown -R www-data:www-data backend/
# atau jika nginx user:
# sudo chown -R nginx:nginx backend/

sudo chmod -R 755 backend/
sudo chmod 644 backend/*.db

# 5. Restart backend service
sudo systemctl restart docscan-backend
sudo systemctl status docscan-backend

# 6. Restart nginx
sudo systemctl restart nginx
sudo systemctl status nginx

# 7. Wait for services to start
sleep 3
```

---

### **PART 7: Verify Deployment** (Di Server)

```bash
# 1. Run diagnostic again
./diagnose.sh

# 2. Check backend API
curl http://localhost:8000/api/health
# Should return: {"status":"healthy"}

# 3. Check production URL
curl https://docscan.adilabs.id/api/health
# Should return: {"status":"healthy"}

# 4. Check batches endpoint (need token)
# Get token from browser localStorage first
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/batches

# 5. Check logs for errors
tail -n 50 backend/server.log
# atau
sudo journalctl -u docscan-backend -n 50
```

---

### **PART 8: Test in Browser**

1. **Clear browser cache:**
   - Chrome: `Ctrl+Shift+Del` → Clear cache
   - Or hard refresh: `Ctrl+Shift+R`

2. **Open production:**
   - URL: https://docscan.adilabs.id

3. **Test critical features:**
   - [ ] Login works
   - [ ] Dashboard shows batches ✅
   - [ ] History page shows data ✅
   - [ ] Documents page shows data ✅
   - [ ] Upload new document works
   - [ ] Real-time processing works
   - [ ] Export works (Excel/PDF)
   - [ ] Edit data works

4. **Check browser console (F12):**
   - No errors should appear
   - API calls successful (200 status)
   - No CORS errors

---

## 🐛 **TROUBLESHOOTING DEPLOYMENT**

### Issue 1: "Permission denied" saat git pull

```bash
# Fix ownership
sudo chown -R yapi:yapi ~/doc-scan-ai

# Try pull again
git pull origin master
```

### Issue 2: Backend tidak restart

```bash
# Check service status
sudo systemctl status docscan-backend

# Check logs
sudo journalctl -u docscan-backend -n 50

# Manual restart
sudo systemctl restart docscan-backend

# Check if running
ps aux | grep uvicorn
```

### Issue 3: Frontend tidak update

```bash
# Rebuild frontend
cd ~/doc-scan-ai
npm install
npm run build

# Clear browser cache
# Ctrl+Shift+R di browser
```

### Issue 4: Batches masih tidak muncul

```bash
# Run full diagnostic
./diagnose.sh

# Check database
sqlite3 backend/database.db "SELECT COUNT(*) FROM batches;"

# Check permissions
ls -la backend/database.db

# Fix if needed
sudo chown www-data:www-data backend/database.db
sudo chmod 644 backend/database.db
sudo systemctl restart docscan-backend
```

### Issue 5: 502 Bad Gateway

```bash
# Backend probably not running
sudo systemctl status docscan-backend

# Restart
sudo systemctl restart docscan-backend

# Check logs
sudo journalctl -u docscan-backend -f
```

---

## 🔄 **ROLLBACK PROCEDURE**

Jika ada masalah serius, rollback:

```bash
# 1. Stop services
sudo systemctl stop docscan-backend
sudo systemctl stop nginx

# 2. Restore from backup
cd ~
tar -xzf backups/docscan_backup_TIMESTAMP.tar.gz -C doc-scan-ai/

# 3. Fix permissions
cd doc-scan-ai
sudo chown -R www-data:www-data backend/
sudo chmod -R 755 backend/

# 4. Restart services
sudo systemctl start docscan-backend
sudo systemctl start nginx

# 5. Verify
curl http://localhost:8000/api/health
```

---

## 📊 **DEPLOYMENT CHECKLIST**

### Pre-Deployment
- [x] Code tested locally
- [x] Build successful
- [x] All commits pushed to GitHub
- [ ] Team notified
- [ ] Backup created

### During Deployment
- [ ] Connected to production server
- [ ] Backup created
- [ ] Code pulled from GitHub
- [ ] Dependencies updated
- [ ] Frontend built
- [ ] Permissions fixed
- [ ] Services restarted
- [ ] Health checks passed

### Post-Deployment
- [ ] Website accessible
- [ ] Dashboard shows batches
- [ ] All pages load correctly
- [ ] Upload works
- [ ] No console errors
- [ ] Logs clean
- [ ] Team notified of completion

---

## 🎯 **QUICK REFERENCE COMMANDS**

### On Local (Mac)
```bash
git status
git push origin master
```

### On Server (via Termius)
```bash
# Connect
ssh yapi@docscan.adilabs.id

# Navigate
cd ~/doc-scan-ai

# Backup
sudo tar -czf ~/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/

# Update
git pull origin master
chmod +x update-production.sh
sudo ./update-production.sh

# Verify
./diagnose.sh
curl http://localhost:8000/api/health
```

---

## 📞 **NEED HELP?**

### Error Messages & Solutions

| Error | Solution |
|-------|----------|
| "Permission denied (publickey)" | Check SSH key setup |
| "Already up to date" | No changes to pull |
| "Port 8000 already in use" | `sudo systemctl restart docscan-backend` |
| "502 Bad Gateway" | Backend not running, restart service |
| "Database locked" | Stop backend, wait, restart |
| Batch tidak muncul | Run `./diagnose.sh`, fix permissions |

### Log Locations
```bash
# Backend logs
tail -f ~/doc-scan-ai/backend/server.log
sudo journalctl -u docscan-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

---

## 🎉 **SUCCESS CRITERIA**

Deployment berhasil jika:

✅ **Services Running:**
- Backend: `systemctl status docscan-backend` → active (running)
- Nginx: `systemctl status nginx` → active (running)

✅ **API Responding:**
- `curl http://localhost:8000/api/health` → {"status":"healthy"}
- `curl https://docscan.adilabs.id/api/health` → {"status":"healthy"}

✅ **Website Working:**
- Homepage loads
- Login works
- Dashboard shows batches
- All features functional

✅ **No Errors:**
- Backend logs clean
- Nginx logs clean
- Browser console clean

---

## 📚 **RELATED DOCS**

- **BUGFIXES.md** - All fixes in v2.0.0
- **PRODUCTION_DEBUG.md** - Troubleshooting guide
- **TEST_PLAN.md** - Testing procedures
- **UPGRADE_SUMMARY.md** - Complete upgrade info

---

**Version:** 2.0.0
**Last Updated:** 2025-10-11
**Deployment Time:** ~10-15 minutes
**Rollback Time:** ~5 minutes

---

## 💡 **PRO TIPS**

1. **Always backup before deploy**
2. **Run diagnostic before AND after**
3. **Check logs immediately after restart**
4. **Test in browser with hard refresh**
5. **Keep Termius session open during deploy**
6. **Have rollback plan ready**
7. **Deploy during low traffic time**
8. **Notify team before/after deploy**

---

**Ready to deploy?** Follow the steps above! 🚀
