# Deployment Guide - Delete Batch Feature

## Overview

Feature delete batch telah **selesai diimplementasikan** di frontend dan backend. Tinggal deploy ke production server.

## What's New

### Frontend Changes ✅
- SweetAlert2 confirmation dialog untuk delete batch
- Delete button di History page (hanya untuk batch error/failed)
- Beautiful loading/success/error dialogs
- Indonesian language messages
- Improved error handling for 405 and other errors

### Backend Changes ✅
- DELETE endpoint `/api/batches/{batch_id}` implemented
- Security features:
  - Authentication & Authorization required
  - Only error/failed batches can be deleted (safety measure)
  - Owner or admin verification
  - Path validation for file deletion
- Cascade delete: scan_results → document_files → batch
- Physical file cleanup from disk
- Transaction safety with automatic rollback on error
- Comprehensive logging for audit trail

## Deployment Steps

### 1. Deploy Backend (CRITICAL - Do this first!)

Via Termius, connect to production server and run:

```bash
cd /var/www/docscan
sudo -u docScan git pull origin master
sudo systemctl restart docscan-backend
sudo systemctl status docscan-backend
```

**Verify backend is running:**
```bash
# Check logs for any errors
sudo journalctl -u docscan-backend -n 50 --no-pager
```

### 2. Frontend Already Deployed ✅

Frontend dengan SweetAlert2 sudah di-deploy sebelumnya. Tidak perlu deploy ulang.

## Testing

### Test Delete Functionality:

1. **Via Browser (Recommended):**
   - Login ke https://docscan.adilabs.id
   - Go to History page
   - Filter status "Error"
   - Click Delete button (🗑️ icon) pada batch yang error
   - Verify SweetAlert2 dialog muncul dengan batch details
   - Click "Ya, Hapus!"
   - Verify loading dialog appears
   - Verify success dialog: "Batch #xxx telah dihapus"
   - Verify batch hilang dari table
   - Check database untuk confirm deletion

2. **Via curl (Advanced):**
```bash
# Get token first
TOKEN=$(curl -X POST https://docscan.adilabs.id/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your-username","password":"your-password"}' \
  | jq -r '.access_token')

# Test delete
curl -X DELETE https://docscan.adilabs.id/api/batches/BATCH_ID \
  -H "Authorization: Bearer $TOKEN" \
  -v
```

## Security Features

1. **Authentication Required**: Must be logged in
2. **Authorization Check**: Only batch owner or admin can delete
3. **Status Validation**: Only error/failed batches allowed (prevents accidental deletion)
4. **Path Validation**: Files only deleted if within upload directory
5. **Transaction Safety**: Database rollback on any error
6. **Audit Logging**: All deletions logged with username

## Files Changed

### Backend:
- backend/routers/batches.py (added delete_batch function)

### Frontend:
- src/pages/History.tsx (SweetAlert2 integration)
- src/context/DocumentContext.tsx (deleteBatch with 405 handling)
- src/services/api.ts (deleteBatch API call)
- package.json (added sweetalert2 dependency)

## Commits

```
c76c7c2 - docs: Update backend delete documentation - implementation completed
fefebf3 - feat: Implement DELETE /api/batches/{batch_id} endpoint with security checks
e7f3e87 - feat: Add SweetAlert2 for delete batch confirmation
f346cbd - feat: Add delete batch functionality for error/failed batches
```

---

**Deployment Status**: Ready for Production ✅
