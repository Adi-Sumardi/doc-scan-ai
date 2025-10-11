# Production Update Guide - Smart Mapper AI Enhancement

## 📋 Update Summary

**Date**: October 11, 2025
**Version**: Smart Mapper AI Universal Update
**Commit**: `3d2df1f`

### 🎯 What's New:

1. **Rekening Koran** - Full Smart Mapper AI support
2. **Invoice** - Universal template for all invoice types
3. **Faktur Pajak** - Email field for buyer
4. **Export Routing** - Fixed missing exporters

---

## 🚀 Step-by-Step Production Update

### Step 1: Connect to Production Server

```bash
# Via Termius or SSH
ssh docScan@your-production-ip
```

### Step 2: Navigate to Project Directory

```bash
cd ~/doc-scan-ai
```

### Step 3: Backup Current Production (IMPORTANT!)

```bash
# Create backup directory with timestamp
backup_dir=~/backups/doc-scan-ai-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $backup_dir

# Backup backend files
cp -r backend/ $backup_dir/
cp -r src/ $backup_dir/

echo "✅ Backup created at: $backup_dir"
```

### Step 4: Pull Latest Changes from GitHub

```bash
# Stash any local changes (if any)
git stash

# Pull latest code
git pull origin master

# Should show: 3d2df1f - feat: Universal Smart Mapper AI for All Document Types
git log -1 --oneline
```

### Step 5: Install/Update Dependencies (If Needed)

```bash
# Check if new Python packages are needed
cd backend
pip install -r requirements.txt

# If using virtual environment:
source venv/bin/activate  # or your venv path
pip install -r requirements.txt
```

### Step 6: Verify New Files

```bash
# Check new template files exist
ls -la backend/templates/

# Should see:
# - faktur_pajak_template.json (updated)
# - invoice_template.json (NEW)
# - rekening_koran_template.json (NEW)
# - pph21_template.json
# - pph23_template.json
```

### Step 7: Restart Backend Service

```bash
# If using PM2
pm2 restart doc-scan-backend

# Or if using systemd
sudo systemctl restart doc-scan-backend

# Or if running manually
# Kill old process and start new one
pkill -f "uvicorn"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
```

### Step 8: Restart Frontend (If Needed)

```bash
# If using PM2
pm2 restart doc-scan-frontend

# Or rebuild frontend assets
npm run build
```

### Step 9: Verify Services Running

```bash
# Check backend
curl http://localhost:8000/api/health

# Check PM2 status
pm2 status

# Should show both services running
```

### Step 10: Test New Features

**Test Checklist:**

- [ ] Upload **Rekening Koran** (any bank)
  - [ ] Verify Excel export shows ALL transactions
  - [ ] Verify PDF export shows complete data

- [ ] Upload **Invoice** (any type)
  - [ ] Verify Excel export shows vendor, customer, items
  - [ ] Verify PDF export shows complete invoice details

- [ ] Upload **Faktur Pajak**
  - [ ] Check PDF page 2 (Faktur Masukan)
  - [ ] Verify "Email" field shows buyer email (if available in document)

---

## 🔍 Troubleshooting

### Issue: "Template not found" error

**Solution:**
```bash
# Verify template files exist
ls -la backend/templates/*.json

# If missing, check git status
git status

# Re-pull if needed
git fetch origin master
git reset --hard origin/master
```

### Issue: Backend crashes after update

**Solution:**
```bash
# Check logs
pm2 logs doc-scan-backend --lines 50

# Or check systemd logs
sudo journalctl -u doc-scan-backend -n 50

# Common issues:
# 1. Missing dependencies - run: pip install -r requirements.txt
# 2. Port already in use - kill old process first
# 3. Permission issues - check file ownership
```

### Issue: Smart Mapper not working

**Solution:**
```bash
# Verify environment variables
cat backend/.env | grep -i openai

# Should have:
# OPENAI_API_KEY=sk-...
# ENABLE_SMART_MAPPER=true

# Restart backend after verifying
pm2 restart doc-scan-backend
```

### Issue: Excel/PDF export errors

**Solution:**
```bash
# Check Python packages
pip list | grep -E "openpyxl|reportlab"

# Should show:
# openpyxl >= 3.0.0
# reportlab >= 3.6.0

# Reinstall if missing
pip install openpyxl reportlab
```

---

## 🎯 Verification Commands

### Quick Health Check
```bash
# Backend health
curl http://localhost:8000/api/health

# Check logs for errors
pm2 logs doc-scan-backend --lines 20 | grep -i error

# Test Smart Mapper status
curl http://localhost:8000/api/status
```

### Check File Changes
```bash
# Show modified files in this update
git show --name-status 3d2df1f

# Show detailed changes
git show 3d2df1f
```

---

## 📊 What Changed (Technical Details)

### Files Modified:
```
backend/ai_processor.py                          # Added Smart Mapper for rekening_koran & invoice
backend/exporters/invoice_exporter.py            # Enhanced converter with items array
backend/exporters/rekening_koran_exporter.py     # Added debug logging
backend/routers/exports.py                       # Added missing RekeningKoranExporter routes
backend/templates/faktur_pajak_template.json     # Added email field to buyer
```

### Files Added:
```
backend/templates/invoice_template.json          # Universal invoice template
backend/templates/rekening_koran_template.json   # Universal bank statement template
backend/pdf_chunker.py                           # PDF chunking utility
```

---

## 🔐 Security Notes

- ✅ No API keys in code
- ✅ All secrets in .env file
- ✅ .env file is in .gitignore
- ✅ GitHub push protection enabled

---

## 📝 Rollback Plan (If Needed)

If something goes wrong, rollback to previous version:

```bash
# Navigate to backup
cd ~/backups/doc-scan-ai-backup-YYYYMMDD-HHMMSS

# Copy back to production
cp -r backend/* ~/doc-scan-ai/backend/
cp -r src/* ~/doc-scan-ai/src/

# Restart services
pm2 restart all

# Or rollback git commit
cd ~/doc-scan-ai
git reset --hard HEAD~1
pm2 restart all
```

---

## ✅ Success Criteria

Update is successful when:

- ✅ Backend service running without errors
- ✅ Frontend accessible
- ✅ Can upload rekening koran from any bank
- ✅ Can upload any invoice type
- ✅ Excel exports show complete data
- ✅ PDF exports show buyer email (faktur pajak)
- ✅ No errors in PM2 logs

---

## 📞 Support

If you encounter issues:

1. Check logs: `pm2 logs doc-scan-backend --lines 100`
2. Verify services: `pm2 status`
3. Test API: `curl http://localhost:8000/api/health`
4. Review this guide's troubleshooting section

---

**Last Updated**: October 11, 2025
**Deployed By**: [Your Name]
**Status**: Ready for Production Deployment
