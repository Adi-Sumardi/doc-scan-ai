#!/bin/bash
# =============================================================================
# Nginx & SSL Setup for Doc Scan AI
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DOMAIN="$1"

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ Usage: $0 <domain>${NC}"
    echo "   Example: $0 docscan.adilabs.id"
    exit 1
fi

echo "🌐 Setting up Nginx for ${DOMAIN}..."

# Install Nginx
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing Nginx..."
    sudo apt update
    sudo apt install -y nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
fi

echo "✅ Nginx installed"

# Create Nginx configuration
echo "📝 Creating Nginx configuration..."

sudo tee /etc/nginx/sites-available/docscan > /dev/null <<EOF
# Doc Scan AI - Nginx Configuration

upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};

    # For Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/docscan;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};

    # SSL Certificates (will be configured by certbot)
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Root directory
    root /var/www/docscan/dist;
    index index.html;

    # Max upload size
    client_max_body_size 50M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json application/javascript;

    # API Backend
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://backend/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    # Static files
    location /uploads/ {
        alias /var/www/docscan/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /exports/ {
        alias /var/www/docscan/exports/;
        expires 1d;
        add_header Cache-Control "public";
    }

    # Frontend - SPA fallback
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Logs
    access_log /var/log/nginx/docscan_access.log;
    error_log /var/log/nginx/docscan_error.log;
}
EOF

# Enable site
echo "🔗 Enabling site..."
sudo ln -sf /etc/nginx/sites-available/docscan /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
echo "🧪 Testing Nginx configuration..."
if sudo nginx -t; then
    echo -e "${GREEN}✅ Nginx configuration is valid${NC}"
else
    echo -e "${RED}❌ Nginx configuration has errors${NC}"
    exit 1
fi

# Reload Nginx
sudo systemctl reload nginx
echo -e "${GREEN}✅ Nginx reloaded${NC}"

# Install Certbot if not exists
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing Certbot..."
    sudo apt install -y certbot python3-certbot-nginx
fi

# Get SSL certificate
echo ""
echo -e "${YELLOW}🔒 Setting up SSL certificate...${NC}"
echo "Please enter your email for SSL certificate notifications:"
read EMAIL

sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} \
    --non-interactive --agree-tos --email ${EMAIL} \
    --redirect || {
    echo -e "${YELLOW}⚠️  SSL setup failed. You can run it manually later with:${NC}"
    echo "   sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
}

echo ""
echo "🎉 Nginx + SSL setup complete!"
echo "   Domain: https://${DOMAIN}"
echo "   Config: /etc/nginx/sites-available/docscan"
echo ""
echo "🔄 To reload Nginx: sudo systemctl reload nginx"
