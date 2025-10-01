#!/bin/bash
# =============================================================================
# 🚀 Doc Scan AI - Complete VPS Deployment Script
# =============================================================================
# This script automates the entire deployment process
# Run on fresh VPS: ./deploy_to_vps.sh
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_DIR="/var/www/docscan"
APP_USER="docScan"
DOMAIN="docscan.adilabs.id"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║          🚀 Doc Scan AI - VPS Deployment 🚀             ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Please run as root (use sudo)${NC}"
    exit 1
fi

# Step 1: System Update
echo -e "${YELLOW}📦 Step 1/9: Updating system packages...${NC}"
apt update && apt upgrade -y
apt install -y git curl wget build-essential python3-pip

# Step 2: Create Application User
echo -e "${YELLOW}👤 Step 2/9: Creating application user...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash $APP_USER
    echo -e "${GREEN}✅ User $APP_USER created${NC}"
else
    echo -e "${GREEN}✅ User $APP_USER already exists${NC}"
fi

# Step 3: Create Directory Structure
echo -e "${YELLOW}📁 Step 3/9: Creating directory structure...${NC}"
mkdir -p $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR
echo -e "${GREEN}✅ Directory created: $APP_DIR${NC}"

# Step 4: Clone/Update Repository
echo -e "${YELLOW}📥 Step 4/9: Cloning repository...${NC}"
if [ -d "$APP_DIR/.git" ]; then
    echo "Updating existing repository..."
    cd $APP_DIR
    sudo -u $APP_USER git pull
else
    echo "Cloning repository..."
    sudo -u $APP_USER git clone https://github.com/Adi-Sumardi/doc-scan-ai.git $APP_DIR
fi
echo -e "${GREEN}✅ Repository ready${NC}"

# Step 5: Get Database Password
echo ""
echo -e "${YELLOW}🔐 Step 5/9: Database Configuration${NC}"
echo -n "Enter MySQL password for docuser (min 12 chars): "
read -s DB_PASS
echo ""

if [ ${#DB_PASS} -lt 12 ]; then
    echo -e "${RED}❌ Password too short (minimum 12 characters)${NC}"
    exit 1
fi

# Step 6: Setup MySQL
echo -e "${YELLOW}🗄️  Step 6/9: Setting up MySQL database...${NC}"
cd $APP_DIR
chmod +x scripts/setup_mysql.sh
./scripts/setup_mysql.sh "$DB_PASS"

# Step 7: Configure Environment
echo -e "${YELLOW}⚙️  Step 7/9: Configuring environment...${NC}"

# Generate SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)

# Create .env from template
cp backend/.env.production backend/.env
sed -i "s/CHANGE_THIS_PASSWORD/${DB_PASS}/g" backend/.env
sed -i "s/CHANGE_THIS_TO_RANDOM_SECRET_KEY/${SECRET_KEY}/g" backend/.env

chown $APP_USER:$APP_USER backend/.env
chmod 600 backend/.env

echo -e "${GREEN}✅ Environment configured${NC}"

# Step 8: Setup Backend
echo -e "${YELLOW}🐍 Step 8/9: Setting up Python backend...${NC}"
cd $APP_DIR
chmod +x scripts/setup_backend.sh
sudo -u $APP_USER ./scripts/setup_backend.sh

# Step 9: Setup Frontend
echo -e "${YELLOW}⚛️  Step 9/9: Building frontend...${NC}"
chmod +x scripts/setup_frontend.sh
./scripts/setup_frontend.sh

# Create systemd service
echo -e "${YELLOW}🔧 Creating systemd service...${NC}"
cat > /etc/systemd/system/docscan-backend.service <<EOF
[Unit]
Description=Doc Scan AI Backend
After=network.target mysql.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=10
StandardOutput=append:/var/log/docscan/backend.log
StandardError=append:/var/log/docscan/backend.log

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p /var/log/docscan
chown -R $APP_USER:$APP_USER /var/log/docscan

# Enable and start service
systemctl daemon-reload
systemctl enable docscan-backend
systemctl start docscan-backend

echo -e "${GREEN}✅ Backend service started${NC}"

# Setup Nginx
echo ""
echo -e "${YELLOW}🌐 Setting up Nginx + SSL...${NC}"
chmod +x scripts/setup_nginx_ssl.sh
./scripts/setup_nginx_ssl.sh $DOMAIN

# Final Status
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║          🎉 DEPLOYMENT COMPLETE! 🎉                     ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo "   • Application: $APP_DIR"
echo "   • User: $APP_USER"
echo "   • Database: docscan_db"
echo "   • Backend: http://127.0.0.1:8000"
echo "   • Domain: https://$DOMAIN"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "   • Check backend: sudo systemctl status docscan-backend"
echo "   • View logs: sudo journalctl -u docscan-backend -f"
echo "   • Restart backend: sudo systemctl restart docscan-backend"
echo "   • Reload Nginx: sudo systemctl reload nginx"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT NEXT STEPS:${NC}"
echo "   1. Upload Google Cloud credentials:"
echo "      scp automation-ai-pajak-*.json $APP_USER@$DOMAIN:$APP_DIR/backend/config/"
echo ""
echo "   2. Create admin user:"
echo "      sudo su - $APP_USER"
echo "      cd $APP_DIR/backend"
echo "      source ../venv/bin/activate"
echo "      python fresh_start.py"
echo ""
echo "   3. Test the application:"
echo "      https://$DOMAIN"
echo ""
echo -e "${GREEN}🚀 Deployment successful!${NC}"
