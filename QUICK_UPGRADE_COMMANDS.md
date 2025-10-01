# ⚡ Quick Production Upgrade Commands

## Copy-Paste Ready Commands for Your Server

---

## 🚀 FULL UPGRADE (Copy All at Once)

```bash
# === STEP 1: Backup ===
cd /var/www/docscan
mysqldump -u docuser -p docscan_db > /tmp/docscan_backup_$(date +%Y%m%d_%H%M%S).sql

# === STEP 2: Pull Code (You already did this!) ===
# git pull origin master  # ✅ DONE

# === STEP 3: Install Dependencies ===
source venv/bin/activate  # Or your virtualenv name
pip install slowapi

# === STEP 4: Create Logs Directory ===
mkdir -p backend/logs
chmod 755 backend/logs

# === STEP 5: Graceful Restart ===
# Find and stop old process
OLD_PID=$(ps aux | grep "python.*main.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$OLD_PID" ]; then
  echo "Stopping old process: $OLD_PID"
  kill -TERM $OLD_PID
  sleep 5
fi

# Start new version
cd backend
nohup python main.py > /tmp/docscan_backend.log 2>&1 &
echo "Backend started with PID: $!"

# === STEP 6: Verify ===
sleep 3
curl http://localhost:8000/api/health | jq .
```

---

## 🔍 Quick Verification

```bash
# Check backend running
ps aux | grep "python.*main.py" | grep -v grep

# Test health
curl http://localhost:8000/api/health

# Test security (should fail without auth)
curl http://localhost:8000/api/cache/stats
# Expected: {"detail":"Not authenticated"} ✅

# Check audit log created
ls -la /var/www/docscan/backend/logs/audit.log

# Watch audit logs live
tail -f /var/www/docscan/backend/logs/audit.log | jq .
```

---

## 🧪 Test Rate Limiting

```bash
# This will test login rate limit (10/min)
# Request 11 should fail with 429
for i in {1..11}; do
  echo "Request $i:"
  curl -w "\nHTTP: %{http_code}\n" \
    -X POST http://localhost:8000/api/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}'
  sleep 0.5
done
```

---

## 📊 Monitor Audit Logs

```bash
# Watch live
tail -f /var/www/docscan/backend/logs/audit.log | jq .

# Count total login attempts
cat /var/www/docscan/backend/logs/audit.log | jq 'select(.action=="login")' | wc -l

# Count failed logins
cat /var/www/docscan/backend/logs/audit.log | jq 'select(.status=="failure")' | wc -l

# Find IPs with most failed logins (potential attackers)
cat /var/www/docscan/backend/logs/audit.log | \
  jq -r 'select(.status=="failure") | .ip_address' | \
  sort | uniq -c | sort -rn | head -10
```

---

## 🔙 Quick Rollback (If Needed)

```bash
cd /var/www/docscan

# Stop current
pkill -f "python.*main.py"

# Rollback code
git checkout 7e15b89  # Your previous commit

# Restart old version
cd backend && python main.py &

# Verify
curl http://localhost:8000/api/health
```

---

## 🚨 Troubleshooting

### Backend won't start?
```bash
# Check what's wrong
cd /var/www/docscan/backend
python main.py
# Read error messages

# Common fixes:
pip install slowapi  # If module not found
mkdir -p logs && chmod 755 logs  # If permission denied
```

### Port already in use?
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it
kill <PID>

# Or kill all Python processes (careful!)
pkill -f "python.*main"
```

### Check logs?
```bash
# Backend logs
tail -50 /tmp/docscan_backend.log

# Audit logs
tail -50 /var/www/docscan/backend/logs/audit.log | jq .

# System logs (if using systemd)
journalctl -u docscan-backend -n 50
```

---

## ✅ Success Check (Run After Upgrade)

```bash
echo "=== Backend Health ==="
curl -s http://localhost:8000/api/health | jq .

echo -e "\n=== Security Check (Should Fail) ==="
curl -s http://localhost:8000/api/cache/stats | jq .

echo -e "\n=== Debug Removed (Should 404) ==="
curl -s -X DELETE http://localhost:8000/api/debug/clear-storage | jq .

echo -e "\n=== Audit Log Exists? ==="
ls -lh /var/www/docscan/backend/logs/audit.log

echo -e "\n=== Backend Process ==="
ps aux | grep "python.*main.py" | grep -v grep

echo -e "\n✅ If all checks pass, upgrade successful!"
```

---

## 📞 Quick Commands Reference

| Task | Command |
|------|---------|
| Check backend running | `ps aux \| grep python \| grep main` |
| Restart backend | `pkill -f python.*main && cd backend && python main.py &` |
| View audit logs | `tail -f backend/logs/audit.log \| jq .` |
| Test health | `curl localhost:8000/api/health` |
| Check port usage | `lsof -i :8000` |
| Backend logs | `tail -f /tmp/docscan_backend.log` |

---

*Quick Reference v1.0 - October 1, 2025*
