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
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # File Security
    max_file_size_mb: int = 50  # Support rekening koran bank dengan banyak halaman
    allowed_extensions: str = "pdf,png,jpg,jpeg,tiff,bmp"  # Changed to string
    enable_virus_scan: bool = True
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    
    # OCR Configuration
    ocr_timeout_seconds: int = 120
    max_concurrent_processing: int = 5
    enable_ocr_caching: bool = True
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Production Settings
    environment: str = "development"
    debug: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"  # Changed to string
    
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