#!/bin/bash
# 🚀 Hostinger Deployment Script for docscan.adilabs.id
# Run this script in your Hostinger hosting environment

echo "🌐 Deploying Doc Scan AI to docscan.adilabs.id"
echo "================================================"

# Set up directories
echo "📁 Setting up directories..."
mkdir -p ~/public_html/uploads
mkdir -p ~/public_html/exports
mkdir -p ~/public_html/logs
mkdir -p ~/public_html/backend
mkdir -p ~/public_html/dist

# Set permissions
chmod 755 ~/public_html/uploads
chmod 755 ~/public_html/exports
chmod 755 ~/public_html/logs

echo "✅ Directories created and permissions set"

# Install Python dependencies (if Python is available)
echo "🐍 Setting up Python environment..."
cd ~/public_html
python3 -m venv doc_scan_env
source doc_scan_env/bin/activate

# Copy backend files
echo "📋 Copying backend files..."
cp -r backend/* ~/public_html/backend/
cd ~/public_html/backend

# Install Python requirements
pip install -r requirements.txt

echo "✅ Backend setup complete"

# Copy frontend build files
echo "🎨 Setting up frontend..."
cp -r dist/* ~/public_html/

# Create .htaccess for React Router
cat > ~/public_html/.htaccess << 'EOF'
# React Router Support
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    RewriteRule ^index\.html$ - [L]
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule . /index.html [L]
</IfModule>

# Security Headers
<IfModule mod_headers.c>
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
</IfModule>

# File Upload Limits
php_value upload_max_filesize 10M
php_value post_max_size 10M
php_value max_execution_time 300

# Cache Control
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
    ExpiresByType image/png "access plus 1 month"
    ExpiresByType image/jpg "access plus 1 month"
    ExpiresByType image/jpeg "access plus 1 month"
    ExpiresByType image/gif "access plus 1 month"
    ExpiresByType image/svg+xml "access plus 1 month"
</IfModule>
EOF

echo "✅ .htaccess configured"

# Create PHP proxy for API calls (since Hostinger may not support direct Python)
cat > ~/public_html/api.php << 'EOF'
<?php
// API Proxy for Doc Scan AI
// Routes API calls to Python backend

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: https://docscan.adilabs.id');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$request_uri = $_SERVER['REQUEST_URI'];
$method = $_SERVER['REQUEST_METHOD'];
$input = file_get_contents('php://input');

// Route to Python backend (adjust port as needed)
$backend_url = 'http://localhost:8000' . str_replace('/api.php', '', $request_uri);

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $backend_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

if ($input) {
    curl_setopt($ch, CURLOPT_POSTFIELDS, $input);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
}

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

http_response_code($http_code);
echo $response;
?>
EOF

echo "✅ PHP API proxy created"

# Create environment file
cp .env.production ~/public_html/backend/.env

echo ""
echo "🎉 Deployment Complete!"
echo "================================================"
echo "Domain: https://docscan.adilabs.id"
echo "Frontend: Deployed to public_html/"
echo "Backend: Available at public_html/backend/"
echo "API Proxy: public_html/api.php"
echo ""
echo "⚡ Next Steps:"
echo "1. Update .env file with your database credentials"
echo "2. Start Python backend: python ~/public_html/backend/main.py"
echo "3. Test the application at https://docscan.adilabs.id"
echo ""
echo "🔧 Manual Configuration Required:"
echo "- Set up MySQL database in Hostinger panel"
echo "- Configure domain DNS if needed"
echo "- Set up SSL certificate"
echo "- Configure cron jobs for cleanup (optional)"