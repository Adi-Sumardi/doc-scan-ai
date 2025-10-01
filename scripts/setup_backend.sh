#!/bin/bash
# =============================================================================
# Python Backend Setup for Doc Scan AI
# =============================================================================

set -e

echo "🐍 Setting up Python backend..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
APP_DIR="/var/www/docscan"
VENV_DIR="${APP_DIR}/venv"
BACKEND_DIR="${APP_DIR}/backend"

# Check if running as correct user
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}❌ Don't run this script as root. Run as docScan user.${NC}"
    exit 1
fi

# Install Python 3.10 if not exists
if ! command -v python3.10 &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Python 3.10...${NC}"
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.10 python3.10-venv python3.10-dev
fi

echo "✅ Python 3.10 installed"

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3.10 -m venv $VENV_DIR
fi

# Activate venv and install dependencies
echo "📥 Installing Python packages..."
source ${VENV_DIR}/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
cd ${BACKEND_DIR}
pip install -r requirements.txt

echo -e "${GREEN}✅ Backend dependencies installed${NC}"

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p ${APP_DIR}/{uploads,exports,logs}
mkdir -p ${BACKEND_DIR}/config

# Set proper permissions
chmod 755 ${APP_DIR}/{uploads,exports,logs}

echo -e "${GREEN}✅ Directory structure created${NC}"

# Run database migration
echo "🗄️  Running database migration..."
python fresh_start.py

echo -e "${GREEN}✅ Database tables created${NC}"

echo ""
echo "🎉 Backend setup complete!"
echo "   Virtual environment: ${VENV_DIR}"
echo "   Backend directory: ${BACKEND_DIR}"
