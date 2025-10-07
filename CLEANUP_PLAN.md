# 🧹 File Cleanup Plan

## 📋 File Duplikat yang Ditemukan

### 1. Backup Files (Safe to Delete) ⚠️
```
backend/ai_processor.py.backup    # Backup lama dari ai_processor.py
backend/ai_processor.py.old       # Backup lama dari ai_processor.py
```
**Recommendation**: HAPUS (sudah ada ai_processor.py yang aktif)

---

### 2. Main Files (Action Required) 🔄

#### Current Situation:
- `backend/main.py` (1,941 lines) - File lama/original ❌
- `backend/main_new.py` (200 lines) - File baru hasil refactoring ✅

**Recommendation**: 
```bash
# Backup main.py lama
mv backend/main.py backend/main.py.backup_20251007

# Deploy main_new.py sebagai main.py
mv backend/main_new.py backend/main.py
```

---

### 3. Database Files (Choose One) 💾

```
backend/app.db (372KB)           # Database production?
backend/doc_scan_dev.db (300KB)  # Database development?
```

**Question**: Mana yang aktif digunakan?
- Check di `backend/config.py` atau `.env` file
- Biasanya setting: `DATABASE_URL` atau `DB_PATH`

**Recommendation**: Setelah konfirmasi, hapus yang tidak dipakai

---

### 4. Log Files (Duplicate Locations) 📝

```
./backend.log                    # Log di root folder
./backend/backend.log            # Log di backend folder
./backend/logs/audit.log         # Structured logs (KEEP)
```

**Recommendation**: 
- KEEP: `backend/logs/audit.log` (structured logging)
- DELETE: `./backend.log` (duplikat di root)
- REVIEW: `./backend/backend.log` (tergantung logging setup)

---

### 5. Environment Files (Review) 🔧

```
backend/.env                     # Active config ✅ KEEP
backend/.env.example             # Template for developers ✅ KEEP
backend/.env.production          # Production config ✅ KEEP
backend/.env.production.template # Template (duplicate?) ⚠️
```

**Recommendation**: 
- `.env.production.template` seems duplicate of `.env.example`
- REVIEW: Apakah benar-benar berbeda? Jika sama, hapus salah satu

---

### 6. Processor Files (Multiple Implementations) 🤖

**Currently Used** (by main.py and routers):
```
✅ ai_processor.py (9.7KB)        # ACTIVE - Used by routers
✅ batch_processor.py (9.1KB)     # ACTIVE - Used by main_new.py
```

**Potentially Unused** (not imported in main files):
```
❓ cloud_ai_processor.py (20KB)         # Check if used elsewhere
❓ nextgen_ocr_processor.py (17KB)      # Check if used elsewhere
❓ ocr_processor.py (13KB)              # Check if used elsewhere
❓ super_advanced_preprocessor.py (18KB) # Check if used elsewhere
❓ sync_ai_processor.py (5.5KB)         # Check if used elsewhere
```

**Action Required**: 
1. Search for imports of these files across the codebase
2. If not used → Safe to DELETE or ARCHIVE
3. If used → Keep and document

---

## 🎯 Cleanup Actions Summary

### Immediate Actions (Safe) ✅
```bash
cd /Users/yapi/Adi/App-Dev/doc-scan-ai/backend

# 1. Delete backup files
rm ai_processor.py.backup
rm ai_processor.py.old

# 2. Delete duplicate log at root
rm ../backend.log

# 3. Clean pycache of main_new
rm __pycache__/main_new.cpython-310.pyc
```

### After Confirmation (Need Review) ⚠️
```bash
# 4. Deploy refactored main.py
mv main.py main.py.backup_$(date +%Y%m%d)
mv main_new.py main.py

# 5. Check and remove unused database
# First confirm which one is active, then:
# rm doc_scan_dev.db  # or rm app.db

# 6. Check and remove unused processors
# After verifying they're not imported anywhere
```

### Optional Cleanup 🧹
```bash
# Remove old __pycache__ files
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Remove .DS_Store (macOS)
find . -name .DS_Store -delete

# Remove empty directories
find . -type d -empty -delete
```

---

## 📊 Expected Space Savings

| Category | Files | Est. Size |
|----------|-------|-----------|
| Backup files | 2 | ~20KB |
| Duplicate logs | 1 | varies |
| Main.py (keep backup) | 0 | 0KB |
| Unused processors | ? | ~73KB |
| Database (if one removed) | 1 | 300-372KB |
| **Total Potential** | **5-10** | **~400-500KB** |

---

## ⚠️ Before Deleting - Checklist

- [ ] Backup penting sudah dibuat
- [ ] Confirm database mana yang aktif
- [ ] Test main_new.py sudah berjalan
- [ ] Check processor files tidak diimport di tempat lain
- [ ] Git commit current state (safety net)

---

## 🔍 Commands to Verify Usage

### Check if processor files are used:
```bash
cd /Users/yapi/Adi/App-Dev/doc-scan-ai

# Check cloud_ai_processor usage
grep -r "cloud_ai_processor" --include="*.py" backend/

# Check nextgen_ocr_processor usage
grep -r "nextgen_ocr_processor" --include="*.py" backend/

# Check ocr_processor usage
grep -r "ocr_processor" --include="*.py" backend/

# Check super_advanced_preprocessor usage
grep -r "super_advanced_preprocessor" --include="*.py" backend/

# Check sync_ai_processor usage
grep -r "sync_ai_processor" --include="*.py" backend/
```

### Check which database is active:
```bash
# Check config
cat backend/config.py | grep -i "database\|db_path"

# Check .env
cat backend/.env | grep -i "database\|db"
```

---

## 🎯 Recommendation Priority

**HIGH PRIORITY** (Safe to delete now):
1. ✅ `ai_processor.py.backup` - Old backup
2. ✅ `ai_processor.py.old` - Old backup
3. ✅ `backend.log` at root - Duplicate

**MEDIUM PRIORITY** (After verification):
4. ⚠️ Deploy `main_new.py` as `main.py`
5. ⚠️ Remove one database file (after confirming)
6. ⚠️ Remove `.env.production.template` if duplicate

**LOW PRIORITY** (After thorough check):
7. ❓ Unused processor files (need grep verification)

---

**Next Step**: Run verification commands above to confirm what's safe to delete!
