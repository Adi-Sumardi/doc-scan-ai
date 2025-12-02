# VERIFICATION: Chunking Berfungsi Dengan Benar

## ✅ FIXES YANG SUDAH DIIMPLEMENTASIKAN

### Fix #1: Fallback Chunk Threshold
**File**: `backend/ai_processor.py` (line 238)
- ❌ **BEFORE**: `chunk_threshold = 15` (terlalu besar)
- ✅ **AFTER**: `chunk_threshold = 8` (matching config.py)

### Fix #2: File Size Check (Prevent OOM di Google Document AI)
**File**: `backend/cloud_ai_processor.py` (line 193)
- ✅ **NEW**: Check file size **BEFORE** reading into memory
- ✅ Reject files >100MB with error message
- ✅ Force chunking for large files

### Fix #3: Memory Management di Google Document AI
**File**: `backend/cloud_ai_processor.py` (line 322)
- ✅ `del document_content` setelah processing
- ✅ `gc.collect()` untuk force cleanup
- ✅ Memory freed immediately after OCR

### Fix #4: Memory Monitoring per Chunk
**File**: `backend/ai_processor.py` (line 107)
- ✅ Log memory BEFORE chunk processing
- ✅ Log memory AFTER OCR
- ✅ Log memory AFTER cleanup
- ✅ Calculate delta untuk track memory leaks

### Fix #5: Aggressive Cleanup per Chunk
**File**: `backend/ai_processor.py` (line 154)
- ✅ `del chunk_text` setelah use
- ✅ Clear `raw_response` jika terlalu besar
- ✅ `gc.collect()` setelah SETIAP chunk
- ✅ Memory freed before processing next chunk

### Fix #6: Better Logging
**File**: `backend/ai_processor.py` (line 232)
- ✅ Log chunking config (enabled, threshold)
- ✅ Log decision logic (why chunking triggered/skipped)
- ✅ Log expected chunks count
- ✅ Log estimated transactions per chunk

---

## 🧪 VERIFICATION TESTS

### Test 1: Verify Config Loaded Correctly
```bash
# Check backend logs on startup
tail -100 /var/log/supervisor/backend.out.log | grep "PDF Chunker initialized"

# Expected output:
# 📄 PDF Chunker initialized (max 8 pages/chunk)
#    Estimated ~1200 transactions per chunk
```

### Test 2: Verify Chunking Decision Logic
**Upload a rekening koran with 50 pages**

Expected logs:
```
📄 Rekening Koran PDF: 50 pages
⚙️ Chunking config: enabled=True, threshold=8
🔍 Chunking decision: page_count(50) > threshold(8) = True
✅ CHUNKING WILL BE USED (50 pages > 8 threshold)
   Expected chunks: ~7
   Est. transactions per chunk: ~1200

🔄 CHUNKING MODE ACTIVATED
📄 File: rekening_koran.pdf
📊 Total pages: 50
📦 Chunk size: 8 pages
🔢 Expected chunks: 7
✅ Successfully created 7 chunks

========== CHUNK 1/7 ==========
📄 Pages: 1-8
💾 Memory before chunk 1: XXX MB
📊 File size: XX MB
📄 Reading file into memory: XX MB
✅ File read complete: XXXXX bytes
✅ Google Document AI success: XXXXX chars
🧹 Cleared document_content from memory
🧹 Garbage collection complete - memory freed
✅ Extracted XXXXX characters from chunk 1
💾 Memory after OCR: XXX MB (delta: +XX MB)
🧹 Clearing chunk 1 raw_response from memory
💾 Memory after cleanup: XXX MB (freed: XX MB)
📊 Chunk 1/7 complete - continuing...

[... repeat for chunks 2-7 ...]

🔗 MERGING CHUNK RESULTS
   Chunk 1: XXX txns, 0 duplicates removed
   Chunk 2: XXX txns, 0 duplicates removed
   ...
   ✅ Total unique transactions: ~7500
🧹 Cleaned up 7 chunk files + freed memory
```

### Test 3: Memory Profile
**Monitor memory during scan:**
```bash
# In terminal 1: Monitor memory
watch -n 1 'free -h && echo "---" && ps aux | grep python | grep -v grep | head -3'

# In terminal 2: Upload 50-page file
# Watch memory usage

# Expected behavior:
# - Memory rises during chunk 1 processing (~500MB)
# - Memory drops after chunk 1 cleanup
# - Pattern repeats for each chunk
# - NEVER exceeds 2GB per chunk
# - NO OOM KILL
```

### Test 4: File Size Protection
**Upload file >100MB:**
```bash
# Create large PDF (for testing)
# Expected error:
❌ File too large for processing: 150.5MB (>100MB limit)
❌ This file MUST be chunked before processing!
❌ Please ensure chunking is enabled and threshold is low enough
```

---

## 🔍 DEBUGGING CHECKLIST

If OOM KILL still occurs, check these in order:

