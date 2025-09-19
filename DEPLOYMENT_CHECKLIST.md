# 🚀 Production Deployment Checklist

## 📋 Pre-Deployment Checklist

### ✅ Code Cleanup (COMPLETED)
- [x] All test files removed (`test_*.py`)
- [x] Debug files removed (`*debug*.py`, `*test*.py`)
- [x] Log files cleaned (`*.log`)
- [x] Temporary files removed
- [x] `__pycache__` directories cleaned
- [x] Upload/export directories cleaned
- [x] `.DS_Store` files removed
- [x] `.gitignore` updated for production
- [x] `.gitkeep` files added for directory structure

### 🔧 Production Files Created
- [x] `README_PRODUCTION.md` - Comprehensive production guide
- [x] `deploy.sh` - Automated deployment script
- [x] Updated `.gitignore` - Production-ready git ignore rules
- [x] Directory structure maintained with `.gitkeep` files

### 📁 Final Backend Structure
```
backend/
├── .env                      # Environment configuration
├── .python-version          # Python version specification
├── ai_processor.py          # Main AI/OCR processing engine
├── config.py                # Application configuration
├── database.py              # Database models and connection
├── device_config.py         # Device and GPU configuration
├── enhanced_ocr_processor.py # Enhanced OCR capabilities
├── main.py                  # FastAPI application main file
├── models.py                # Pydantic models
├── production_ocr.py        # Production OCR processor
├── redis_cache.py           # Redis caching implementation
├── requirements.txt         # Python dependencies
├── security.py              # File security validation
├── start.sh                 # Local start script
├── super_maximum_ocr.py     # Maximum performance OCR
├── utils.py                 # Utility functions
├── websocket_manager.py     # WebSocket connection manager
├── uploads/                 # File upload directory (empty)
│   └── .gitkeep
├── results/                 # Processing results directory (empty)
│   └── .gitkeep
└── exports/                 # Export files directory (empty)
    └── .gitkeep
```

## 🏗️ Production Deployment Steps

### 1. Server Preparation
- [ ] VPS/Server dengan minimum 4GB RAM
- [ ] Ubuntu 20.04+ atau CentOS 8+
- [ ] Python 3.10+ installed
- [ ] MySQL/MariaDB server installed
- [ ] Redis server installed
- [ ] Nginx (optional, for reverse proxy)

### 2. Repository Setup
```bash
# Clone repository
git clone <your-repo-url>
cd doc-scan-ai

# Run automated deployment
chmod +x deploy.sh
./deploy.sh
```

### 3. Environment Configuration
```bash
# Edit environment file
nano backend/.env

# Required configurations:
# - DATABASE_URL (MySQL connection string)
# - REDIS_URL (Redis connection string)
# - SECRET_KEY (generated automatically)
# - CORS_ORIGINS (your domain)
```

### 4. Database Setup
```sql
-- Create database
CREATE DATABASE doc_scan_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'doc_scan_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON doc_scan_ai.* TO 'doc_scan_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Service Installation
```bash
# Copy systemd service
sudo cp /tmp/doc-scan-ai.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable doc-scan-ai
sudo systemctl start doc-scan-ai

# Check status
sudo systemctl status doc-scan-ai
```

### 6. Nginx Configuration (Optional)
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 10M;

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
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 7. SSL/HTTPS Setup
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

## 🧪 Production Testing

### Health Check Endpoints
```bash
# Basic health check
curl http://your-server:8000/api/health

# Production heartbeat
curl -X POST http://your-server:8000/api/heartbeat

# WebSocket stats
curl http://your-server:8000/api/ws/stats
```

### Expected Responses
```json
// Health check
{
  "status": "healthy",
  "service": "doc-scan-ai",
  "timestamp": "2025-09-19T10:00:00.000000",
  "cache": {
    "redis_connected": true,
    "total_cached_items": 0
  }
}
```

## 📊 Performance Optimization

### Server Specifications (Recommended)
- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB+ SSD
- **GPU**: Optional (NVIDIA for CUDA, Apple Silicon for MPS)

### Gunicorn Configuration
```bash
# Production command
gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 300 \
  --keep-alive 5
```

## 🔒 Security Checklist

- [ ] Environment variables secured
- [ ] Database credentials protected
- [ ] HTTPS/SSL enabled
- [ ] Firewall configured
- [ ] File upload limits enforced
- [ ] CORS origins restricted
- [ ] Regular security updates

## 📈 Monitoring Setup

### Log Files
```bash
# Application logs
tail -f /var/log/doc-scan-ai/app.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# System logs
journalctl -u doc-scan-ai -f
```

### Monitoring Commands
```bash
# Check service status
sudo systemctl status doc-scan-ai

# Check Redis
redis-cli ping

# Check MySQL
mysql -u doc_scan_user -p -e "SELECT 1;"

# Check disk space
df -h

# Check memory usage
free -h
```

## 🔄 Backup Strategy

### Database Backup
```bash
# Create backup script
#!/bin/bash
mysqldump -u doc_scan_user -p doc_scan_ai > /backup/doc_scan_ai_$(date +%Y%m%d_%H%M%S).sql
```

### File Backup
```bash
# Backup uploads and exports
tar -czf /backup/files_$(date +%Y%m%d_%H%M%S).tar.gz uploads/ exports/
```

## 🚨 Troubleshooting

### Common Issues
1. **Redis Connection Failed**
   ```bash
   sudo systemctl restart redis
   ```

2. **Database Connection Error**
   ```bash
   # Check MySQL status
   sudo systemctl status mysql
   ```

3. **Permission Denied**
   ```bash
   # Fix file permissions
   chmod 755 /path/to/app
   chown -R www-data:www-data /path/to/app
   ```

4. **Memory Issues**
   ```bash
   # Check memory usage
   free -h
   # Restart service
   sudo systemctl restart doc-scan-ai
   ```

## ✅ Deployment Complete

### Final Verification
- [ ] Application starts without errors
- [ ] Health endpoint returns 200
- [ ] Database connection working
- [ ] Redis caching functional
- [ ] File upload working
- [ ] WebSocket connections stable
- [ ] SSL certificate valid
- [ ] Monitoring setup complete

### Production URLs
- **API**: `https://yourdomain.com/api`
- **WebSocket**: `wss://yourdomain.com/ws`
- **Health Check**: `https://yourdomain.com/api/health`

🎉 **Application is now ready for production use!**