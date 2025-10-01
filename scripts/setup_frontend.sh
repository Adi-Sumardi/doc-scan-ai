#!/bin/bash
# =============================================================================
# Frontend Build & Deploy for Doc Scan AI
# =============================================================================

set -e

echo "⚛️  Building frontend..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
APP_DIR="/var/www/docscan"
PROJECT_DIR="$(pwd)"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Node.js 18...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

echo "✅ Node.js $(node -v) installed"

# Install dependencies
echo "📥 Installing npm packages..."
cd ${PROJECT_DIR}
npm install

# Build frontend
echo "🔨 Building React app..."
npm run build

# Deploy to web root
echo "🚀 Deploying frontend..."
sudo rm -rf ${APP_DIR}/dist
sudo cp -r dist ${APP_DIR}/

# Set proper permissions
sudo chown -R www-data:www-data ${APP_DIR}/dist
sudo chmod -R 755 ${APP_DIR}/dist

echo -e "${GREEN}✅ Frontend deployed to ${APP_DIR}/dist${NC}"

echo ""
echo "🎉 Frontend build complete!"
echo "   Build directory: ${APP_DIR}/dist"
