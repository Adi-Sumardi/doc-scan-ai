#!/bin/bash
# 🚀 BiznetGio VPS Deployment Script for Doc Scan AI
# Domain: docscan.adilabs.id

echo "🚀 Doc Scan AI - BiznetGio VPS Deployment"
echo "========================================="
echo "Domain: docscan.adilabs.id"
echo "Date: $(date)"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
sudo apt install -y curl wget git unzip software-properties-common

# Install Python 3.10 (same as development)
echo "🐍 Installing Python 3.10..."
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3.10-distutils
curl https://bootstrap.pypa.io/get-pip.py | sudo python3.10
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Install Node.js and npm
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install MySQL
echo "🗄️  Installing MySQL..."
sudo apt install -y mysql-server mysql-client
sudo systemctl start mysql
sudo systemctl enable mysql

# Install Nginx
echo "🌐 Installing Nginx..."
sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Install additional OCR dependencies
echo "🔍 Installing OCR dependencies..."
sudo apt install -y tesseract-ocr tesseract-ocr-ind libtesseract-dev
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# Create application directory
echo "📁 Creating application directory..."
sudo mkdir -p /var/www/docscan
sudo chown $USER:$USER /var/www/docscan

# Clone repository
echo "📋 Cloning repository..."
cd /var/www/docscan
git clone https://github.com/Adi-Sumardi/doc-scan-ai.git .

# Setup Python 3.10 virtual environment
echo "🐍 Setting up Python 3.10 virtual environment..."
python3.10 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt

# Build frontend
echo "🎨 Building frontend..."
cd ..
npm install
npm run build

# Setup database
echo "🗄️  Setting up database..."
sudo mysql -e "CREATE DATABASE docscan_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER 'docscan_user'@'localhost' IDENTIFIED BY 'docscan_secure_password_2025';"
sudo mysql -e "GRANT ALL PRIVILEGES ON docscan_db.* TO 'docscan_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Create environment file
echo "⚙️  Creating environment configuration..."
cat > backend/.env << EOF
# Production Database Configuration
DATABASE_URL=mysql://docscan_user:docscan_secure_password_2025@localhost/docscan_db

# Domain Configuration
FRONTEND_URL=https://docscan.adilabs.id
BACKEND_URL=https://docscan.adilabs.id/api

# File Storage
UPLOAD_FOLDER=/var/www/docscan/uploads
EXPORT_FOLDER=/var/www/docscan/exports

# Security
SECRET_KEY=docscan_super_secret_key_biznetgio_2025
ENVIRONMENT=production

# OCR Configuration
DEFAULT_OCR_ENGINE=paddleocr
ENABLE_CLOUD_OCR=false

# Cache
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS_CACHE=false
EOF

# Create necessary directories
echo "📁 Creating application directories..."
mkdir -p uploads exports logs
chmod 755 uploads exports logs

# Create systemd service for backend
echo "🔧 Creating systemd service..."
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

# Create Nginx configuration
echo "🌐 Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/docscan.adilabs.id > /dev/null << 'EOF'
server {
    listen 80;
    server_name docscan.adilabs.id www.docscan.adilabs.id;

    # Frontend files
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

    # File uploads
    location /uploads/ {
        alias /var/www/docscan/uploads/;
        expires 1d;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/docscan.adilabs.id /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t

# Install SSL certificate (Certbot)
echo "🔒 Installing SSL certificate..."
sudo apt install -y certbot python3-certbot-nginx

# Enable services
echo "🚀 Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable docscan-backend
sudo systemctl start docscan-backend
sudo systemctl reload nginx

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "✅ VPS Setup: Complete"
echo "✅ Database: MySQL configured"
echo "✅ Backend: Running on port 8000"
echo "✅ Frontend: Served by Nginx"
echo "✅ Domain: Ready for docscan.adilabs.id"
echo ""
echo "📋 Next Steps:"
echo "1. Point your domain DNS to this VPS IP"
echo "2. Run: sudo certbot --nginx -d docscan.adilabs.id -d www.docscan.adilabs.id"
echo "3. Test: curl http://$(curl -s ifconfig.me)/api/health"
echo ""
echo "🔧 Management Commands:"
echo "- Check backend: sudo systemctl status docscan-backend"
echo "- View logs: sudo journalctl -u docscan-backend -f"
echo "- Restart: sudo systemctl restart docscan-backend"
echo "- Nginx reload: sudo systemctl reload nginx"