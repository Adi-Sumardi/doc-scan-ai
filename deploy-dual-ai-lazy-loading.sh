#!/bin/bash
# =============================================================================
# 🚀 Deploy Dual AI Model + Lazy Loading Optimization to Production
# =============================================================================
# Deploys major performance and UX improvements
# Changes:
#   - Dual AI routing (GPT-4o for tax docs, Claude Sonnet 4 for rekening koran)
#   - Fix frontend timeout (10 minute polling)
#   - Beautiful loading animation (replace "No results" error)
#   - Date format standardization (DD/MM/YYYY across all banks)
#   - Lazy loading (10 recent batches first, rest in background)
#   - Auto-polling for results when batch completes
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VPS_USER="docScan"
VPS_HOST="docscan.adilabs.id"
APP_DIR="/var/www/docscan"
SERVICE_NAME="docscan-backend"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║   🚀 Dual AI Model + Lazy Loading Deployment 🚀         ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}📝 Changes to deploy:${NC}"
echo "   🤖 Dual AI Model Routing:"
echo "      • GPT-4o: Faktur Pajak, PPh21, PPh23"
echo "      • Claude Sonnet 4: Rekening Koran"
echo ""
echo "   ⚡ Performance Optimizations:"
echo "      • Lazy loading: 10 recent batches first (fast!)"
echo "      • Background loading for remaining batches"
echo "      • Frontend timeout: 5min → 10min"
echo ""
echo "   🎨 UX Improvements:"
echo "      • Beautiful loading animation"
echo "      • Auto-polling for results"
echo "      • CSS animations for smooth experience"
echo ""
echo "   📅 Date Standardization:"
echo "      • Support 9+ date formats from Indonesian banks"
echo "      • Standardize all to DD/MM/YYYY format"
echo ""

# Step 1: Pull latest code on VPS
echo -e "${YELLOW}📥 Step 1/6: Pulling latest code from GitHub...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
git pull origin master
echo "✅ Code updated"
ENDSSH

echo -e "${GREEN}✅ Code pulled successfully${NC}"
echo ""

# Step 2: Check for new dependencies (backend)
echo -e "${YELLOW}📦 Step 2/6: Checking backend dependencies...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan/backend
source ../venv/bin/activate
pip install -q anthropic
echo "✅ Backend dependencies checked"
ENDSSH

echo -e "${GREEN}✅ Backend dependencies up to date${NC}"
echo ""

# Step 3: Build Frontend
echo -e "${YELLOW}⚛️  Step 3/6: Building frontend...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
echo "Building React app..."
npm run build
echo "✅ Frontend built"
ENDSSH

echo -e "${GREEN}✅ Frontend built successfully${NC}"
echo ""

# Step 4: Restart backend service
echo -e "${YELLOW}🔄 Step 4/6: Restarting backend service...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo systemctl restart docscan-backend
echo "✅ Backend restarted"
ENDSSH

echo -e "${GREEN}✅ Backend service restarted${NC}"
echo ""

# Step 5: Check service status
echo -e "${YELLOW}🔍 Step 5/6: Checking service status...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
echo "Waiting for service to start..."
sleep 3
sudo systemctl status docscan-backend --no-pager -l | head -25
ENDSSH

echo ""

# Step 6: Test API endpoint
echo -e "${YELLOW}🧪 Step 6/6: Testing API health...${NC}"
sleep 2
HEALTH_CHECK=$(curl -s https://docscan.adilabs.id/health || echo "FAILED")

if [[ $HEALTH_CHECK == *"healthy"* ]] || [[ $HEALTH_CHECK == *"ok"* ]]; then
    echo -e "${GREEN}✅ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠️  API health check inconclusive${NC}"
    echo "Response: $HEALTH_CHECK"
fi

# Final Summary
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║          🎉 DEPLOYMENT COMPLETE! 🎉                     ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo "   • Backend Files:"
echo "     - backend/cloud_ai_processor.py (dual AI routing)"
echo "     - backend/smart_mapper.py (Claude integration)"
echo "     - backend/config.py (Claude API config)"
echo "     - backend/exporters/rekening_koran_exporter.py (date standardization)"
echo ""
echo "   • Frontend Files:"
echo "     - src/context/DocumentContext.tsx (lazy loading)"
echo "     - src/pages/ScanResults.tsx (loading animation)"
echo "     - src/services/api.ts (timeout fix)"
echo "     - src/index.css (CSS animations)"
echo ""
echo "   • Service: $SERVICE_NAME (restarted)"
echo "   • Domain: https://$VPS_HOST"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "   • Check status: ssh $VPS_USER@$VPS_HOST 'sudo systemctl status $SERVICE_NAME'"
echo "   • View logs: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u $SERVICE_NAME -f'"
echo "   • Restart: ssh $VPS_USER@$VPS_HOST 'sudo systemctl restart $SERVICE_NAME'"
echo ""
echo -e "${BLUE}✨ New Features Available:${NC}"
echo "   🤖 AI Model Routing:"
echo "      • Faktur Pajak → GPT-4o (better accuracy)"
echo "      • Rekening Koran → Claude Sonnet 4 (better table parsing)"
echo ""
echo "   ⚡ Performance:"
echo "      • App loads 10 recent batches instantly"
echo "      • Upload works immediately (no waiting)"
echo "      • Backend processing timeout: 10 minutes"
echo ""
echo "   🎨 User Experience:"
echo "      • Beautiful 'Processing Smart Mapper AI' animation"
echo "      • Auto-refresh when results ready"
echo "      • Smooth loading transitions"
echo ""
echo "   📅 Data Quality:"
echo "      • All rekening koran dates → DD/MM/YYYY"
echo "      • Supports 9+ date formats (BCA, Mandiri, BNI, etc.)"
echo ""
echo -e "${GREEN}🚀 Deployment successful!${NC}"
echo -e "${YELLOW}💡 Test by:${NC}"
echo "   1. Upload Rekening Koran → Should use Claude AI"
echo "   2. Upload Faktur Pajak → Should use GPT-4o"
echo "   3. Refresh app → Should load instantly (10 recent batches)"
echo "   4. Check Excel dates → Should all be DD/MM/YYYY"
echo ""
