"""
Admin Router
Handles admin-only endpoints for user management and system statistics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import secrets
import string
import logging

from database import get_db, Batch, DocumentFile, User
from auth import get_current_active_user, get_password_hash
from audit_logger import log_user_status_change, log_password_reset
from security import SecurityValidator

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ==================== Dependency Functions ====================

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Dependency to verify admin access"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_user_by_id_from_path(user_id: str, db: Session = Depends(get_db)):
    """Dependency to get a user by ID from the URL path and handle not found cases."""
    # Centralized validation
    if SecurityValidator.check_sql_injection(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==================== Admin Endpoints ====================

@router.get("/users")
async def get_all_users(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users with their activity stats (Admin only)"""
    users = db.query(User).all()
    
    # Get activity stats for each user
    user_list = []
    for user in users:
        # Count batches created by user
        batch_count = db.query(Batch).filter(Batch.user_id == user.id).count()
        
        # Get latest batch
        latest_batch = db.query(Batch).filter(Batch.user_id == user.id).order_by(Batch.created_at.desc()).first()
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "total_batches": batch_count,
            "last_activity": latest_batch.created_at if latest_batch else None
        }
        user_list.append(user_data)
    
    return user_list


@router.get("/users/{user_id}/activities")
async def get_user_activities(
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed activity history for a specific user (Admin only)"""
    # Get all batches by user
    batches = db.query(Batch).filter(Batch.user_id == user.id).order_by(Batch.created_at.desc()).all()
    
    batch_list = []
    for batch in batches:
        # Get file count for this batch
        files = db.query(DocumentFile).filter(DocumentFile.batch_id == batch.id).all()
        
        batch_data = {
            "id": batch.id,
            "status": batch.status,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at,
            "file_count": len(files),
            "processed_files": batch.processed_files,
            "file_names": [f.name for f in files[:5]],  # First 5 files
            "processing_time": batch.total_processing_time
        }
        batch_list.append(batch_data)
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login
        },
        "batches": batch_list,
        "total_batches": len(batch_list)
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    is_active: bool,
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update user active status (Admin only)"""
    # Prevent admin from deactivating themselves
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own status")
    
    user.is_active = is_active
    db.commit()
    
    # Audit log for admin action
    log_user_status_change(
        admin=current_admin.username,
        target=user.username,
        new_status="active" if is_active else "inactive",
        ip="admin_action"
    )
    
    logger.info(f"Admin {current_admin.username} changed user {user.username} status to {'active' if is_active else 'inactive'}")
    
    return {"message": f"User {user.username} has been {'activated' if is_active else 'deactivated'}"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    new_password: str,
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Reset user password (Admin only) with password strength validation"""
    # Validate password strength
    SecurityValidator.validate_password_strength(new_password)
    
    # Hash new password
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Audit log for admin action
    log_password_reset(
        admin=current_admin.username,
        target=user.username,
        ip="admin_action"
    )
    
    logger.info(f"Admin {current_admin.username} reset password for user {user.username}")
    
    return {
        "message": f"Password for user {user.username} has been reset successfully",
        "username": user.username,
        "email": user.email
    }


@router.post("/users/{user_id}/generate-temp-password")
async def generate_temp_password(
    user: User = Depends(get_user_by_id_from_path),
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Generate and set a temporary password for user (Admin only)"""
    # Generate secure random password (10 chars: letters, digits, special chars)
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    temp_password = ''.join(secrets.choice(alphabet) for i in range(10))
    
    # Hash and set new password
    user.hashed_password = get_password_hash(temp_password)
    db.commit()
    
    logger.info(f"Admin {current_admin.username} generated temporary password for user {user.username}")
    
    return {
        "message": f"Temporary password generated for user {user.username}",
        "username": user.username,
        "email": user.email,
        "temp_password": temp_password,
        "note": "This password is shown only once. Please share it securely with the user."
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get overall system statistics (Admin only)"""
    # Count users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    
    # Count batches
    total_batches = db.query(Batch).count()
    completed_batches = db.query(Batch).filter(Batch.status == "completed").count()
    processing_batches = db.query(Batch).filter(Batch.status == "processing").count()
    partial_batches = db.query(Batch).filter(Batch.status == "partial").count()
    failed_batches = db.query(Batch).filter(Batch.status.in_(["failed", "error"])).count()
    
    # Count files
    total_files = db.query(DocumentFile).count()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_batches = db.query(Batch).filter(Batch.created_at >= seven_days_ago).count()
    recent_users = db.query(User).filter(User.created_at >= seven_days_ago).count()
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "admins": admin_users,
            "new_this_week": recent_users
        },
        "batches": {
            "total": total_batches,
            "completed": completed_batches,
            "processing": processing_batches,
            "partial": partial_batches,
            "failed": failed_batches,
            "this_week": recent_batches
        },
        "files": {
            "total": total_files
        }
    }
