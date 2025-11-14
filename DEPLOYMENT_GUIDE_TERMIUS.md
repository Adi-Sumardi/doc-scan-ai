# 🚀 Deployment Guide - Update Production via Termius

## 📋 Update: Faktur Pajak Flat Table Excel Export

**Date:** 2025-01-14
**Commit:** 574fc53
**Impact:** Excel export for Faktur Pajak - Non-breaking change

---

## ✅ Pre-Deployment Checklist

- [x] Code pushed to GitHub (commit: 574fc53)
- [x] Changes tested locally
- [x] Deployment script created (`deploy-flat-table-excel.sh`)
- [ ] Backup production database (optional, no DB changes)
- [ ] Notify users (optional, no downtime expected)

---

## 🔧 Production Server Info

**From deploy scripts:**
- **Server:** docscan.adilabs.id
- **User:** docScan
- **App Directory:** /var/www/docscan
- **Service Name:** docscan-backend
- **No Docker** (uses systemd service)

---

## 📱 OPTION 1: Automatic Deployment (Recommended)

### Step 1: Run Deployment Script from Local

```bash
# Make script executable
chmod +x deploy-flat-table-excel.sh

# Run deployment
./deploy-flat-table-excel.sh
```

**What the script does:**
1. SSH to production server
2. Pull latest code from GitHub
3. Verify flat table code is present
4. Check Python dependencies
5. Restart backend service
6. Verify service is running
7. Test API health

**Expected output:**
```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          🎉 DEPLOYMENT COMPLETE! 🎉                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

**If script fails:**
- Check SSH connection to production
- Verify you can SSH as `docScan@docscan.adilabs.id`
- Proceed to Manual Deployment (Option 2)

---

## 🔨 OPTION 2: Manual Deployment via Termius

### Step 1: Connect to Production Server

**Via Termius App:**
1. Open Termius
2. Find connection: `docScan@docscan.adilabs.id`
3. Click "Connect"
4. Enter password/SSH key

**Expected:**
```
Welcome to Ubuntu...
Last login: ...
docScan@production:~$
```

---

### Step 2: Navigate to Application Directory

```bash
# Go to app directory
cd /var/www/docscan

# Verify you're in the right place
pwd
# Should show: /var/www/docscan

# Check current branch
git branch
# Should show: * master
```

---

### Step 3: Check Current Status

```bash
# Check current commit
git log -1 --oneline
# Note the current commit hash

# Check git status
git status
# Should be clean (no uncommitted changes)

# Check service status
sudo systemctl status docscan-backend
# Should show: Active: active (running)
```

---

### Step 4: Pull Latest Code

```bash
# Fetch from GitHub
git fetch origin

# Check what will be pulled
git log HEAD..origin/master --oneline
# Should show: 574fc53 feat: Faktur Pajak Excel export - Flat table structure

# Pull changes
git pull origin master
```

**Expected output:**
```
Updating 076ec74..574fc53
Fast-forward
 backend/exporters/faktur_pajak_exporter.py | 468 ++++++++++++++-------
 1 file changed, 219 insertions(+), 249 deletions(-)
```

---

### Step 5: Verify Changes

```bash
# Verify flat table code is present
grep -n "FLAT TABLE: ALL DATA REPEATED" backend/exporters/faktur_pajak_exporter.py

# Should show two matches:
# Line 882: # ===== FLAT TABLE: ALL DATA REPEATED PER ITEM ROW (NO MERGE) =====
# Line 1103: # ===== FLAT TABLE: ALL DATA REPEATED PER ITEM ROW (NO MERGE) =====
```

If you see the matches above, code is updated correctly! ✅

---

### Step 6: Check Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Check openpyxl is installed
python -c "from openpyxl import Workbook; print('✅ openpyxl OK')"

# Should show: ✅ openpyxl OK
```

**If openpyxl not found (unlikely):**
```bash
pip install openpyxl
```

---

### Step 7: Restart Backend Service

```bash
# Restart backend
sudo systemctl restart docscan-backend

# Wait a few seconds
sleep 5

# Check status
sudo systemctl status docscan-backend
```

**Expected output:**
```
● docscan-backend.service - Doc Scan AI Backend
   Loaded: loaded (/etc/systemd/system/docscan-backend.service; enabled)
   Active: active (running) since ...

   ... INFO:main:✅ Modular Exporter System Loaded
   ... INFO:     Application startup complete.
```

✅ Look for "Active: active (running)" and "Application startup complete"

---

### Step 8: Monitor Logs (Optional)

```bash
# Watch logs in real-time
sudo journalctl -u docscan-backend -f

# Press Ctrl+C to stop watching
```

**Look for:**
- `✅ Modular Exporter System Loaded`
- `✅ Database connection OK`
- `INFO: Application startup complete.`

---

### Step 9: Test the Update

**Option A: Via Browser**

1. Open: https://docscan.adilabs.id
2. Upload a Faktur Pajak PDF
3. Wait for processing
4. Click "Download Excel"
5. Open Excel file

