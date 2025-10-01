#!/bin/bash
# =============================================================================
# Frontend Rebuild Script for Doc Scan AI
# Handles permission issues automatically
# =============================================================================

set -e

echo "🔄 Rebuilding Frontend..."

# Change ownership to allow build
echo "📝 Setting permissions for build..."
sudo chown -R docScan:docScan dist 2>/dev/null || true

# Run build
echo "🔨 Building React app..."
npm run build

# Set proper ownership for Nginx
echo "🔒 Setting ownership for web server..."
sudo chown -R www-data:www-data dist
sudo chmod -R 755 dist

# Verify
echo ""
echo "✅ Frontend rebuild complete!"
echo "📁 Files in dist/:"
ls -lh dist/
echo ""
echo "🔗 Assets:"
ls -lh dist/assets/ | head -5
echo ""
echo "🌐 Access: https://docscan.adilabs.id"
echo "💡 Hard refresh browser: Ctrl+Shift+R or Cmd+Shift+R"
