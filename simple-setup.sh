#!/bin/bash
# 🚀 Simple Hostinger Setup Script
# Script sederhana untuk deploy di Hostinger

echo "🚀 Simple Doc Scan AI Setup"
echo "=========================="

# Cek lokasi saat ini
echo "📍 Current directory: $(pwd)"

# Buat direktori yang diperlukan
echo "📁 Creating directories..."
mkdir -p uploads exports logs
chmod 755 uploads exports logs

# Copy file production ke tempat yang benar
echo "📋 Setting up files..."
if [ -f "production_files/index.html" ]; then
    cp production_files/index.html .
    cp -r production_files/assets .
    cp production_files/.htaccess .
    cp production_files/api.php .
    echo "✅ Frontend files copied"
else
    echo "⚠️  production_files not found, using existing files"
fi

# Cek Python yang tersedia
echo "🐍 Checking Python..."
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found!"
    exit 1
fi

echo "✅ Using: $PYTHON_CMD"

# Install minimal dependencies
echo "📦 Installing basic packages..."
cd backend
$PYTHON_CMD -m pip install --user fastapi uvicorn sqlalchemy pymysql python-multipart || echo "⚠️  Some packages failed"

# Buat startup script sederhana
cd ..
cat > start_simple.sh << EOF
#!/bin/bash
echo "🚀 Starting Doc Scan AI Backend..."
cd backend
$PYTHON_CMD main.py
EOF

chmod +x start_simple.sh

echo ""
echo "✅ Simple setup complete!"
echo "========================"
echo "🚀 To start backend: ./start_simple.sh"
echo "🌐 Frontend: https://docscan.adilabs.id"
echo "🔧 Test API: https://docscan.adilabs.id/api.php/health"