# Backend: Delete Batch Endpoint ✅

## Status: COMPLETED ✅

**Implementation Date**: 2025-10-11

DELETE endpoint `/api/batches/{batch_id}` telah diimplementasikan di `backend/routers/batches.py:250-350`

## Previous Issue (RESOLVED)
Frontend sudah mengirim request `DELETE /api/batches/{batch_id}` tapi backend mengembalikan **405 Method Not Allowed**.

Frontend membutuhkan endpoint untuk menghapus batch yang error/failed.

## Required Backend Changes

### 1. Add DELETE endpoint di backend

**File**: `backend/main.py` atau `backend/routers/batches.py`

```python
@app.delete("/api/batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a batch and all associated results.
    Only error/failed batches should be deletable.
    """
    # 1. Get batch from database
    batch = db.query(Batch).filter(Batch.id == batch_id).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # 2. Check if batch belongs to current user (for security)
    if batch.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this batch")

    # 3. Optional: Only allow deletion of error/failed batches
    # if batch.status not in ['error', 'failed']:
    #     raise HTTPException(status_code=400, detail="Only error or failed batches can be deleted")

    # 4. Delete associated results first (cascade)
    db.query(ScanResult).filter(ScanResult.batch_id == batch_id).delete()

    # 5. Delete batch files from storage (optional)
    # import os
    # import shutil
    # batch_folder = f"uploads/{batch_id}"
    # if os.path.exists(batch_folder):
    #     shutil.rmtree(batch_folder)

    # 6. Delete batch from database
    db.delete(batch)
    db.commit()

    return {"message": f"Batch {batch_id} deleted successfully"}
```

### 2. Update Database Models (jika perlu)

Pastikan ada foreign key cascade delete:

```python
# In models.py
class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(String, primary_key=True)
    batch_id = Column(String, ForeignKey("batches.id", ondelete="CASCADE"))
    # ... other fields
```

### 3. Test Endpoint

**Test dengan curl:**
```bash
# Get token first
TOKEN=$(curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | jq -r '.access_token')

# Test delete batch
curl -X DELETE http://localhost:8000/api/batches/{batch_id} \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "message": "Batch {batch_id} deleted successfully"
}
```

## Security Considerations

1. **Authentication**: Endpoint harus require authentication
2. **Authorization**: User hanya bisa delete batch milik sendiri (kecuali admin)
3. **Status Check**: Pertimbangkan hanya allow delete untuk batch dengan status error/failed
4. **Cascade Delete**: Pastikan results dan files terkait ikut terhapus
5. **Audit Log**: Catat siapa yang menghapus batch (optional)

## Current Implementation Status

### Frontend ✅
- ✅ API call ke `DELETE /api/batches/{batch_id}`
- ✅ SweetAlert2 confirmation dialog
- ✅ Loading state saat delete
- ✅ Success/error handling
- ✅ Auto-remove dari UI setelah berhasil
- ✅ Hanya muncul untuk batch error/failed

### Backend ✅
- ✅ DELETE endpoint `/api/batches/{batch_id}` (backend/routers/batches.py:250-350)
- ✅ Authentication & Authorization checks
- ✅ Only error/failed batches can be deleted
- ✅ Owner or admin verification
- ✅ Physical file deletion from disk
- ✅ Cascade delete: scan_results → document_files → batch
- ✅ Transaction safety with rollback
- ✅ Comprehensive logging
- ✅ Indonesian error messages

## Deployment Required

Backend code sudah committed dan pushed ke GitHub. Deploy ke production dengan:

```bash
cd /var/www/docscan
sudo -u docScan git pull origin master
sudo systemctl restart docscan-backend
```

Atau gunakan script: `bash deploy-backend-delete.sh`

## Testing After Implementation

1. Login ke aplikasi
2. Go to History page
3. Filter status "Error"
4. Click Delete button pada batch yang error
5. Confirm di SweetAlert dialog
6. Batch harus terhapus dari database dan UI
7. Check database untuk memastikan batch dan results terhapus
