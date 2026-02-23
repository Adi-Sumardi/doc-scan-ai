"""
MySQL Database Configuration and Setup for Doc-Scan-AI
Production-grade database with comprehensive models
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import LONGTEXT
import os
from datetime import datetime
from typing import Generator
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Helper function for database compatibility
def get_text_column():
    """Return appropriate text column type based on database engine"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./doc_scan_dev.db")
    if "sqlite" in db_url.lower():
        return Text  # SQLite uses TEXT for large text
    else:
        return LONGTEXT  # MySQL uses LONGTEXT

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./doc_scan_dev.db"  # ✅ FIX: SQLite default (no credentials in code)
)

# ✅ FIX: Enhanced database engine configuration with proper timeouts
# This prevents connection pool exhaustion and hanging connections
is_mysql = "mysql" in DATABASE_URL.lower()
is_sqlite = "sqlite" in DATABASE_URL.lower()

# Prepare connect_args based on database type
connect_args = {}
if is_mysql:
    # MySQL-specific connection arguments
    connect_args = {
        'connect_timeout': 10,      # ✅ FIX: Max 10s to establish connection
        'read_timeout': 300,         # ✅ FIX: Max 5min to read query results
        'write_timeout': 300,        # ✅ FIX: Max 5min to write data
    }
elif is_sqlite:
    # SQLite-specific: enable thread-safety check
    connect_args = {'check_same_thread': False}

# Create engine with optimized settings for production
engine = create_engine(
    DATABASE_URL,
    pool_size=20,                    # Max 20 persistent connections in pool
    max_overflow=30,                 # Max 30 additional connections when pool is full
    pool_pre_ping=True,              # ✅ Verify connection is alive before using
    pool_recycle=1800,               # ✅ FIX: Recycle connections every 30min (was 1 hour)
    pool_timeout=30,                 # ✅ FIX: Max 30s wait for connection from pool
    connect_args=connect_args,       # ✅ FIX: Database-specific connection timeouts
    echo=False                       # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger = logging.getLogger(__name__)

# Database Models for Production

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

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
    extracted_text = Column(get_text_column(), nullable=True)
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

# ==================== PPN Reconciliation Models ====================

class PPNProject(Base):
    """PPN Reconciliation Project"""
    __tablename__ = "ppn_projects"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    # Project metadata
    name = Column(String(255), nullable=False)
    periode_start = Column(DateTime, nullable=False)
    periode_end = Column(DateTime, nullable=False)
    company_npwp = Column(String(20), nullable=False)

    # Status tracking
    status = Column(String(50), default="draft", index=True)  # draft, in_progress, completed, archived

    # Counts for each point
    point_a_count = Column(Integer, default=0)
    point_b_count = Column(Integer, default=0)
    point_c_count = Column(Integer, default=0)
    point_e_count = Column(Integer, default=0)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class PPNDataSource(Base):
    """PPN Data Source"""
    __tablename__ = "ppn_data_sources"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)

    # Source identification
    point_type = Column(String(20), nullable=False, index=True)  # point_a_b, point_c, point_e
    source_type = Column(String(20), nullable=False)  # scanned, upload

    # File reference
    excel_export_id = Column(String(36), nullable=True)
    uploaded_file_path = Column(String(500), nullable=True)

    # File metadata
    filename = Column(String(255), nullable=False)
    row_count = Column(Integer, default=0)

    # Processing status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class PPNPointA(Base):
    """Point A: Faktur Pajak Keluaran (Output Tax)"""
    __tablename__ = "ppn_point_a"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    data_source_id = Column(String(36), nullable=False, index=True)

    # Faktur Pajak Keluaran data
    nomor_faktur = Column(String(100), index=True)
    tanggal_faktur = Column(DateTime, index=True)
    npwp_seller = Column(String(20), index=True)
    nama_seller = Column(String(200))
    npwp_buyer = Column(String(20), index=True)
    nama_buyer = Column(String(200))

    # Amount fields
    dpp = Column(Float)
    ppn = Column(Float)
    total = Column(Float)

    # Reconciliation status
    is_matched = Column(Boolean, default=False, index=True)
    matched_with_point_c_id = Column(String(36), nullable=True)
    match_confidence = Column(Float, nullable=True)
    match_type = Column(String(50), nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PPNPointB(Base):
    """Point B: Faktur Pajak Masukan (Input Tax)"""
    __tablename__ = "ppn_point_b"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    data_source_id = Column(String(36), nullable=False, index=True)

    # Faktur Pajak Masukan data
    nomor_faktur = Column(String(100), index=True)
    tanggal_faktur = Column(DateTime, index=True)
    npwp_seller = Column(String(20), index=True)
    nama_seller = Column(String(200))
    npwp_buyer = Column(String(20), index=True)
    nama_buyer = Column(String(200))

    # Amount fields
    dpp = Column(Float)
    ppn = Column(Float)
    total = Column(Float)

    # Reconciliation status
    is_matched = Column(Boolean, default=False, index=True)
    matched_with_point_e_id = Column(String(36), nullable=True)
    match_confidence = Column(Float, nullable=True)
    match_type = Column(String(50), nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PPNPointC(Base):
    """Point C: Bukti Potong Lawan Transaksi"""
    __tablename__ = "ppn_point_c"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    data_source_id = Column(String(36), nullable=False, index=True)

    # Bukti Potong data
    nomor_bukti_potong = Column(String(100), index=True)
    tanggal_bukti_potong = Column(DateTime, index=True)
    npwp_pemotong = Column(String(20), index=True)
    nama_pemotong = Column(String(200))
    npwp_dipotong = Column(String(20), index=True)
    nama_dipotong = Column(String(200))

    # Amount fields
    jumlah_penghasilan_bruto = Column(Float)
    tarif_pph = Column(Float)
    pph_dipotong = Column(Float)

    # Reconciliation status
    is_matched = Column(Boolean, default=False, index=True)
    matched_with_point_a_id = Column(String(36), nullable=True)
    match_confidence = Column(Float, nullable=True)
    match_type = Column(String(50), nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PPNPointE(Base):
    """Point E: Rekening Koran (Bank Statement)"""
    __tablename__ = "ppn_point_e"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    data_source_id = Column(String(36), nullable=False, index=True)

    # Rekening Koran data
    tanggal_transaksi = Column(DateTime, index=True)
    keterangan = Column(Text)
    nominal = Column(Float, index=True)
    jenis_transaksi = Column(String(20))  # debit, credit

    # Bank details
    bank_name = Column(String(100))
    account_number = Column(String(100))

    # Reconciliation status
    is_matched = Column(Boolean, default=False, index=True)
    matched_with_point_b_id = Column(String(36), nullable=True)
    match_confidence = Column(Float, nullable=True)
    match_type = Column(String(50), nullable=True)

    # Metadata
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== Reconciliation Chat Models ====================

class ReconciliationSession(Base):
    """Chat-based reconciliation session"""
    __tablename__ = "reconciliation_sessions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Reconciliation")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReconciliationMessage(Base):
    """Message in a reconciliation chat session"""
    __tablename__ = "reconciliation_messages"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)  # [{name, size, detected_type, row_count}]
    results = Column(JSON, nullable=True)  # reconciliation results (assistant only)
    created_at = Column(DateTime, default=datetime.utcnow)


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
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def get_database_info():
    """Get database information"""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        result = db.execute(text("SELECT VERSION() as version, DATABASE() as database")).fetchone()
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