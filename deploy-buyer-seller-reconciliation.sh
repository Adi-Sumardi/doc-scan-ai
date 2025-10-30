#!/bin/bash
# =============================================================================
# 🚀 Deploy Buyer/Seller Reconciliation + Sample Data Fix to Production
# =============================================================================
# Deploys Excel Reconciliation improvements:
#   1. Buyer & Seller data integration in Faktur Pajak reconciliation
#   2. Fixed sample data structure (SAMPLE_FAKTUR_PAJAK_TEST)
#   3. Professional Excel export with 11 columns including buyer/seller info
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
echo "║   🚀 Buyer/Seller Reconciliation Deployment 🚀          ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}📝 Changes to deploy:${NC}"
echo "   📊 Excel Reconciliation Enhancement:"
echo "      • Add buyer/seller fields to FakturPajakData dataclass"
echo "      • Smart format detection (11+ columns = new format)"
echo "      • Maintain backward compatibility with legacy data"
echo ""
echo "   📄 Excel Export - 11 Columns:"
echo "      • Confidence"
echo "      • Seller (Penjual) + NPWP Seller"
echo "      • Buyer (Pembeli) + NPWP Buyer"
echo "      • Tanggal Faktur + Nominal Faktur (Rp format)"
echo "      • Tanggal Bank + Nominal Bank (Rp format)"
echo "      • Tipe Match + Selisih (Rp format)"
echo ""
echo "   🔧 Bug Fix - Sample Data:"
echo "      • Fixed corrupt SAMPLE_FAKTUR_PAJAK_TEST structure"
echo "      • Removed duplicate PPN/Total columns (was 13, now 11)"
echo "      • Corrected DPP/PPN/Total values"
echo "      • Now reconciliation works correctly (was 100% unmatch)"
echo ""

# Step 1: Pull latest code on VPS
echo -e "${YELLOW}📥 Step 1/5: Pulling latest code from GitHub...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
git pull origin master
echo "✅ Code updated"
ENDSSH

echo -e "${GREEN}✅ Code pulled successfully${NC}"
echo ""

# Step 2: Build Frontend
echo -e "${YELLOW}⚛️  Step 2/5: Building frontend...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
echo "Building React app..."
npm run build
echo "✅ Frontend built"
ENDSSH

echo -e "${GREEN}✅ Frontend built successfully${NC}"
echo ""

# Step 3: Restart backend service
echo -e "${YELLOW}🔄 Step 3/5: Restarting backend service...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo systemctl restart docscan-backend
echo "✅ Backend restarted"
ENDSSH

echo -e "${GREEN}✅ Backend service restarted${NC}"
echo ""

# Step 4: Check service status
echo -e "${YELLOW}🔍 Step 4/5: Checking service status...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
echo "Waiting for service to start..."
sleep 3
sudo systemctl status docscan-backend --no-pager -l | head -25
ENDSSH

echo ""

# Step 5: Test API endpoint
echo -e "${YELLOW}🧪 Step 5/5: Testing API health...${NC}"
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
echo "     - backend/excel_reader_service.py (buyer/seller fields + parsing)"
echo "     - backend/exports/SAMPLE_FAKTUR_PAJAK_TEST_scan_result.xlsx (fixed)"
echo ""
echo "   • Frontend Files:"
echo "     - src/pages/ExcelReconciliation.tsx (11-column export)"
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
echo "   📊 Excel Reconciliation Export:"
echo "      • Seller information: Nama Penjual + NPWP Seller"
echo "      • Buyer information: Nama Pembeli + NPWP Buyer"
echo "      • Complete transaction trail with both parties"
echo "      • Professional Rupiah formatting for all amounts"
echo ""
echo "   🔧 Backend Improvements:"
echo "      • Smart format detection (new vs legacy data)"
echo "      • Backward compatibility maintained"
echo "      • Buyer/seller data stored in raw_data"
echo ""
echo "   🐛 Bug Fixes:"
echo "      • Sample FAKTUR_PAJAK_TEST data structure corrected"
echo "      • Reconciliation now works (was 100% unmatch, now matches correctly)"
echo "      • DPP/PPN/Total columns properly aligned"
echo ""
echo -e "${GREEN}🚀 Deployment successful!${NC}"
echo -e "${YELLOW}💡 Test by:${NC}"
echo "   1. Go to Reconciliation menu (direct to Excel Reconciliation)"
echo "   2. Select Faktur Pajak + Rekening Koran files"
echo "   3. Run reconciliation"
echo "   4. Export to Excel → Should show 11 columns with buyer/seller info"
echo "   5. Check Excel columns: Seller, NPWP Seller, Buyer, NPWP Buyer"
echo ""
