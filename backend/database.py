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

# Tax Reconciliation Models

class ReconciliationProject(Base):
    """Proyek rekonsiliasi pajak"""
    __tablename__ = "reconciliation_projects"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)

    # Status
    status = Column(String(20), default="active", index=True)  # active, completed, archived

    # Statistics
    total_invoices = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    unmatched_invoices = Column(Integer, default=0)
    unmatched_transactions = Column(Integer, default=0)

    # Totals
    total_invoice_amount = Column(Float, default=0.0)
    total_transaction_amount = Column(Float, default=0.0)
    variance_amount = Column(Float, default=0.0)

    # Metadata
    user_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class TaxInvoice(Base):
    """Faktur pajak untuk rekonsiliasi"""
    __tablename__ = "tax_invoices"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    scan_result_id = Column(String(36), nullable=True, index=True)  # Link ke hasil scan

    # Invoice details
    invoice_number = Column(String(100), nullable=False, index=True)
    invoice_date = Column(DateTime, nullable=False, index=True)
    invoice_type = Column(String(20), nullable=True)  # masukan/keluaran

    # Vendor/Customer info
    vendor_name = Column(String(255), nullable=True, index=True)
    vendor_npwp = Column(String(50), nullable=True, index=True)

    # Amounts
    dpp = Column(Float, nullable=False)  # Dasar Pengenaan Pajak
    ppn = Column(Float, nullable=False)  # PPN
    total_amount = Column(Float, nullable=False, index=True)

    # Matching status
    match_status = Column(String(20), default="unmatched", index=True)  # unmatched, auto_matched, manual_matched, disputed
    match_confidence = Column(Float, default=0.0)
    matched_transaction_id = Column(String(36), nullable=True, index=True)
    matched_by = Column(String(36), nullable=True)  # user_id
    matched_at = Column(DateTime, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)
    dispute_reason = Column(Text, nullable=True)

    # AI Processing Metadata (V2.0 - Dual AI Integration)
    ai_model_used = Column(String(50), default="gpt-4o")  # gpt-4o for tax invoices
    extraction_confidence = Column(Float, nullable=True)  # AI extraction confidence 0.0-100.0

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BankTransaction(Base):
    """Transaksi rekening koran untuk rekonsiliasi"""
    __tablename__ = "bank_transactions"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)
    scan_result_id = Column(String(36), nullable=True, index=True)  # Link ke hasil scan

    # Bank details
    bank_name = Column(String(100), nullable=True, index=True)
    account_number = Column(String(50), nullable=True)
    account_holder = Column(String(255), nullable=True)

    # Transaction details
    transaction_date = Column(DateTime, nullable=False, index=True)
    posting_date = Column(DateTime, nullable=True)
    effective_date = Column(DateTime, nullable=True)

    description = Column(Text, nullable=True)
    transaction_type = Column(String(50), nullable=True)
    reference_number = Column(String(100), nullable=True, index=True)

    # Amounts
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    balance = Column(Float, nullable=True)

    # Matching status
    match_status = Column(String(20), default="unmatched", index=True)  # unmatched, auto_matched, manual_matched, disputed
    match_confidence = Column(Float, default=0.0)
    matched_invoice_id = Column(String(36), nullable=True, index=True)
    matched_by = Column(String(36), nullable=True)  # user_id
    matched_at = Column(DateTime, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)
    dispute_reason = Column(Text, nullable=True)

    # AI Extracted Fields (V2.0 - Claude AI Integration)
    extracted_vendor_name = Column(String(255), nullable=True, index=True)  # AI-extracted from description
    extracted_invoice_number = Column(String(100), nullable=True)  # AI-extracted from reference/description
    ai_model_used = Column(String(50), default="claude-sonnet-4")  # claude for bank statements
    extraction_confidence = Column(Float, nullable=True)  # AI extraction confidence 0.0-100.0

    # Metadata
    branch_code = Column(String(20), nullable=True)
    teller = Column(String(50), nullable=True)
    additional_info = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ReconciliationMatch(Base):
    """Match antara faktur pajak dan transaksi bank"""
    __tablename__ = "reconciliation_matches"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), nullable=False, index=True)

    # Match details
    invoice_id = Column(String(36), nullable=False, index=True)
    transaction_id = Column(String(36), nullable=False, index=True)

    # Match quality
    match_type = Column(String(20), nullable=False, index=True)  # auto, manual, suggested
    match_confidence = Column(Float, default=0.0, index=True)
    match_score = Column(Float, default=0.0)  # Detail scoring

    # Variance
    amount_variance = Column(Float, default=0.0)
    date_variance_days = Column(Integer, default=0)

    # Match criteria scores
    score_amount = Column(Float, default=0.0)
    score_date = Column(Float, default=0.0)
    score_vendor = Column(Float, default=0.0)
    score_reference = Column(Float, default=0.0)

    # Status
    status = Column(String(20), default="active", index=True)  # active, rejected, confirmed
    confirmed = Column(Boolean, default=False)
    confirmed_by = Column(String(36), nullable=True)
    confirmed_at = Column(DateTime, nullable=True)

    # Notes
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Metadata
    matched_by = Column(String(36), nullable=True)  # user_id
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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