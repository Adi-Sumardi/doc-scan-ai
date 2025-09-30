"""
Database migration script for Doc Scan AI
"""
from database import Base, engine, SessionLocal
import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    logger.info("🔄 Starting database migration...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Successfully created all tables")
        
        # Verify tables
        with SessionLocal() as session:
            # Get list of all tables using inspector
            from sqlalchemy import inspect, text
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            logger.info(f"📋 Created tables: {', '.join(tables)}")
            
            # Test connection with MySQL
            session.execute(text("SELECT 1"))
            logger.info("✅ Database connection verified")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        raise
    
    logger.info("✅ Migration completed successfully")

if __name__ == "__main__":
    run_migrations()