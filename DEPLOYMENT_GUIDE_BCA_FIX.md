# 🚀 Deployment Guide - BCA Smart Mapper Fix

## 📋 Summary of Changes

This deployment includes critical fixes for BCA bank statement processing:

### 1. **Smart Mapper max_tokens Increase**
- **File**: `backend/smart_mapper.py:40`
- **Change**: `max_tokens: 2500 → 8000`
- **Impact**: Fixes GPT-4o response truncation for BCA statements with 90+ transactions

### 2. **Transaction Description Cleaning**
- **File**: `backend/exporters/rekening_koran_exporter.py`
- **New Function**: `_clean_keterangan()` - Lines 51-91
- **Impact**: Removes verbose bank prefixes from transaction descriptions
- **Example**:
  - Before: `TRSF E-BANKING DB 0307/FTSCY/WS95051 TRUCKING UNICER S1232 IKMAL`
  - After: `TRUCKING UNICER S1232 IKMAL`

### 3. **Debug Logging for Balance Tracking**
- **File**: `backend/exporters/rekening_koran_exporter.py:230-232`
- **Impact**: Adds logging to track `saldo_awal`, `saldo_akhir`, `saldo` extraction

---

## 🔧 Manual Deployment Steps

### Step 1: SSH into Production Server

```bash
ssh docScan@docscan.adilabs.id
```

### Step 2: Navigate to Application Directory

```bash
cd /var/www/docscan
```

### Step 3: Pull Latest Changes from GitHub

```bash
git pull origin master
```

You should see output like:
```
remote: Enumerating objects: 7, done.
remote: Counting objects: 100% (7/7), done.
remote: Compressing objects: 100% (4/4), done.
remote: Total 4 (delta 3), reused 4 (delta 3), pack-reused 0
Unpacking objects: 100% (4/4), 2.34 KiB | 2.34 MiB/s, done.
From https://github.com/Adi-Sumardi/doc-scan-ai
   387357e..519b680  master     -> origin/master
Updating 387357e..519b680
Fast-forward
 backend/exporters/rekening_koran_exporter.py | 53 +++++++++++++++++++++++++++
 backend/smart_mapper.py                      | 2 +-
 2 files changed, 54 insertions(+), 1 deletion(-)
```

### Step 4: Restart Backend Service

```bash
sudo systemctl restart docscan-backend
```

### Step 5: Verify Service Status

```bash
sudo systemctl status docscan-backend
```

Expected output:
```
● docscan-backend.service - Doc Scan AI Backend
   Loaded: loaded (/etc/systemd/system/docscan-backend.service; enabled)
   Active: active (running) since ...
```

### Step 6: Check Logs for Errors

```bash
sudo journalctl -u docscan-backend -n 50 --no-pager
```

Look for:
```
INFO:smart_mapper:🤖 Smart Mapper initialized with provider openai and model gpt-4o
INFO:     Application startup complete.
```

---

## ✅ Verification Steps

### 1. Test BCA Upload

1. Go to https://docscan.adilabs.id
2. Login as admin
3. Upload BCA bank statement (`ESTATEMENT_08990385808_202507.pdf`)
4. Wait for processing (~60 seconds)
5. Export to Excel

### 2. Verify Results

Check the exported Excel file:

**Expected Results:**
- ✅ **66 transactions** extracted (was failing before)
- ✅ **Clean descriptions** in "Keterangan" column:
  - ❌ Before: `TRSF E-BANKING DB 0307/FTSCY/WS95051 TRUCKING UNICER S1232 IKMAL MAULANA HARA`
  - ✅ After: `TRUCKING UNICER S1232 IKMAL MAULANA HARA`
- ✅ **Saldo Akhir** displays correctly (check Row 3, Column D)

### 3. Monitor Real-time Logs

```bash
sudo journalctl -u docscan-backend -f
```

Look for these log entries:
```
INFO:ai_processor:🤖 Applying Smart Mapper to chunk 1
INFO:smart_mapper:🤖 Calling OpenAI API with model: gpt-4o
INFO:smart_mapper:✅ OpenAI response received: [characters] characters
INFO:pdf_chunker:✅ Merged 2 chunks → 66 total transactions
INFO:rekening_koran_exporter:🔍 Excel Export - saldo_akhir: [value]
```

---

## 🐛 Troubleshooting

### Issue 1: Service Won't Start

**Check logs:**
```bash
sudo journalctl -u docscan-backend -n 100
```

**Common causes:**
- Python dependency issue → Check if `openai` library installed
- Port 8000 already in use → Check with `lsof -ti:8000`

### Issue 2: Smart Mapper Still Failing

**Check environment variables:**
```bash
cat /var/www/docscan/backend/.env | grep SMART_MAPPER
```

**Expected:**
```
SMART_MAPPER_ENABLED=true
SMART_MAPPER_PROVIDER=openai
SMART_MAPPER_MODEL=gpt-4o
SMART_MAPPER_API_KEY=sk-proj-...
```

### Issue 3: Transactions Still Truncated

**Check max_tokens in code:**
```bash
grep "max_tokens" /var/www/docscan/backend/smart_mapper.py
```

**Expected output:**
```python
self.max_tokens = int(os.getenv("SMART_MAPPER_MAX_TOKENS", "8000"))  # Increased for BCA statements
```

---

## 📊 Git Commit Reference

**Commit Hash**: `519b680`
**Commit Message**: `feat: Fix BCA Smart Mapper extraction and clean transaction descriptions`

**GitHub URL**: https://github.com/Adi-Sumardi/doc-scan-ai/commit/519b680

---

## 🎯 Success Criteria

Deployment is successful when:
- [x] Code pulled from GitHub successfully
- [x] Backend service restarts without errors
- [x] BCA file uploads process completely (66 transactions)
- [x] Excel export shows clean transaction descriptions
- [x] No truncation errors in logs
- [x] Saldo_akhir appears in Excel header

---

## 📞 Support

If deployment fails, check:
1. GitHub repository is up to date
2. Production server has internet access
3. MySQL database is running
4. OpenAI API key is valid and has credits
5. Google Document AI credentials are valid

---

## 🚀 Quick Commands Summary

```bash
# Deploy
ssh docScan@docscan.adilabs.id
cd /var/www/docscan
git pull origin master
sudo systemctl restart docscan-backend

# Verify
sudo systemctl status docscan-backend
sudo journalctl -u docscan-backend -n 50

# Monitor
sudo journalctl -u docscan-backend -f
```

---

**Deployment Date**: October 13, 2025
**Deployed By**: Claude Code AI Assistant
**Version**: BCA Smart Mapper Fix v1.0
