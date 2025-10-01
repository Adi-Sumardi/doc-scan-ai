"""
Database migration script to add User table and update existing tables
Run this script to update your database schema
"""
from database import Base, engine, SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Create or update database schema"""
    try:
        logger.info("🚀 Starting database migration...")
        
        # Create all tables (will only create new ones, existing ones are unchanged)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/updated successfully")
        
        # Check if migration is needed for existing tables
        db = SessionLocal()
        try:
            # Check if user_id column exists in batches table
            result = db.execute(text("SHOW COLUMNS FROM batches LIKE 'user_id'"))
            if result.rowcount == 0:
                logger.info("Adding user_id column to batches table...")
                db.execute(text("ALTER TABLE batches ADD COLUMN user_id VARCHAR(36) AFTER error_message"))
                db.execute(text("CREATE INDEX idx_batches_user_id ON batches(user_id)"))
                logger.info("✅ Added user_id to batches table")
            else:
                logger.info("✅ user_id column already exists in batches table")
            
            db.commit()
            logger.info("🎉 Migration completed successfully!")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Migration error: {e}")
            # For SQLite, different approach
            if "sqlite" in str(engine.url).lower():
                logger.info("SQLite detected - recreating tables")
                Base.metadata.drop_all(bind=engine)
                Base.metadata.create_all(bind=engine)
                logger.info("✅ SQLite tables recreated")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_database()