**Verify:**
- ✅ Columns A-O: Data should be repeated per item row (NO merged cells)
- ✅ Test formula: `=VLOOKUP(A3, A:S, 12, FALSE)` → Should return DPP value
- ✅ Create Pivot Table: Insert → PivotTable → Should work!
- ✅ Grand Total row has SUM formulas (not hardcoded values)

**Option B: Via API Test (from server)**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Should return: {"status":"healthy"} or similar
```

---

### Step 10: Verify in Logs

```bash
# Upload a file via browser, then check logs
sudo journalctl -u docscan-backend -n 50 | grep -E "(Excel|export|FLAT)"

# Look for:
# ✅ Faktur Pajak Excel export created: /path/to/file.xlsx
```

---

## 🆘 Rollback Procedure (If Issues)

### If something goes wrong:

```bash
# Navigate to app directory
cd /var/www/docscan

# Check previous commit
git log -2 --oneline
# 574fc53 feat: Faktur Pajak Excel export - Flat table structure
# 076ec74 fix: Project edit modal - resolve 500 error & improve UX

# Rollback to previous commit
git reset --hard 076ec74

# Restart backend
sudo systemctl restart docscan-backend

# Check status
sudo systemctl status docscan-backend
```

---

## 🔍 Troubleshooting

### Issue: Service won't start

```bash
# Check detailed logs
sudo journalctl -u docscan-backend -n 100

# Common fixes:
# 1. Port already in use
sudo lsof -i:8000
sudo kill -9 <PID>

# 2. Python import error
cd /var/www/docscan/backend
source ../venv/bin/activate
python -c "from exporters.faktur_pajak_exporter import FakturPajakExporter; print('OK')"

# 3. Restart service
sudo systemctl restart docscan-backend
```

---

### Issue: Excel still shows merged cells

```bash
# Clear Python cache
cd /var/www/docscan/backend
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -delete

# Restart service
sudo systemctl restart docscan-backend

# Verify code is updated
grep -c "FLAT TABLE" backend/exporters/faktur_pajak_exporter.py
# Should show: 2
```

---

### Issue: Git pull fails

```bash
# Check git status
git status

# If uncommitted changes, stash them
git stash

# Pull again
git pull origin master

# If merge conflict
git reset --hard origin/master
```

---

## 📊 Post-Deployment Verification

### Checklist:

- [ ] Backend service is running (`sudo systemctl status docscan-backend`)
- [ ] No errors in logs (`sudo journalctl -u docscan-backend -n 50`)
- [ ] Website loads (https://docscan.adilabs.id)
- [ ] Upload Faktur Pajak works
- [ ] Excel download works
- [ ] Excel has NO merged cells in data rows
- [ ] Excel formulas work (VLOOKUP, SUMIF)
- [ ] Pivot table works
- [ ] Batch upload (ZIP) works

---

## 📝 Quick Command Reference

```bash
# SSH to server
ssh docScan@docscan.adilabs.id

# Navigate to app
cd /var/www/docscan

# Pull code
git pull origin master

# Restart backend
sudo systemctl restart docscan-backend

# Check status
sudo systemctl status docscan-backend

# View logs
sudo journalctl -u docscan-backend -f

# Test API
curl http://localhost:8000/health

# Rollback
git reset --hard 076ec74 && sudo systemctl restart docscan-backend
```

---

## 🎯 What Changed

### File Modified:
- `backend/exporters/faktur_pajak_exporter.py`

### Changes:
1. **_populate_excel_sheet()** (Line 819-1043)
   - Removed merged cells for columns 1-15
   - Repeat seller/buyer/financial data per item row
   - Flat table structure (formula-friendly)

2. **batch_export_to_excel()** (Line 1103-1258)
   - Same flat structure for batch exports
   - Alternating row colors per document
   - Subtotal row per document

### Excel Structure:
```
Row 1: [TITLE]
Row 2: [HEADERS - 19 columns]
Row 3: PT ABC | ... | Laptop  | 10 | 5M | 50M   (All data filled)
Row 4: PT ABC | ... | Mouse   | 5  | 150K | 750K (All data repeated)
Row 5: PT ABC | ... | Keyboard| 3  | 850K | 2.5M (All data repeated)
Row 6: [GRAND TOTAL] | 18 | | 58.25M
```

**Key:** NO merged cells = VLOOKUP/Pivot Tables work! 🎉

---

## ✅ Success Criteria

Deployment is successful when:

1. ✅ Backend service is running without errors
2. ✅ Excel export creates files successfully
3. ✅ Excel files have NO merged cells in data rows (except Grand Total label)
4. ✅ VLOOKUP formula works: `=VLOOKUP("PT ABC", A:S, 12, FALSE)`
5. ✅ Pivot Table works (can group by Seller/Buyer)
6. ✅ All upload methods work (single, batch, ZIP)

---

## 📞 Support

If issues persist:
- Check logs: `sudo journalctl -u docscan-backend -n 100`
- Rollback: `git reset --hard 076ec74`
- Contact: Check ADMIN_CREDENTIALS.md for admin access

---

**Last Updated:** 2025-01-14
**Tested:** ✅ Local environment
**Production Status:** Ready to deploy

---
