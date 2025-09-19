# Document Scanning AI - Production Deployment

## 🚀 Production-Ready Document Scanning Application

Aplikasi AI untuk scanning dan ekstraksi data dari dokumen dengan fitur real-time progress tracking, Redis caching, dan comprehensive error handling.

## ✨ Features

- **AI-Powered OCR**: PaddleOCR + EasyOCR dengan GPU acceleration
- **Real-time Progress**: WebSocket untuk tracking progress secara real-time
- **Redis Caching**: High-performance caching untuk OCR results
- **Security Validation**: Multi-layer file validation dan security checks
- **Database Integration**: MySQL dengan optimized performance
- **Error Handling**: Production-grade error handling dengan user-friendly messages
- **Export Capabilities**: Export ke Excel dan PDF

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI dengan async support
- **Database**: MySQL dengan SQLAlchemy ORM
- **Caching**: Redis untuk high-performance caching
- **AI/OCR**: PaddleOCR, EasyOCR dengan Apple Silicon MPS support
- **Real-time**: WebSocket untuk progress tracking

### Frontend (React + TypeScript)
- **Framework**: React dengan TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Context API

## 📋 Requirements

### System Requirements
- Python 3.10+
- Redis Server
- MySQL Server
- Node.js 18+ (untuk frontend)

### Python Dependencies
```bash
fastapi
uvicorn[standard]
sqlalchemy
mysql-connector-python
redis
paddlepaddle
paddleocr
easyocr
opencv-python
layoutparser
torch
torchvision
pandas
openpyxl
reportlab
python-multipart
aiofiles
websockets
pydantic
```

## 🚀 Production Deployment

### 1. Environment Setup

```bash
# Clone repository
git clone <your-repo-url>
cd doc-scan-ai

# Setup Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Database Setup

```sql
-- Create database
CREATE DATABASE doc_scan_ai;

-- Create user (optional)
CREATE USER 'doc_scan_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON doc_scan_ai.* TO 'doc_scan_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Environment Configuration

Buat file `.env` di folder `backend/`:

```env
# Database Configuration
DATABASE_URL=mysql+mysqlconnector://username:password@localhost:3306/doc_scan_ai

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
SECRET_KEY=your_secret_key_here
DEBUG=false
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# File Upload Configuration
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_PATH=./uploads
RESULTS_PATH=./results
EXPORTS_PATH=./exports
```

### 4. Redis Setup

```bash
# Install Redis (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
```

### 5. Run Application

```bash
# Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend (development)
cd ..
npm install
npm run dev

# Frontend (production)
npm run build
npm run preview
```

### 6. Production Server (dengan Gunicorn)

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 7. Nginx Configuration (Optional)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📊 API Endpoints

### Upload & Processing
- `POST /api/upload` - Upload documents for processing
- `GET /api/batches/{batch_id}` - Get batch status
- `GET /api/batches/{batch_id}/results` - Get processing results

### Real-time
- `WebSocket /ws` - General WebSocket connection
- `WebSocket /ws/batch/{batch_id}` - Batch-specific WebSocket

### Export
- `GET /api/batches/{batch_id}/export/excel` - Export to Excel
- `GET /api/batches/{batch_id}/export/pdf` - Export to PDF

### Health & Monitoring
- `GET /api/health` - Health check with cache statistics
- `POST /api/heartbeat` - Production heartbeat
- `GET /api/ws/stats` - WebSocket connection statistics

## 🛡️ Security Features

- File type validation (jpg, jpeg, png, pdf, tiff, tif)
- File size limits (10MB max)
- MIME type checking
- Content validation
- Executable file detection
- Input sanitization

## 📈 Performance Features

- **Apple Silicon MPS GPU** acceleration
- **Redis caching** untuk OCR results
- **Background processing** dengan FastAPI BackgroundTasks
- **Connection pooling** untuk database
- **Optimized image processing** pipeline

## 🔧 Monitoring & Logging

- Comprehensive error logging
- Performance metrics tracking
- Redis cache statistics
- Database performance monitoring
- WebSocket connection tracking

## 🚨 Production Checklist

- [ ] Environment variables configured
- [ ] Database created and migrated
- [ ] Redis server running
- [ ] SSL certificates installed (untuk HTTPS)
- [ ] Firewall configured
- [ ] Backup strategy implemented
- [ ] Monitoring setup
- [ ] Log rotation configured

## 📞 Support

Untuk dukungan production deployment, hubungi tim development.

## 📄 License

Private/Commercial License