# 🚀 Quick Deploy Commands - Copy & Paste Ready

## For You (Copy ini step by step)

---

## **STEP 1: Push dari Mac** ✅ (DONE)

```bash
# Already done! ✅
# Code sudah di GitHub
```

---

## **STEP 2: Connect ke Server via Termius**

**Open Termius → Connect to:**
- Host: `docscan.adilabs.id`
- Username: `yapi`
- Password: [your password]

**Or via Terminal SSH:**
```bash
ssh yapi@docscan.adilabs.id
```

---

## **STEP 3: Backup (WAJIB!)**

```bash
# Copy-paste semua baris ini:
cd ~/doc-scan-ai
mkdir -p ~/backups
sudo tar -czf ~/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/
ls -lh ~/backups/
```

✅ Pastikan file backup muncul!

---

## **STEP 4: Pull Code dari GitHub**

```bash
# Copy-paste:
cd ~/doc-scan-ai
git stash
git pull origin master
```

Expected: "Updating ... Fast-forward"

---

## **STEP 5: Run Update Script**

```bash
# Copy-paste:
chmod +x update-production.sh
sudo ./update-production.sh
```

Script akan otomatis:
- Install dependencies
- Build frontend
- Fix permissions
- Restart services
- Run health checks

---

## **STEP 6: Verify Everything OK**

```bash
# Copy-paste:
./diagnose.sh
```

Look for:
- ✅ Backend is RUNNING
- ✅ Nginx is RUNNING
- ✅ Database file exists
- ✅ No critical issues

---

## **STEP 7: Test API**

```bash
# Copy-paste:
curl http://localhost:8000/api/health
```

Should return: `{"status":"healthy"}`

---

## **STEP 8: Open Browser**

1. Go to: **https://docscan.adilabs.id**
2. Press: **Ctrl+Shift+R** (hard refresh)
3. Login
4. Check Dashboard → Should show batches! ✅

---

## 🐛 **If Batches STILL Not Showing**

```bash
# Run this:
./diagnose.sh | grep "✗"
```

Common fixes:

### Fix 1: Backend Not Running
```bash
sudo systemctl restart docscan-backend
sudo systemctl status docscan-backend
```

### Fix 2: Permission Issues
```bash
cd ~/doc-scan-ai
sudo chown -R www-data:www-data backend/
sudo chmod -R 755 backend/
sudo chmod 644 backend/*.db
sudo systemctl restart docscan-backend
```

### Fix 3: Database Empty
```bash
sqlite3 backend/database.db "SELECT COUNT(*) FROM batches;"
# If 0, database is empty - need to upload documents
```

---

## 🔄 **If Need to Rollback**

```bash
# Stop services
sudo systemctl stop docscan-backend
sudo systemctl stop nginx

# Restore backup (change TIMESTAMP to your backup file)
cd ~
tar -xzf backups/backup_TIMESTAMP.tar.gz -C doc-scan-ai/

# Fix permissions
cd doc-scan-ai
sudo chown -R www-data:www-data backend/
sudo chmod -R 755 backend/

# Restart
sudo systemctl start docscan-backend
sudo systemctl start nginx
```

---

## 📊 **Verification Checklist**

After deployment, check:

- [ ] `systemctl status docscan-backend` → active (running)
- [ ] `systemctl status nginx` → active (running)
- [ ] `curl http://localhost:8000/api/health` → returns healthy
- [ ] Website loads: https://docscan.adilabs.id
- [ ] Login works
- [ ] Dashboard shows batches
- [ ] No errors in browser console (F12)

---

## 🆘 **Emergency Help**

### Check Logs:
```bash
# Backend logs
tail -n 50 ~/doc-scan-ai/backend/server.log

# System logs
sudo journalctl -u docscan-backend -n 50

# Nginx logs
sudo tail -n 50 /var/log/nginx/error.log
```

### Restart Everything:
```bash
sudo systemctl restart docscan-backend
sudo systemctl restart nginx
sleep 3
curl http://localhost:8000/api/health
```

---

## ✅ **All Commands in One Block** (For Quick Copy)

```bash
# FULL DEPLOYMENT - Copy all this:

cd ~/doc-scan-ai

# 1. Backup
mkdir -p ~/backups
sudo tar -czf ~/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/

# 2. Pull code
git stash
git pull origin master

# 3. Deploy
chmod +x update-production.sh diagnose.sh
sudo ./update-production.sh

# 4. Verify
./diagnose.sh
curl http://localhost:8000/api/health

echo ""
echo "✅ Deployment complete!"
echo "Open browser: https://docscan.adilabs.id"
echo "Press Ctrl+Shift+R to hard refresh"
```

---

**Estimated Time:** 5-10 minutes
**Difficulty:** Easy (just copy-paste)
**Risk:** Low (we have backup!)

**Good luck! 🚀**
