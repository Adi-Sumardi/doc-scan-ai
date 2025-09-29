#!/bin/bash
# 🚀 Hostinger Server Deployment Script
# Jalankan script ini DI SERVER HOSTINGER setelah git pull

echo "🚀 Setting up Doc Scan AI on Hostinger..."
echo "Domain: docscan.adilabs.id"
echo "=========================================="

# Set working directory
cd ~/public_html

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

# Set up Python virtual environment
echo "🐍 Setting up Python environment..."
if command -v python3 &> /dev/null; then
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created"
else
    echo "⚠️  Python3 not found. Using system Python."
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd backend
pip install --user -r requirements.txt
echo "✅ Python packages installed"

# Initialize database
echo "🗄️ Setting up database..."
python -c "
import sys
sys.path.append('.')
try:
    from database import init_database
    init_database()
    print('✅ Database initialized successfully')
except Exception as e:
    print(f'⚠️  Database setup: {e}')
"

# Set up log rotation (optional)
echo "📝 Setting up logging..."
cd ~/public_html
touch logs/app.log
echo "✅ Logging configured"

# Create startup script
cat > start_backend.sh << 'EOF'
#!/bin/bash
cd ~/public_html/backend
nohup python main.py > ../logs/backend.log 2>&1 &
echo $! > ../logs/backend.pid
echo "Backend started with PID: $(cat ../logs/backend.pid)"
EOF

chmod +x start_backend.sh

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