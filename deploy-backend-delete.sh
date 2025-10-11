#!/bin/bash

# Deploy Backend DELETE Endpoint to Production
# Run this script on production server via Termius

set -e  # Exit on error

echo "🚀 Starting backend deployment..."
echo ""

# Navigate to project directory
cd /var/www/docscan || { echo "❌ Directory not found"; exit 1; }

echo "📥 Pulling latest backend code from GitHub..."
sudo -u docScan git pull origin master

echo ""
echo "🔄 Restarting backend service..."
sudo systemctl restart docscan-backend

echo ""
echo "⏳ Waiting for service to start..."
sleep 3

echo ""
echo "✅ Checking backend service status..."
sudo systemctl status docscan-backend --no-pager -l | head -20

echo ""
echo "✅ Backend deployment completed!"
echo ""
echo "📋 Testing DELETE endpoint:"
echo ""
echo "1. Via Browser:"
echo "   - Open https://docscan.adilabs.id/history"
echo "   - Filter status 'Error'"
echo "   - Click Delete button"
echo "   - Should now work successfully!"
echo ""
echo "2. Via curl (replace BATCH_ID and TOKEN):"
echo "   curl -X DELETE https://docscan.adilabs.id/api/batches/BATCH_ID \\"
echo "        -H 'Authorization: Bearer YOUR_TOKEN'"
echo ""
echo "📝 Features:"
echo "   ✅ Authentication & Authorization"
echo "   ✅ Only error/failed batches can be deleted"
echo "   ✅ Owner or admin only"
echo "   ✅ Deletes physical files from disk"
echo "   ✅ Cascade delete: results -> files -> batch"
echo "   ✅ Transaction safety with rollback"
echo "   ✅ Comprehensive logging"
echo ""
