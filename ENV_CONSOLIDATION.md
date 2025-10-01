# 🔧 Environment Configuration Guide

## 📋 Overview

File `.env` telah dikonsolidasikan menjadi satu file di `backend/.env` dengan konfigurasi lengkap untuk production deployment termasuk **Google Cloud Document AI**.

## 🗂️ File Structure

```
doc-scan-ai/
├── backend/
│   ├── .env                    # ✅ PRODUCTION CONFIG (JANGAN COMMIT)
│   ├── .env.example            # ✅ TEMPLATE (SAFE TO COMMIT)
│   └── config/
│       └── automation-ai-pajak-c560daf6c6d1.json  # Google Cloud credentials
```

## ✅ Changes Made

### Files Consolidated (DELETED):
- ❌ `.env.production` (root level)
- ❌ `production_files/backend/.env` (old backup)
- ❌ `.env.production.template` (replaced with .env.example)

### Files Created:
- ✅ `backend/.env` - **Production configuration** (complete & ready)
- ✅ `backend/.env.example` - **Template for reference** (no secrets)

## 🔐 Security Notes

### Protected by .gitignore:
```gitignore
.env
.env.local
.env.production
backend/.env
.env.*
```

### Safe to Commit:
- `backend/.env.example` - Template tanpa credentials

## 🤖 Google Cloud Document AI Configuration

File `.env` sudah include konfigurasi lengkap untuk Google Document AI:

```bash
# Google Cloud Document AI Settings
ENABLE_CLOUD_OCR=true
DEFAULT_OCR_ENGINE=google_doc_ai

# Credentials
GOOGLE_APPLICATION_CREDENTIALS=/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Project Info
GOOGLE_CLOUD_PROJECT=automation-ai-pajak
GOOGLE_CLOUD_PROJECT_ID=automation-ai-pajak

# Processor
GOOGLE_PROCESSOR_ID=831a22639bf6ff6f
GOOGLE_PROCESSOR_LOCATION=us
```

## 🚀 Production Setup

### 1. Copy Credentials File
```bash
# Di server production
cd /var/www/docscan
mkdir -p backend/config

# Upload file JSON ke server:
# automation-ai-pajak-c560daf6c6d1.json
# ke folder: /var/www/docscan/backend/config/
```

### 2. Verify Environment File
```bash
cd /var/www/docscan/backend
cat .env | head -20
```

### 3. Test Configuration Loading
```bash
cd /var/www/docscan/backend
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('✅ DATABASE_URL:', os.getenv('DATABASE_URL'))
print('✅ GOOGLE_CLOUD_PROJECT:', os.getenv('GOOGLE_CLOUD_PROJECT'))
print('✅ ENABLE_CLOUD_OCR:', os.getenv('ENABLE_CLOUD_OCR'))
"
```

### 4. Update Production Values
Edit `/var/www/docscan/backend/.env` dan ganti:

```bash
# Update SECRET_KEY dengan value baru:
openssl rand -hex 32

# Update path jika berbeda:
GOOGLE_APPLICATION_CREDENTIALS=/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json
```

## 📊 Configuration Sections

### 1. General Settings
- Domain, URLs, Node environment
- File upload/export paths
- Database connection string

### 2. Security
- SECRET_KEY (JWT token signing)
- CORS origins
- Password requirements
- Rate limiting

### 3. Google Cloud Document AI ⭐
- Service account credentials path
- Project ID and processor ID
- Processor location (US)
- Optional: Cloud Storage bucket

### 4. OCR Engines
- Engine priority list
- PaddleOCR settings
- EasyOCR settings
- Confidence thresholds

### 5. Monitoring & Logging
- Log levels and paths
- Audit logging configuration
- Performance monitoring

## ⚠️ Important Notes

### DO NOT Commit to Git:
- `backend/.env` - Contains production secrets
- `backend/config/*.json` - Google Cloud credentials

### Safe to Commit:
- `backend/.env.example` - Template file only

### Before Production:
1. ✅ Generate new SECRET_KEY
2. ✅ Upload Google Cloud credentials JSON
3. ✅ Verify file paths exist
4. ✅ Test database connection
5. ✅ Test Google Cloud API access

## 🔍 Verification Commands

```bash
# Check if .env file exists
ls -lah /var/www/docscan/backend/.env

# Check Google credentials file
ls -lah /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Test Google Cloud connection
cd /var/www/docscan/backend
python3 -c "
from google.cloud import documentai_v1
import os
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json'
client = documentai_v1.DocumentProcessorServiceClient()
print('✅ Google Cloud Document AI connected successfully!')
"
```

## 📝 Next Steps

1. **Git Push** (sudah dilakukan sebelumnya)
2. **Di Server Production**:
   ```bash
   cd /var/www/docscan
   git pull origin master
   source venv/bin/activate
   pip install -r backend/requirements.txt
   # Upload Google Cloud credentials JSON
   # Restart backend
   ```
3. **Verify Google Cloud AI** berfungsi dengan test upload document

## 🎯 Configuration Ready!

✅ Single `.env` file di `backend/.env`  
✅ Complete Google Cloud Document AI settings  
✅ All secrets protected by .gitignore  
✅ Template `.env.example` untuk reference  
✅ Production paths configured  
✅ Security settings enabled  

**Status**: Ready for production deployment! 🚀
