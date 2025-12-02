"""Configuration management using Pydantic Settings"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Database
    database_url: str = "sqlite:///./tax_documents.db"
    mongo_url: str = "mongodb://localhost:27017/"
    mongo_db_name: str = "tax_ocr_db"
    
    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # Upload settings
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB default
    
    # OCR settings
    google_application_credentials: Optional[str] = None
    ocr_engine: str = "google"  # Options: google, tesseract, paddleocr
    
    # Google Document AI
    google_project_id: Optional[str] = None
    google_location: str = "us"
    google_processor_id: Optional[str] = None
    
    # Smart Mapper (GPT-4o for Faktur/PPh, Claude for Rekening Koran)
    smart_mapper_enabled: bool = True
    smart_mapper_provider: str = "openai"  # openai or anthropic
    smart_mapper_model: str = "gpt-4o"
    smart_mapper_api_key: Optional[str] = None
    smart_mapper_timeout: int = 60
    smart_mapper_temperature: float = 0.1
    smart_mapper_max_tokens: int = 16000
    
    # Batch processing
    batch_processing_enabled: bool = True
    max_concurrent_jobs: int = 3
    
    # Logging
    log_level: str = "INFO"
    
    # Export formats
    export_formats: list = ["excel", "pdf"]
    
    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:3000"
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # ✅ CRITICAL FIX: Reduced chunk size for better memory management
    # OLD: 15 pages = ~2250 transactions = potential OOM
    # NEW: 8 pages = ~1200 transactions = safe memory usage
    pdf_chunk_size: int = 8  # ✅ REDUCED from 15 to 8 for large rekening koran (50+ pages, 150+ txns/page)
    enable_page_chunking: bool = True  # ✅ ENABLED: Auto-chunk files >8 pages
    
    # ✅ NEW: Smart Mapper chunking for large documents
    smart_mapper_page_threshold: int = 5  # Process 5 pages max per Claude request (5 × 150 = 750 txns)
    smart_mapper_chunk_overlap: int = 1  # Overlap 1 page between chunks for continuity
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Helper function to get upload directory
def get_upload_dir() -> str:
    """Get upload directory path, create if not exists"""
    import os
    os.makedirs(settings.upload_dir, exist_ok=True)
    return settings.upload_dir
