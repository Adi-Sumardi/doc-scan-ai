#!/bin/bash
# 🚀 Install Python Dependencies for Hostinger
# Script khusus untuk install pip dan dependencies

echo "🐍 Python Dependencies Installer"
echo "================================"

# Cek Python version
echo "🔍 Checking Python..."
python3 --version
echo "Python location: $(which python3)"

# Method 1: Try to install pip using get-pip.py
echo ""
echo "📦 Method 1: Installing pip via get-pip.py..."
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo "Downloading get-pip.py..."
    curl -s https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    if [ -f "get-pip.py" ]; then
        echo "Installing pip..."
        python3 get-pip.py --user
        rm get-pip.py
        
        # Add pip to PATH if needed
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        export PATH="$HOME/.local/bin:$PATH"
        
        echo "✅ pip installation attempted"
    else
        echo "❌ Failed to download get-pip.py"
    fi
else
    echo "✅ pip already available"
fi

# Method 2: Try ensurepip
echo ""
echo "📦 Method 2: Trying ensurepip..."
python3 -m ensurepip --user 2>/dev/null && echo "✅ ensurepip successful" || echo "⚠️  ensurepip not available"

# Check if pip is now available
echo ""
echo "🔍 Checking pip availability..."
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
    echo "✅ Found pip3"
elif python3 -m pip --version &> /dev/null; then
    PIP_CMD="python3 -m pip"
    echo "✅ Found python3 -m pip"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    echo "✅ Found pip"
else
    echo "❌ No pip found! Manual installation needed."
    echo ""
    echo "🔧 Manual alternatives:"
    echo "1. Contact Hostinger support to enable pip"
    echo "2. Use PHP version of the app instead"
    echo "3. Manually download Python packages"
    exit 1
fi

# Install essential packages
echo ""
echo "📦 Installing essential packages..."
cd backend

# Try to install minimal packages first
echo "Installing core packages..."
$PIP_CMD install --user fastapi uvicorn python-multipart || echo "⚠️  Core packages failed"

echo "Installing database packages..."
$PIP_CMD install --user sqlalchemy pymysql || echo "⚠️  Database packages failed"

echo "Installing basic image processing..."
$PIP_CMD install --user Pillow || echo "⚠️  Pillow failed"

echo "Installing utilities..."
$PIP_CMD install --user python-dotenv requests pydantic || echo "⚠️  Utilities failed"

# Test if we can import basic modules
echo ""
echo "🧪 Testing Python imports..."
python3 -c "
try:
    import fastapi
    print('✅ FastAPI imported successfully')
except ImportError:
    print('❌ FastAPI import failed')

try:
    import uvicorn
    print('✅ Uvicorn imported successfully')
except ImportError:
    print('❌ Uvicorn import failed')

try:
    import sqlalchemy
    print('✅ SQLAlchemy imported successfully')
except ImportError:
    print('❌ SQLAlchemy import failed')

try:
    import pymysql
    print('✅ PyMySQL imported successfully')
except ImportError:
    print('❌ PyMySQL import failed')
"

echo ""
echo "🎉 Installation complete!"
echo "========================"
echo "Next steps:"
echo "1. Test the backend: cd backend && python3 main.py"
echo "2. Check what packages are available: $PIP_CMD list --user"