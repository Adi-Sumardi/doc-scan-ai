#!/usr/bin/env python3
"""
Fresh Start Migration Script
Drops all tables, creates fresh schema, and creates admin user
"""
import sys
from database import SessionLocal, engine, Base, User
from auth import get_password_hash, verify_password  # Use the SAME pwd_context as main app!
import uuid
from datetime import datetime

def fresh_start():
    print("🔥 FRESH START - Clean Slate Migration")
    print("=" * 60)
    
    # Step 1: Drop all tables
    print("\n1️⃣ Dropping all existing tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("   ✅ All tables dropped!")
    except Exception as e:
        print(f"   ⚠️  Drop warning: {e}")
    
    # Step 2: Create all tables fresh
    print("\n2️⃣ Creating fresh database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        print("   ✅ All tables created!")
        
        # List tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"   📋 Tables: {', '.join(tables)}")
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        return False
    
    # Step 3: Create admin user
    print("\n3️⃣ Creating admin user...")
    db = SessionLocal()
    
    try:
        # Generate password hash
        password = "admin123"
        hashed_password = get_password_hash(password)
        
        print(f"   🔐 Password: {password}")
        print(f"   🔑 Hash: {hashed_password[:50]}...")
        
        # Create admin
        admin = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@docscan.ai",
            hashed_password=hashed_password,
            full_name="System Administrator",
            is_active=True,
            is_admin=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("   ✅ Admin user created!")
        print(f"      ID: {admin.id}")
        print(f"      Username: {admin.username}")
        print(f"      Email: {admin.email}")
        print(f"      Is Admin: {admin.is_admin}")
        print(f"      Is Active: {admin.is_active}")
        
        # Step 4: Verify password
        print("\n4️⃣ Verifying password hash...")
        if verify_password(password, admin.hashed_password):
            print("   ✅ Password verification: PASSED!")
        else:
            print("   ❌ Password verification: FAILED!")
            return False
            
        # Step 5: Test database query
        print("\n5️⃣ Testing database query...")
        test_user = db.query(User).filter(User.username == "admin").first()
        if test_user:
            print(f"   ✅ Query successful: {test_user.username}")
            
            # Test password verification from database
            if verify_password(password, test_user.hashed_password):
                print("   ✅ Database password verification: PASSED!")
            else:
                print("   ❌ Database password verification: FAILED!")
                print(f"      DB Hash: {test_user.hashed_password[:50]}...")
                print(f"      Created Hash: {hashed_password[:50]}...")
                return False
        else:
            print("   ❌ Query failed: User not found!")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 FRESH START COMPLETE!")
        print("=" * 60)
        print(f"\n✅ Login with:")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"\n🚀 Ready to test!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = fresh_start()
    sys.exit(0 if success else 1)
