#!/bin/bash
# =============================================================================
# 🚀 Quick Deploy Script - BCA Smart Mapper Fix
# =============================================================================
# Deploys the BCA fix to production VPS
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

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║      🚀 Deploying BCA Smart Mapper Fix to VPS 🚀        ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Pull latest changes on VPS
echo -e "${YELLOW}📥 Step 1/3: Pulling latest changes from GitHub...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
git pull origin master
echo "✅ Code updated"
ENDSSH

echo -e "${GREEN}✅ Latest code pulled successfully${NC}"

# Step 2: Restart backend service
echo -e "${YELLOW}🔄 Step 2/3: Restarting backend service...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo systemctl restart docscan-backend
sleep 3
sudo systemctl status docscan-backend --no-pager -l
ENDSSH

echo -e "${GREEN}✅ Backend restarted successfully${NC}"

# Step 3: Check logs for errors
echo -e "${YELLOW}📋 Step 3/3: Checking backend logs...${NC}"
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo journalctl -u docscan-backend -n 20 --no-pager
ENDSSH

# Final Status
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}║          🎉 DEPLOYMENT COMPLETE! 🎉                     ║${NC}"
echo -e "${GREEN}║                                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}✅ Changes deployed:${NC}"
echo "   1. Smart Mapper max_tokens: 2500 -> 8000"
echo "   2. Transaction description cleaning function added"
echo "   3. Debug logging for saldo_akhir tracking"
echo ""
echo -e "${BLUE}🔍 Test now:${NC}"
echo "   • Upload BCA bank statement"
echo "   • Check if all 90+ transactions extracted"
echo "   • Verify keterangan is cleaned (no prefixes)"
echo "   • Check if saldo_akhir appears in Excel export"
echo ""
echo -e "${YELLOW}📊 Monitor logs in real-time:${NC}"
echo "   ssh ${VPS_USER}@${VPS_HOST}"
echo "   sudo journalctl -u docscan-backend -f"
echo ""
echo -e "${GREEN}🚀 Deployment successful!${NC}"
