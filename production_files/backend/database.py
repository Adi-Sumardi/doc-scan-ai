"""
MySQL Database Configuration and Setup for Doc-Scan-AI
Production-grade database with comprehensive models
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float, Boolean
from sqlalchemy.dialects.mysql import LONGTEXT
import os
from datetime import datetime
from typing import Generator
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://docuser:docpass123@localhost:3306/docscan_db"
)

# Create engine with optimized settings for production
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger(__name__)

# Database Models for Production

class Batch(Base):
    """Batch model for document processing"""
    __tablename__ = "batches"
    
    id = Column(String(36), primary_key=True, index=True)
    status = Column(String(20), default="processing", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    user_id = Column(String(36), nullable=True, index=True)  # For future auth
    
    # Metadata
    processing_start = Column(DateTime, nullable=True)
    processing_end = Column(DateTime, nullable=True)
    total_processing_time = Column(Float, nullable=True)  # seconds

class DocumentFile(Base):
    """Document file model"""
    __tablename__ = "document_files"
    
    id = Column(String(36), primary_key=True, index=True)
    batch_id = Column(String(36), index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)
    progress = Column(Integer, default=0)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)  # For deduplication
    mime_type = Column(String(100), nullable=True)
    
    # Security checks
    virus_scan_status = Column(String(20), default="pending")  # pending, clean, infected
    virus_scan_result = Column(Text, nullable=True)
    
    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_start = Column(DateTime, nullable=True)
    processing_end = Column(DateTime, nullable=True)
    processing_time = Column(Float, nullable=True)  # seconds
    
    result_id = Column(String(36), nullable=True, index=True)

class ScanResult(Base):
    """Scan result model with comprehensive metadata"""
    __tablename__ = "scan_results"
    
    id = Column(String(36), primary_key=True, index=True)
    batch_id = Column(String(36), index=True)
    document_file_id = Column(String(36), index=True)
    document_type = Column(String(50), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    
    # OCR and extraction data
    extracted_text = Column(LONGTEXT, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0, index=True)
    
    # AI Processing metadata
    ocr_engine_used = Column(String(50), nullable=True)
    processing_version = Column(String(20), default="1.0")
    field_count = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    ocr_processing_time = Column(Float, nullable=True)  # seconds
    parsing_processing_time = Column(Float, nullable=True)  # seconds
    total_processing_time = Column(Float, nullable=True)  # seconds
    
    # Export tracking
    exported_excel = Column(Boolean, default=False)
    exported_pdf = Column(Boolean, default=False)
    export_count = Column(Integer, default=0)

class ProcessingLog(Base):
    """Comprehensive processing logs"""
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(36), index=True)
    file_id = Column(String(36), index=True)
    level = Column(String(10), index=True)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    component = Column(String(50), index=True)  # OCR, PARSER, SECURITY, etc.
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Additional context
    processing_step = Column(String(50), nullable=True)
    error_code = Column(String(20), nullable=True)
    execution_time = Column(Float, nullable=True)

class SystemMetrics(Base):
    """System performance metrics"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Performance metrics
    total_documents_processed = Column(Integer, default=0)
    average_confidence = Column(Float, nullable=True)
    average_processing_time = Column(Float, nullable=True)
    
    # System health
    memory_usage_mb = Column(Float, nullable=True)
    disk_usage_mb = Column(Float, nullable=True)
    active_batches = Column(Integer, default=0)
    
    # OCR Engine metrics
    ocr_success_rate = Column(Float, nullable=True)
    ocr_average_time = Column(Float, nullable=True)

# Database utility functions

def get_db() -> Generator[Session, None, None]:
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def get_database_info():
    """Get database information"""
    try:
        db = SessionLocal()
        result = db.execute("SELECT VERSION() as version, DATABASE() as database").fetchone()
        db.close()
        return {
            "version": result.version if result else "Unknown",
            "database": result.database if result else "Unknown",
            "status": "connected"
        }
    except Exception as e:
        return {
            "version": "Unknown",
            "database": "Unknown", 
            "status": f"error: {str(e)}"
        }

# Production-grade connection pooling
def init_database():
    """Initialize database with proper error handling"""
    try:
        # Test connection first
        if not test_connection():
            raise Exception("Database connection test failed")
        
        # Create tables
        if not create_tables():
            raise Exception("Table creation failed")
            
        logger.info("🚀 Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    # Test database setup
    print("🔍 Testing MySQL Database Setup...")
    print(f"📊 Database Info: {get_database_info()}")
    
    if init_database():
        print("✅ Database setup successful!")
    else:
        print("❌ Database setup failed!")