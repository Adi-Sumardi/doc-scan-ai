#!/bin/bash

# Deploy SweetAlert2 Update to Production
# Run this script on production server via Termius

set -e  # Exit on error

echo "🚀 Starting deployment..."
echo ""

# Navigate to project directory
cd /var/www/docscan || { echo "❌ Directory not found"; exit 1; }

echo "📥 Pulling latest code from GitHub..."
sudo -u docScan git pull origin master

echo ""
echo "📦 Installing dependencies (sweetalert2)..."
sudo -u docScan npm install

echo ""
echo "🔨 Building production bundle..."
sudo -u docScan npm run build

echo ""
echo "🔄 Restarting Nginx..."
sudo systemctl restart nginx

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Open https://docscan.adilabs.id/history"
echo "2. Filter status 'Error'"
echo "3. Click Delete button on any error batch"
echo "4. Verify SweetAlert2 dialog appears"
echo "5. Confirm deletion"
echo "6. Should see error: 'Backend endpoint belum tersedia' (expected until backend implements DELETE endpoint)"
echo ""
echo "📝 Backend implementation guide: BACKEND_DELETE_BATCH.md"
