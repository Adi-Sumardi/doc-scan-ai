#!/bin/bash

# Production Deployment Script for Document Scanning AI
# Author: Development Team
# Version: 1.0

set -e

echo "🚀 Starting Document Scanning AI Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root"
    exit 1
fi

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d" " -f2)
required_version="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    print_error "Python 3.10+ is required. Current version: $python_version"
    exit 1
fi

print_status "Python version check passed: $python_version"

# Create virtual environment
print_status "Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
cd backend
pip install -r requirements.txt

# Check if Redis is installed and running
print_status "Checking Redis installation..."
if ! command -v redis-server &> /dev/null; then
    print_warning "Redis not found. Installing Redis..."
    
    # Detect OS and install Redis
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Ubuntu/Debian
        sudo apt update
        sudo apt install -y redis-server
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install redis
        else
            print_error "Homebrew not found. Please install Redis manually."
            exit 1
        fi
    else
        print_error "Unsupported OS. Please install Redis manually."
        exit 1
    fi
fi

# Start Redis service
print_status "Starting Redis service..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    sudo systemctl start redis-server
    sudo systemctl enable redis-server
elif [[ "$OSTYPE" == "darwin"* ]]; then
    brew services start redis
fi

# Test Redis connection
print_status "Testing Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    print_status "Redis is running and accessible"
else
    print_error "Redis is not accessible"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << EOL
# Database Configuration
DATABASE_URL=mysql+mysqlconnector://username:password@localhost:3306/doc_scan_ai

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# File Upload Configuration
MAX_FILE_SIZE=10485760
UPLOAD_PATH=./uploads
RESULTS_PATH=./results
EXPORTS_PATH=./exports
EOL
    print_warning "Please edit .env file with your database credentials"
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads results exports

# Test database connection (if configured)
print_status "Testing application startup..."
if python -c "from database import engine; engine.connect()" 2>/dev/null; then
    print_status "Database connection successful"
else
    print_warning "Database connection failed. Please check your .env configuration"
fi

# Create systemd service file for production
print_status "Creating systemd service file..."
SERVICE_FILE="/tmp/doc-scan-ai.service"
cat > $SERVICE_FILE << EOL
[Unit]
Description=Document Scanning AI FastAPI Application
After=network.target

[Service]
Type=notify
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
ExecReload=/bin/kill -s HUP \$MAINPID
RestartSec=1
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

print_status "Systemd service file created at $SERVICE_FILE"
print_warning "To install: sudo cp $SERVICE_FILE /etc/systemd/system/"
print_warning "To enable: sudo systemctl enable doc-scan-ai"
print_warning "To start: sudo systemctl start doc-scan-ai"

# Install gunicorn for production
print_status "Installing Gunicorn for production..."
pip install gunicorn

cd ..

# Frontend setup (if Node.js is available)
if command -v npm &> /dev/null; then
    print_status "Installing frontend dependencies..."
    npm install
    
    print_status "Building frontend for production..."
    npm run build
    
    print_status "Frontend built successfully"
else
    print_warning "Node.js not found. Frontend setup skipped."
fi

# Print deployment summary
print_status "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Summary:"
echo "  ✅ Python virtual environment created"
echo "  ✅ Python dependencies installed"
echo "  ✅ Redis server checked and started"
echo "  ✅ Application directories created"
echo "  ✅ Systemd service file created"
echo "  ✅ Production server (Gunicorn) installed"
if command -v npm &> /dev/null; then
    echo "  ✅ Frontend dependencies installed and built"
fi
echo ""
echo "🚀 Next steps:"
echo "  1. Edit backend/.env with your database credentials"
echo "  2. Create and configure your MySQL database"
echo "  3. Install the systemd service (see warnings above)"
echo "  4. Configure Nginx (optional, see README_PRODUCTION.md)"
echo "  5. Setup SSL certificates for HTTPS"
echo ""
echo "🔧 Manual start commands:"
echo "  Backend:  cd backend && ../venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
if command -v npm &> /dev/null; then
    echo "  Frontend: npm run preview"
fi
echo ""
echo "📚 For detailed instructions, see README_PRODUCTION.md"