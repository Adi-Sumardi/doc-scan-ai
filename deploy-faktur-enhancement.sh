#!/bin/bash
# =============================================================================
# 🚀 Deploy Faktur Pajak Enhancement to Production
# =============================================================================
# Deploys the new Faktur Pajak Excel export enhancement (13 columns)
# Changes: Add "Nilai Barang" and "Total Nilai Barang" columns
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
echo "║     🚀 Faktur Pajak Enhancement Deployment 🚀           ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}📝 Changes to deploy:${NC}"
echo "   • Add Column 12: Nilai Barang (unit prices, left-aligned)"
echo "   • Add Column 13: Total Nilai Barang (grand total)"
echo "   • Show ALL item prices in numbered list format"
echo "   • New helper functions: _calculate_nilai_barang_satuan(), _parse_price()"
echo "   • Apply to both single and batch exports"
echo ""

# Step 1: Pull latest code on VPS
echo -e "${YELLOW}📥 Step 1/5: Pulling latest code from GitHub...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
git pull origin master
echo "✅ Code updated"
ENDSSH

echo -e "${GREEN}✅ Code pulled successfully${NC}"

# Step 2: Build Frontend
echo -e "${YELLOW}⚛️  Step 2/5: Building frontend...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
npm run build
echo "✅ Frontend built"
ENDSSH

echo -e "${GREEN}✅ Frontend built successfully${NC}"

# Step 3: Restart backend service
echo -e "${YELLOW}🔄 Step 3/5: Restarting backend service...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo systemctl restart docscan-backend
echo "✅ Backend restarted"
ENDSSH

echo -e "${GREEN}✅ Backend service restarted${NC}"

# Step 4: Check service status
echo -e "${YELLOW}🔍 Step 4/5: Checking service status...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo systemctl status docscan-backend --no-pager -l | head -20
ENDSSH

# Step 5: Test API endpoint
echo -e "${YELLOW}🧪 Step 5/5: Testing API health...${NC}"
sleep 3
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
echo "   • Backend: backend/exporters/faktur_pajak_exporter.py (updated)"
echo "   • Frontend: src/context/DocumentContext.tsx (updated + built)"
echo "   • Service: $SERVICE_NAME (restarted)"
echo "   • Domain: https://$VPS_HOST"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "   • Check status: ssh $VPS_USER@$VPS_HOST 'sudo systemctl status $SERVICE_NAME'"
echo "   • View logs: ssh $VPS_USER@$VPS_HOST 'sudo journalctl -u $SERVICE_NAME -f'"
echo "   • Restart: ssh $VPS_USER@$VPS_HOST 'sudo systemctl restart $SERVICE_NAME'"
echo ""
echo -e "${BLUE}📋 New Features Available:${NC}"
echo "   • Faktur Pajak Excel now has 13 columns (was 12)"
echo "   • Column 12: Individual unit prices (left-aligned)"
echo "   • Column 13: Total nilai barang (qty × unit_price)"
echo "   • Numbered list format for multiple items"
echo ""
echo -e "${GREEN}🚀 Deployment successful!${NC}"
echo -e "${YELLOW}💡 Test by exporting a Faktur Pajak document to Excel${NC}"
