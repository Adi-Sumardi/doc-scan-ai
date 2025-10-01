#!/bin/bash
# ===================================================================
# 🚀 Setup Production Environment Configuration
# ===================================================================
# This script creates backend/.env file on production server
# Run this script on production server: bash setup_production_env.sh
# ===================================================================

set -e

BACKEND_DIR="/var/www/docscan/backend"
ENV_FILE="$BACKEND_DIR/.env"
CONFIG_DIR="$BACKEND_DIR/config"

echo "🔧 Setting up production environment configuration..."
echo ""

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Error: Backend directory not found: $BACKEND_DIR"
    exit 1
fi

# Create config directory if not exists
if [ ! -d "$CONFIG_DIR" ]; then
    echo "📁 Creating config directory..."
    mkdir -p "$CONFIG_DIR"
fi

# Backup existing .env if it exists
if [ -f "$ENV_FILE" ]; then
    BACKUP_FILE="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "💾 Backing up existing .env to: $BACKUP_FILE"
    cp "$ENV_FILE" "$BACKUP_FILE"
fi

# Create new .env file
echo "✍️  Creating new production .env file..."
cat > "$ENV_FILE" << 'EOF'
# ===================================================================
# 🚀 Doc Scan AI - Production Environment Configuration
# ===================================================================
# Server: VPS (/var/www/docscan)
# Domain: docscan.adilabs.id
# ===================================================================

# --- General App Settings ---
NODE_ENV=production
DOMAIN=docscan.adilabs.id
FRONTEND_URL=https://docscan.adilabs.id
BACKEND_URL=https://docscan.adilabs.id/api

# --- Database Configuration ---
# MySQL Production Database
DATABASE_URL=mysql+pymysql://docuser:docpass123@localhost:3306/docscan_db

# --- Redis Cache Configuration ---
# Redis for caching and rate limiting (uncomment if Redis is installed)
# REDIS_URL=redis://localhost:6379/0

# --- Security Settings ---
# Generate secure key with: openssl rand -hex 32
SECRET_KEY=REPLACE_THIS_WITH_SECURE_KEY_GENERATED_BY_OPENSSL
ALGORITHM=HS256

# --- CORS Configuration ---
# Allow requests from these origins
CORS_ORIGINS=https://docscan.adilabs.id,https://www.docscan.adilabs.id

# --- File Upload Configuration ---
UPLOAD_FOLDER=/var/www/docscan/uploads
EXPORT_FOLDER=/var/www/docscan/exports
MAX_FILE_SIZE=10485760

# --- Logging Configuration ---
LOG_LEVEL=INFO
LOG_FILE=/var/www/docscan/backend/logs/docscan.log

# ===================================================================
# 🤖 Google Cloud Document AI Configuration
# ===================================================================
# Primary OCR Engine - Google Document AI for high accuracy

# Enable Cloud OCR Processing
ENABLE_CLOUD_OCR=true
DEFAULT_OCR_ENGINE=google_doc_ai

# Google Cloud Credentials
# Path to your service account JSON key file
GOOGLE_APPLICATION_CREDENTIALS=/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Google Cloud Project Configuration
GOOGLE_CLOUD_PROJECT=automation-ai-pajak
GOOGLE_CLOUD_PROJECT_ID=automation-ai-pajak

# Document AI Processor Configuration
GOOGLE_PROCESSOR_ID=831a22639bf6ff6f
GOOGLE_PROCESSOR_LOCATION=us

# Optional: Google Cloud Storage (for large file processing)
# GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
# GOOGLE_CLOUD_STORAGE_PREFIX=docscan/

# ===================================================================
# 📄 OCR Engine Configuration
# ===================================================================
# OCR Processing Settings
OCR_CONFIDENCE_THRESHOLD=0.6
MAX_PROCESSING_TIME=300

# OCR Engine Priority (comma-separated list)
# Engines: google_doc_ai, paddleocr, easyocr, tesseract, rapidocr
OCR_ENGINE_PRIORITY=google_doc_ai,paddleocr,easyocr

# PaddleOCR Settings
PADDLE_OCR_USE_ANGLE_CLS=true
PADDLE_OCR_USE_GPU=false
PADDLE_OCR_LANG=en

# EasyOCR Settings
EASYOCR_GPU=false
EASYOCR_LANGS=en

# ===================================================================
# 🔒 Security & Rate Limiting
# ===================================================================
# Rate Limiting (requires slowapi)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_LOGIN=10/minute
RATE_LIMIT_REGISTER=5/minute
RATE_LIMIT_CACHE_CLEAR=5/minute

# JWT Token Settings
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Password Requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true

# ===================================================================
# 📊 Monitoring & Performance
# ===================================================================
# Enable Performance Monitoring
ENABLE_PERFORMANCE_MONITORING=true

# WebSocket Configuration
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_PING_TIMEOUT=10

# Cache Settings
CACHE_DEFAULT_TIMEOUT=3600
CACHE_MAX_SIZE=1000

# ===================================================================
# 🛠️ Development Settings (Disable in Production)
# ===================================================================
# Debug Mode (MUST be false in production)
DEBUG=false
ENABLE_DEBUG_ENDPOINTS=false

# API Documentation (set to false to hide Swagger docs in production)
ENABLE_API_DOCS=true

# ===================================================================
# 📝 Audit Logging
# ===================================================================
# Audit Log Configuration
AUDIT_LOG_ENABLED=true
AUDIT_LOG_FILE=/var/www/docscan/backend/logs/audit.log
AUDIT_LOG_LEVEL=INFO

# Log Types to Track
AUDIT_LOG_AUTHENTICATION=true
AUDIT_LOG_ADMIN_ACTIONS=true
AUDIT_LOG_SECURITY_EVENTS=true
AUDIT_LOG_DATA_ACCESS=true
EOF

# Set proper permissions
chmod 640 "$ENV_FILE"

echo ""
echo "✅ Production .env file created successfully!"
echo ""
echo "📋 File location: $ENV_FILE"
ls -lah "$ENV_FILE"
echo ""
echo "⚠️  IMPORTANT: Next steps required:"
echo ""
echo "1️⃣  Generate and update SECRET_KEY:"
echo "    NEW_KEY=\$(openssl rand -hex 32)"
echo "    sed -i \"s/REPLACE_THIS_WITH_SECURE_KEY_GENERATED_BY_OPENSSL/\$NEW_KEY/g\" $ENV_FILE"
echo ""
echo "2️⃣  Upload Google Cloud credentials to:"
echo "    $CONFIG_DIR/automation-ai-pajak-c560daf6c6d1.json"
echo ""
echo "3️⃣  Verify configuration:"
echo "    cd $BACKEND_DIR"
echo "    python3 -c 'from dotenv import load_dotenv; import os; load_dotenv(); print(\"✅ Config loaded\")'"
echo ""
echo "4️⃣  Install dependencies:"
echo "    source /var/www/docscan/venv/bin/activate"
echo "    pip install -r $BACKEND_DIR/requirements.txt"
echo ""
echo "5️⃣  Restart backend:"
echo "    pkill -f \"uvicorn main:app\""
echo "    cd $BACKEND_DIR"
echo "    nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &"
echo ""
echo "🎉 Setup complete!"
