# 🚀 Doc Scan AI - VPS Deployment Guide

## 📋 Prerequisites

- VPS Server (Ubuntu 20.04+)
- Domain: docscan.adilabs.id
- MySQL 8.0+
- Python 3.10+
- Node.js 18+
- Nginx

## 🎯 Quick Deployment

```bash
# 1. Clone repository on VPS
git clone https://github.com/Adi-Sumardi/doc-scan-ai.git
cd doc-scan-ai

# 2. Run automated deployment
chmod +x deploy_to_vps.sh
./deploy_to_vps.sh

# 3. Configure domain & SSL
sudo ./scripts/setup_nginx_ssl.sh docscan.adilabs.id
```

## 📁 Deployment Files

- `deploy_to_vps.sh` - Main deployment script
- `scripts/setup_mysql.sh` - MySQL database setup
- `scripts/setup_backend.sh` - Python backend setup
- `scripts/setup_frontend.sh` - React frontend build
- `scripts/setup_nginx_ssl.sh` - Nginx + SSL configuration
- `backend/.env.production` - Production environment template

## 🔐 Security Checklist

- [ ] Change SECRET_KEY in .env.production
- [ ] Update MySQL password
- [ ] Upload Google Cloud credentials
- [ ] Configure firewall rules
- [ ] Enable HTTPS/SSL

## 📞 Support

Issues: https://github.com/Adi-Sumardi/doc-scan-ai/issues
