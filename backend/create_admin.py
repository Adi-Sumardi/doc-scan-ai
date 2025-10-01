"""
Create Admin User
Run this script to create an admin user in the database
"""
import sys
sys.path.append('/Users/yapi/Adi/App-Dev/doc-scan-ai/backend')

from database import SessionLocal, User
from auth import get_password_hash
import uuid
from datetime import datetime

def create_admin_user():
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print(f"❌ Admin user already exists: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Is Admin: {existing_admin.is_admin}")
            return
        
        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@docscan.ai",
            hashed_password=get_password_hash("admin123"),  # Change this password!
            full_name="System Administrator",
            is_active=True,
            is_admin=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Password: admin123")
        print(f"   Is Admin: {admin_user.is_admin}")
        print("\n⚠️  IMPORTANT: Change the admin password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()
