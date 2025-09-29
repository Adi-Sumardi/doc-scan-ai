# 🚀 BiznetGio VPS Deployment Guide

## Overview
Complete deployment guide for Doc Scan AI on BiznetGio VPS with Ubuntu 20.04/22.04.

## Prerequisites
- BiznetGio VPS (minimal 2GB RAM, 2 CPU cores)
- Ubuntu 20.04/22.04 LTS
- Root/sudo access
- Domain `docscan.adilabs.id` pointing to VPS IP
- Python 3.10 (same as development environment)

## Quick Deployment

### 1. VPS Setup
```bash
# SSH into your VPS
ssh root@your-vps-ip

# Create user (if needed)
adduser deploy
usermod -aG sudo deploy
su - deploy
```

### 2. Clone and Deploy
```bash
# Clone repository
git clone https://github.com/Adi-Sumardi/doc-scan-ai.git
cd doc-scan-ai

# Run deployment script
chmod +x deploy-biznetgio.sh
./deploy-biznetgio.sh
```

### 3. SSL Certificate
```bash
# After DNS is pointed to VPS
sudo certbot --nginx -d docscan.adilabs.id -d www.docscan.adilabs.id
```

## Manual Installation Steps

### 1. System Update
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip software-properties-common
```

### 2. Python 3.10 Installation (Development Compatible)
```bash
# Add deadsnakes PPA for Python 3.10
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.10
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3.10-distutils

# Install pip for Python 3.10
curl https://bootstrap.pypa.io/get-pip.py | sudo python3.10

# Set Python 3.10 as default python3
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
```

### 3. Node.js Installation
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 4. Database Setup
```bash
# Install MySQL
sudo apt install -y mysql-server mysql-client
sudo systemctl start mysql
sudo systemctl enable mysql

# Create database
sudo mysql -e "CREATE DATABASE docscan_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'docscan_user'@'localhost' IDENTIFIED BY 'your_secure_password';"
sudo mysql -e "GRANT ALL PRIVILEGES ON docscan_db.* TO 'docscan_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
```

### 5. OCR Dependencies
```bash
# Tesseract OCR
sudo apt install -y tesseract-ocr tesseract-ocr-ind libtesseract-dev

# OpenCV dependencies
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
```

### 6. Application Setup
```bash
# Create directory
sudo mkdir -p /var/www/docscan
sudo chown $USER:$USER /var/www/docscan
cd /var/www/docscan

# Clone repository
git clone https://github.com/Adi-Sumardi/doc-scan-ai.git .

# Python 3.10 virtual environment
python3.10 -m venv venv
source venv/bin/activate
cd backend
pip install --upgrade pip
pip install -r requirements.txt

# Build frontend
cd ..
npm install
npm run build
```

### 7. Environment Configuration
```bash
# Create .env file
cat > backend/.env << EOF
DATABASE_URL=mysql://docscan_user:your_secure_password@localhost/docscan_db
FRONTEND_URL=https://docscan.adilabs.id
BACKEND_URL=https://docscan.adilabs.id/api
UPLOAD_FOLDER=/var/www/docscan/uploads
EXPORT_FOLDER=/var/www/docscan/exports
SECRET_KEY=your_super_secret_key_here
ENVIRONMENT=production
DEFAULT_OCR_ENGINE=paddleocr
ENABLE_CLOUD_OCR=false
EOF

# Create directories
mkdir -p uploads exports logs
chmod 755 uploads exports logs
```

### 8. Systemd Service
```bash
# Create service file
sudo tee /etc/systemd/system/docscan-backend.service > /dev/null << EOF
[Unit]
Description=Doc Scan AI Backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/var/www/docscan/backend
Environment=PATH=/var/www/docscan/venv/bin
ExecStart=/var/www/docscan/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable docscan-backend
sudo systemctl start docscan-backend
```

### 9. Nginx Configuration
```bash
# Install Nginx
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Create site configuration
sudo tee /etc/nginx/sites-available/docscan.adilabs.id > /dev/null << 'EOF'
server {
    listen 80;
    server_name docscan.adilabs.id www.docscan.adilabs.id;

    root /var/www/docscan/dist;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }

    # Frontend routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Static assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/docscan.adilabs.id /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 10. SSL Certificate
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (after DNS is pointed)
sudo certbot --nginx -d docscan.adilabs.id -d www.docscan.adilabs.id
```

## Post-Deployment

### Testing
```bash
# Check services
sudo systemctl status docscan-backend
sudo systemctl status nginx
sudo systemctl status mysql

# Test API
curl http://localhost:8000/health
curl http://your-vps-ip/api/health

# Test frontend
curl http://your-vps-ip
```

### Monitoring
```bash
# Backend logs
sudo journalctl -u docscan-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# System resources
htop
df -h
free -h
```

## Maintenance

### Update Application
```bash
cd /var/www/docscan
git pull origin master
source venv/bin/activate
cd backend
pip install -r requirements.txt
cd ..
npm install
npm run build
sudo systemctl restart docscan-backend
sudo systemctl reload nginx
```

### Database Backup
```bash
# Create backup
mysqldump -u docscan_user -p docscan_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
mysql -u docscan_user -p docscan_db < backup_file.sql
```

### Security Updates
```bash
# System updates
sudo apt update && sudo apt upgrade -y

# SSL certificate renewal (automatic with certbot)
sudo certbot renew --dry-run
```

## Firewall Configuration
```bash
# UFW firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw status
```

## Performance Optimization

### 1. Redis Cache (Optional)
```bash
# Install Redis
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Update .env
echo "REDIS_URL=redis://localhost:6379/0" >> backend/.env
echo "ENABLE_REDIS_CACHE=true" >> backend/.env
```

### 2. Process Manager (PM2)
```bash
# Install PM2
sudo npm install -g pm2

# Create PM2 ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'docscan-backend',
    cwd: '/var/www/docscan/backend',
    script: '/var/www/docscan/venv/bin/python',
    args: 'main.py',
    instances: 2,
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
EOF

# Start with PM2
pm2 start ecosystem.config.js
pm2 startup
pm2 save
```

## Troubleshooting

### Common Issues
1. **Port 8000 blocked**: Check firewall rules
2. **Database connection failed**: Verify MySQL credentials
3. **OCR processing errors**: Install missing OCR dependencies
4. **Nginx 502 error**: Check backend service status
5. **SSL certificate issues**: Verify DNS pointing and domain configuration

### Useful Commands
```bash
# Check ports
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :80

# Check disk space
df -h
du -sh /var/www/docscan/

# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart all services
sudo systemctl restart docscan-backend nginx mysql
```

---

**VPS Specs Recommendation:**
- **Minimal**: 2GB RAM, 2 CPU, 40GB SSD
- **Recommended**: 4GB RAM, 2 CPU, 80GB SSD
- **High Traffic**: 8GB RAM, 4 CPU, 160GB SSD

**Estimated Setup Time**: 15-30 minutes with automated script

**Domain**: docscan.adilabs.id
**Backend**: FastAPI with advanced OCR processing
**Frontend**: React with production optimization
**Database**: MySQL with full persistence