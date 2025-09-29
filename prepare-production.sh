#!/bin/bash
# Script untuk menyiapkan file production yang ready untuk upload ke Hostinger

echo "🚀 Preparing production files for Hostinger deployment..."

# Create production directory
mkdir -p production_files

# Copy dist files (frontend)
cp -r dist/* production_files/
echo "✅ Frontend files copied from dist/"

# Copy backend files
cp -r backend production_files/
echo "✅ Backend files copied"

# Copy configuration files
cp .htaccess production_files/
cp api.php production_files/
cp .env.production production_files/backend/.env
echo "✅ Configuration files copied"

# Create necessary directories
mkdir -p production_files/uploads
mkdir -p production_files/exports
mkdir -p production_files/logs
echo "✅ Required directories created"

# Create upload instructions
cat > production_files/UPLOAD_INSTRUCTIONS.txt << 'EOF'
🚀 HOSTINGER UPLOAD INSTRUCTIONS

1. Upload ALL contents of this production_files folder to your public_html/ directory
2. Struktur yang benar di Hostinger:
   public_html/
   ├── index.html (from dist)
   ├── assets/ (from dist/assets)
   ├── .htaccess
   ├── api.php
   ├── backend/
   │   ├── *.py files
   │   ├── requirements.txt
   │   └── .env
   ├── uploads/ (empty folder)
   ├── exports/ (empty folder)
   └── logs/ (empty folder)

3. Setup database MySQL di panel Hostinger
4. Update file backend/.env dengan kredensial database
5. Install Python dependencies di server

NEXT STEPS AFTER UPLOAD:
- Setup database MySQL
- Configure backend/.env
- Install Python packages
- Test at https://docscan.adilabs.id
EOF

echo ""
echo "🎉 Production files ready!"
echo "📁 All files are in: production_files/"
echo "📋 Check UPLOAD_INSTRUCTIONS.txt for upload guide"
echo ""
echo "File structure:"
ls -la production_files/