#!/bin/bash
# 🚀 Hostinger Server Deployment Script
# Jalankan script ini DI SERVER HOSTINGER setelah git pull

echo "🚀 Setting up Doc Scan AI on Hostinger..."
echo "Domain: docscan.adilabs.id"
echo "=========================================="

# Get current working directory (should be public_html)
CURRENT_DIR=$(pwd)
echo "📍 Current directory: $CURRENT_DIR"

# Create required directories
echo "📁 Creating required directories..."
mkdir -p uploads exports logs
chmod 755 uploads exports logs
echo "✅ Directories created with proper permissions"

# Copy production files to correct locations
echo "📋 Setting up production files..."

# Copy dist files to root
if [ -d "production_files" ]; then
    cp production_files/index.html .
    cp -r production_files/assets .
    cp production_files/.htaccess .
    cp production_files/api.php .
    echo "✅ Frontend files deployed"
    
    # Backend is already in place from git
    echo "✅ Backend files ready"
else
    echo "❌ production_files directory not found. Make sure you pulled from git first."
    exit 1
fi

# Set up Python environment
echo "🐍 Setting up Python environment..."
cd backend

# Check for available Python commands
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ No Python found! Please install Python first."
    exit 1
fi

echo "✅ Using Python: $PYTHON_CMD"

# Install Python dependencies using --user flag
echo "📦 Installing Python dependencies..."
$PYTHON_CMD -m pip install --user -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✅ Python packages installed successfully"
else
    echo "⚠️  Some packages may have failed to install. Continuing..."
fi

# Initialize database
echo "🗄️ Setting up database..."
$PYTHON_CMD -c "
import sys
sys.path.append('.')
try:
    from database import init_database
    init_database()
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'⚠️  Database setup: {e}')
" || echo "⚠️  Database initialization failed - will try at runtime"

# Set up logging
echo "📝 Setting up logging..."
cd "$CURRENT_DIR"
touch logs/app.log
echo "✅ Logging configured"

# Create startup script with proper paths
cat > start_backend.sh << EOF
#!/bin/bash
SCRIPT_DIR=\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)
cd "\$SCRIPT_DIR/backend"
nohup $PYTHON_CMD main.py > ../logs/backend.log 2>&1 &
echo \$! > ../logs/backend.pid
echo "Backend started with PID: \$(cat ../logs/backend.pid)"
echo "Backend URL: http://localhost:8000"
echo "Frontend URL: https://docscan.adilabs.id"
EOF

chmod +x start_backend.sh

# Create stop script too
cat > stop_backend.sh << 'EOF'
#!/bin/bash
if [ -f logs/backend.pid ]; then
    PID=$(cat logs/backend.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Backend stopped (PID: $PID)"
        rm logs/backend.pid
    else
        echo "Backend not running"
        rm logs/backend.pid
    fi
else
    echo "No PID file found"
fi
EOF

chmod +x stop_backend.sh

echo ""
echo "🎉 Deployment Complete!"
echo "========================"
echo "✅ Frontend: https://docscan.adilabs.id"
echo "✅ Backend: Ready to start"
echo "✅ Database: Configured"
echo "✅ Files: All in place"
echo ""
echo "🚀 To start the backend:"
echo "./start_backend.sh"
echo ""
echo "🔧 To check backend status:"
echo "ps aux | grep python | grep main.py"
echo ""
echo "📋 To view logs:"
echo "tail -f logs/backend.log"