### 1. ✅ Verify Chunking is Triggered
```bash
# Check logs for:
grep "CHUNKING WILL BE USED" /var/log/supervisor/backend.out.log

# If NOT found, check:
grep "CHUNKING SKIPPED" /var/log/supervisor/backend.out.log
```

**If skipped, possible reasons:**
- File has ≤8 pages (expected behavior)
- `enable_page_chunking = False` in config
- Page count detection failed

### 2. ✅ Verify Config Values
```bash
# Check current config
grep "pdf_chunk_size\|enable_page_chunking" /app/backend/config.py

# Expected:
pdf_chunk_size: int = 8
enable_page_chunking: bool = True
```

### 3. ✅ Check File Size
```bash
# Before upload, check file size
ls -lh /path/to/rekening_koran.pdf

# If >100MB per chunk (e.g., 50 pages / 8 = ~6.25 pages per chunk)
# Each chunk should be <20MB ideally
```

### 4. ✅ Monitor Memory Usage
```bash
# Real-time monitoring
watch -n 1 'free -h'

# Check for OOM in kernel logs
dmesg | tail -50 | grep -i "oom\|kill"

# Check backend memory specifically
ps aux | grep "uvicorn\|python" | grep -v grep
```

### 5. ✅ Check for Memory Leaks
```bash
# Get memory growth pattern from logs
grep "Memory after cleanup" /var/log/supervisor/backend.out.log

# Memory should NOT continuously grow
# Each chunk should show memory freed
```

---

## 📊 EXPECTED MEMORY USAGE (16GB RAM VPS)

### Per Chunk (8 pages, ~1,200 transactions):
- **File read**: +200-300 MB
- **Google OCR processing**: +400-600 MB
- **Peak during OCR**: ~800 MB
- **After cleanup**: -600 MB (back to ~200 MB)

### Total for 50-page file (7 chunks):
- **Sequential processing**: Peak ~1 GB per chunk
- **Total time**: 15-20 minutes
- **Peak system memory**: 4-6 GB (safe for 16GB VPS)
- **OOM Risk**: ❌ **VERY LOW**

### WARNING SIGNS:
- 🚨 Memory >8GB per chunk → File too large per chunk
- 🚨 Memory grows continuously → Memory leak
- 🚨 OOM KILL within 1-2 chunks → Google Document AI file size issue

---

## 🔧 EMERGENCY FIXES

### If still getting OOM:

#### Option 1: Reduce Chunk Size Further
```python
# File: backend/config.py
pdf_chunk_size: int = 5  # Reduce from 8 to 5 pages
```

#### Option 2: Add Memory Limit to Backend
```bash
# File: /etc/supervisor/conf.d/backend.conf
# Add memory limit (example: 4GB)
[program:backend]
environment=MALLOC_ARENA_MAX=2
```

#### Option 3: Process Chunks in Batches
```python
# Process 2 chunks, cleanup, then next 2 chunks
# Prevents memory accumulation
```

#### Option 4: Skip Large Files
```python
# File: backend/cloud_ai_processor.py
# Reduce file size limit from 100MB to 50MB
if file_size_mb > 50:  # More aggressive
    raise Exception(...)
```

---

## ✅ VALIDATION STEPS

### Before declaring fix complete:

1. ✅ Upload 10-page file → Should use chunking (2 chunks)
2. ✅ Upload 50-page file → Should use chunking (7 chunks)
3. ✅ Check Excel output → Should have ALL transactions
4. ✅ Monitor memory → Should stay <2GB per chunk
5. ✅ No OOM KILL → Process should complete successfully
6. ✅ Check logs → Should show proper memory cleanup

---

## 📝 LOG ANALYSIS COMMANDS

### Check if chunking was used:
```bash
grep -A 5 "CHUNKING MODE ACTIVATED" /var/log/supervisor/backend.out.log | tail -50
```

### Check memory usage per chunk:
```bash
grep "Memory after cleanup" /var/log/supervisor/backend.out.log | tail -20
```

### Check for errors:
```bash
grep -i "error\|fail\|oom" /var/log/supervisor/backend.out.log | tail -50
```

### Check final result:
```bash
grep -A 3 "MERGING CHUNK RESULTS" /var/log/supervisor/backend.out.log | tail -20
```

---

## 🎯 SUCCESS CRITERIA

✅ **Fix is successful if:**
1. 50-page file triggers chunking (7 chunks)
2. Memory per chunk <2GB
3. No OOM KILL occurs
4. Excel output contains all ~7,500 transactions
5. Processing completes in 15-20 minutes
6. System memory usage <8GB peak

---

## 📞 SUPPORT

If OOM still occurs after all fixes:
1. Collect full backend logs
2. Collect memory monitoring data
3. Share file size and page count
4. Check VPS memory: `free -h`
5. Report to development team

**Status**: ✅ Fixes deployed - Ready for testing
**Date**: 2025-01-10
