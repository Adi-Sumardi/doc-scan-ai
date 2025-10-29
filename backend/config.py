import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from repository root and backend/.env
load_dotenv()  # Attempt default location first for compatibility
backend_env_path = Path(__file__).resolve().parent / ".env"
if backend_env_path.exists():
    load_dotenv(dotenv_path=backend_env_path)

# Utility function for parsing boolean environment variables
def parse_bool_env(value: str, default: bool = False) -> bool:
    """Parse boolean environment variable with support for multiple formats"""
    if not value:
        return default
    return value.lower() in ('true', '1', 'yes', 'on', 'enabled')

class Settings(BaseSettings):

    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    upload_folder: str = "uploads"
    export_folder: str = "exports"
    default_ocr_engine: str = "auto"
    enable_cloud_ocr: bool = False

    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "")
    database_pool_size: int = 20
    database_max_overflow: int = 30

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    enable_redis_cache: bool = True

    # Security Configuration
    # ✅ FIX: SECRET_KEY now REQUIRED from environment - no unsafe default
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File Security
    max_file_size_mb: int = 50  # Support rekening koran bank dengan banyak halaman
    allowed_extensions: str = "pdf,png,jpg,jpeg,tiff,bmp,xlsx,xls"  # Added Excel formats for faktur pajak
    enable_virus_scan: bool = True
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    
    # OCR Configuration
    ocr_timeout_seconds: int = 120
    max_concurrent_processing: int = 10  # Increased from 5 to 10 for better throughput
    enable_ocr_caching: bool = True

    # Batch Processing Configuration
    max_zip_files: int = 100  # Maximum files in ZIP (increased from 50)
    max_zip_size_mb: int = 200  # Maximum ZIP size (increased from 100)
    max_pdf_pages_per_file: int = 15  # Maximum pages per PDF (Google Document AI limit without imageless mode)
    pdf_chunk_size: int = 15  # DISABLED: No chunking, reject files >15 pages
    enable_page_chunking: bool = False  # DISABLED: No chunking, user must split manually
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Production Settings
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    # ✅ FIX: CORS origins determined by environment, not hardcoded with localhost
    cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173" if os.getenv("ENVIRONMENT", "development").lower() == "development" else ""
    )
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    # Google Cloud AI Configuration (added to fix validation error)
    google_application_credentials: Optional[str] = None
    google_cloud_project_id: Optional[str] = None
    google_processor_location: Optional[str] = None
    google_processor_id: Optional[str] = None

    # Smart Mapper Configuration
    smart_mapper_enabled: bool = True
    smart_mapper_provider: str = "openai"
    smart_mapper_model: Optional[str] = None
    smart_mapper_api_key: Optional[str] = None
    smart_mapper_timeout: int = 60
    
    # Computed properties
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get allowed extensions as a list"""
        return [ext.strip() for ext in self.allowed_extensions.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list with proper whitespace handling"""
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        # Filter out empty strings after stripping
        return [origin for origin in origins if origin]
    
    # Use SettingsConfigDict for Pydantic v2
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra='ignore')

# Global settings instance
settings = Settings()

# ✅ FIX: Validate SECRET_KEY on startup to prevent security vulnerabilities
def validate_secret_key():
    """Validate that SECRET_KEY is properly configured"""
    # List of insecure default values that should never be used
    INSECURE_DEFAULTS = [
        "",
        "your-super-secret-key-change-in-production",
        "change-me",
        "secret",
        "secret-key",
        "dev-secret",
        "development",
    ]

    if not settings.secret_key or settings.secret_key in INSECURE_DEFAULTS:
        import secrets
        error_msg = (
            "\n" + "="*80 + "\n"
            "🚨 CRITICAL SECURITY ERROR: SECRET_KEY is not configured or uses default value!\n"
            "="*80 + "\n"
            "SECRET_KEY must be set to a cryptographically strong random value.\n\n"
            "To generate a secure SECRET_KEY, run:\n"
            "  python -c 'import secrets; print(secrets.token_urlsafe(32))'\n\n"
            "Then set it in your .env file or environment:\n"
            "  export SECRET_KEY='<generated-value>'\n\n"
            "Current value: " + (f"'{settings.secret_key}'" if settings.secret_key else "(empty)") + "\n"
            "="*80 + "\n"
        )

        # In development, generate a temporary key with warning
        if settings.environment.lower() == "development":
            temp_key = secrets.token_urlsafe(32)
            settings.secret_key = temp_key
            print("⚠️  WARNING: Using temporary SECRET_KEY for development")
            print(f"⚠️  Temporary key: {temp_key}")
            print("⚠️  This is NOT safe for production!")
            print("⚠️  Set a permanent SECRET_KEY in your .env file\n")
        else:
            # In production, refuse to start
            raise ValueError(error_msg)

    # Validate key strength (should be at least 32 bytes / 256 bits)
    if len(settings.secret_key) < 32:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"⚠️  SECRET_KEY is weak (only {len(settings.secret_key)} characters). "
            f"Recommended: at least 32 characters (256 bits)."
        )

# Validate on module load
validate_secret_key()

# Synchronize critical settings back into environment variables for SDKs that rely on them
_google_env_map = {
    'GOOGLE_APPLICATION_CREDENTIALS': settings.google_application_credentials,
    'GOOGLE_CLOUD_PROJECT_ID': settings.google_cloud_project_id,
    'GOOGLE_PROCESSOR_LOCATION': settings.google_processor_location,
    'GOOGLE_PROCESSOR_ID': settings.google_processor_id,
}

for env_key, env_value in _google_env_map.items():
    if env_value and not os.getenv(env_key):
        os.environ[env_key] = env_value

# Environment-specific configurations
def get_database_url() -> str:
    """Get database URL with proper configuration"""
    if settings.environment == "production":
        # In production, use environment variables
        return os.getenv("DATABASE_URL", settings.database_url)
    return settings.database_url

def is_production() -> bool:
    """Check if running in production environment"""
    return settings.environment.lower() == "production"

def get_upload_dir() -> str:
    """Get upload directory path"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "uploads")

def get_results_dir() -> str:
    """Get results directory path"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "results")

def get_exports_dir() -> str:
    """Get exports directory path"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "exports")