# 🔧 Fix Production - Database Missing

## ❌ **ROOT CAUSE IDENTIFIED**

```
✗ Database file NOT found!
  → Database should be at: backend/database.db
```

**This is why batches not showing!** Backend running tapi database tidak ada.

---

## 🎯 **SOLUTION - Copy Commands Berikut**

### **Step 1: Check Lokasi Database Sebenarnya**

```bash
# Cari dimana database sebenarnya ada
find /var/www/docscan -name "*.db" -type f 2>/dev/null
```

**Kemungkinan lokasi:**
- `/var/www/docscan/backend/database.db`
- `/var/www/docscan/database.db`
- `/var/www/docscan/doc_scan.db`

---

### **Step 2A: Jika Database Ditemukan di /var/www/docscan**

```bash
# Copy database ke lokasi yang benar
sudo cp /var/www/docscan/backend/database.db ~/doc-scan-ai/backend/database.db

# Set permissions
sudo chown docScan:docScan ~/doc-scan-ai/backend/database.db
chmod 644 ~/doc-scan-ai/backend/database.db

# Verify
ls -lah ~/doc-scan-ai/backend/database.db
```

---

### **Step 2B: Jika Database Tidak Ditemukan (Create New)**

```bash
# Create database manually
cd ~/doc-scan-ai/backend

# Check if there's database initialization script
ls -la *.py | grep -E "(database|init|setup)"

# If there's database.py or init_db.py:
python3 database.py
# or
python3 init_db.py

# Verify database created
ls -lah database.db
```

---

### **Step 3: Verify Database Has Tables**

```bash
# Check database structure
sqlite3 ~/doc-scan-ai/backend/database.db ".tables"

# Should show tables like:
# batches  users  scan_results  etc.

# Check if has data
sqlite3 ~/doc-scan-ai/backend/database.db "SELECT COUNT(*) FROM batches;"
```

---

### **Step 4: Restart Backend**

```bash
# Restart backend service di /var/www/docscan
sudo systemctl restart docscan-backend

# Wait 3 seconds
sleep 3

# Check status
sudo systemctl status docscan-backend

# Test API
curl http://localhost:8000/api/batches
```

---

## 🔍 **DIAGNOSIS**

Backend Anda berjalan dari **2 lokasi berbeda:**

1. **Code Location:** `~/doc-scan-ai/` (tempat git pull)
2. **Running Location:** `/var/www/docscan/` (tempat backend aktif)

**Backend yang running** membaca database dari `/var/www/docscan/backend/database.db`
**Git pull location** di `~/doc-scan-ai/backend/database.db`

---

## ✅ **PROPER FIX - Sync Locations**

### **Option 1: Point Backend to Correct Database (Recommended)**

```bash
# 1. Find backend config file
cd /var/www/docscan
find . -name "config.py" -o -name "settings.py" -o -name ".env"

# 2. Edit config to point to correct database path
# Look for DATABASE_URL or database path setting

# 3. Or create symlink
ln -sf /var/www/docscan/backend/database.db ~/doc-scan-ai/backend/database.db
```

### **Option 2: Deploy from /var/www/docscan (Better)**

```bash
# 1. Go to actual running location
cd /var/www/docscan

# 2. Pull updates there
sudo -u docScan git stash
sudo -u docScan git pull origin master

# 3. Install dependencies
npm install
npm run build

# 4. Restart
sudo systemctl restart docscan-backend
```

---

## 🎯 **IMMEDIATE FIX - RUN THESE NOW**

```bash
# 1. Find database
DB_PATH=$(find /var/www/docscan -name "database.db" -type f 2>/dev/null | head -n 1)
echo "Found database at: $DB_PATH"

# 2. Check if found
if [ -n "$DB_PATH" ]; then
    echo "Database exists!"
    sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM batches;"
else
    echo "Database NOT found - need to restore from backup"
fi

# 3. If found, copy to both locations
if [ -n "$DB_PATH" ]; then
    sudo cp "$DB_PATH" ~/doc-scan-ai/backend/database.db
    sudo chown docScan:docScan ~/doc-scan-ai/backend/database.db
    chmod 644 ~/doc-scan-ai/backend/database.db
    echo "Database copied!"
fi

# 4. Restart backend
sudo systemctl restart docscan-backend
sleep 3

# 5. Test
curl http://localhost:8000/api/batches -H "Authorization: Bearer YOUR_TOKEN" | jq
```

---

## 📊 **VERIFY SUCCESS**

```bash
# Run diagnostic again
cd ~/doc-scan-ai
./diagnose.sh | grep -A 5 "Database Status"

# Should now show:
# ✓ Database file exists
# ✓ Database has data
```

---

## 🚨 **IF DATABASE TRULY MISSING - RESTORE FROM BACKUP**

```bash
# 1. List backups
ls -lh ~/backups/

# 2. Extract latest backup
cd ~
tar -xzf backups/backup_TIMESTAMP.tar.gz

# 3. Copy database
cp backend/database.db doc-scan-ai/backend/
cp backend/database.db /var/www/docscan/backend/

# 4. Set permissions
sudo chown docScan:docScan doc-scan-ai/backend/database.db
sudo chown docScan:docScan /var/www/docscan/backend/database.db
chmod 644 doc-scan-ai/backend/database.db
chmod 644 /var/www/docscan/backend/database.db

# 5. Restart
sudo systemctl restart docscan-backend
```

---

## 💡 **UNDERSTANDING THE ISSUE**

Your setup has:
- **Development code:** `~/doc-scan-ai/` (where you git pull)
- **Production code:** `/var/www/docscan/` (where backend runs)

**The backend process is running from `/var/www/docscan/`** as shown:
```
docScan   242732  /var/www/docscan/venv/bin/python3.10
```

So database must be at: `/var/www/docscan/backend/database.db`

---

## ✅ **RECOMMENDED PERMANENT FIX**

### **Deploy to Correct Location:**

```bash
# 1. Go to actual running location
cd /var/www/docscan

# 2. Backup first
sudo tar -czf ~/backups/var_www_backup_$(date +%Y%m%d_%H%M%S).tar.gz .

# 3. Pull v2.0.0
sudo -u docScan git stash
sudo -u docScan git pull origin master

# 4. Update dependencies
npm install
npm run build
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 5. Restart
sudo systemctl restart docscan-backend
sudo systemctl restart nginx

# 6. Test
curl http://localhost:8000/api/batches
```

---

## 🎯 **NEXT COMMANDS TO RUN NOW**

```bash
# Copy-paste all of this:

echo "=== Finding Database ==="
find /var/www/docscan -name "*.db" -type f 2>/dev/null

echo ""
echo "=== Deploying to Correct Location ==="
cd /var/www/docscan
sudo -u docScan git stash
sudo -u docScan git pull origin master

echo ""
echo "=== Restarting Services ==="
sudo systemctl restart docscan-backend
sleep 3
sudo systemctl status docscan-backend

echo ""
echo "=== Testing API ==="
curl http://localhost:8000/api/health
curl http://localhost:8000/api/batches | jq

echo ""
echo "✅ Done! Check browser now"
```

---

**Run the commands above and batches will appear!** 🚀
