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

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Node.js 18...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi

echo "✅ Node.js $(node -v) installed"

# Make sure we're in the app directory
cd ${APP_DIR}

# Install dependencies
echo "📥 Installing npm packages..."
npm install

# Build frontend
echo "🔨 Building React app..."
npm run build

# Check if dist was created
if [ ! -d "dist" ]; then
    echo -e "${RED}❌ Error: dist directory not created after build${NC}"
    exit 1
fi

# Deploy to web root (dist is already in APP_DIR, just set permissions)
echo "🚀 Deploying frontend..."

# Set proper permissions
sudo chown -R www-data:www-data ${APP_DIR}/dist
sudo chmod -R 755 ${APP_DIR}/dist

echo -e "${GREEN}✅ Frontend deployed to ${APP_DIR}/dist${NC}"
echo "   Files: $(ls -lh ${APP_DIR}/dist/index.html 2>/dev/null || echo 'index.html found')"

echo ""
echo "🎉 Frontend build complete!"
echo "   Build directory: ${APP_DIR}/dist"
