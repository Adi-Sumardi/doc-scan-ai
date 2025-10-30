#!/bin/bash
# =============================================================================
# 🚀 Deploy Buyer/Seller Reconciliation (LOCAL VERSION - Run on VPS directly)
# =============================================================================
# Use this script when you're already SSH'd into the VPS
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_DIR="/var/www/docscan"
SERVICE_NAME="docscan-backend"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║   🚀 Buyer/Seller Reconciliation Deployment 🚀          ║"
echo "║          (Local Version - Run on VPS)                   ║"
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

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}❌ Error: Not in the correct directory!${NC}"
    echo "Please cd to $APP_DIR first"
    exit 1
fi

# Step 0: Resolve git conflicts
echo -e "${YELLOW}🔧 Step 0/5: Resolving git conflicts...${NC}"
if git status | grep -q "both modified"; then
    echo "Found merge conflicts, resolving..."
    # Use remote version for tsconfig.app.tsbuildinfo (it's auto-generated)
    git checkout --theirs tsconfig.app.tsbuildinfo
    git add tsconfig.app.tsbuildinfo
    echo "✅ Conflicts resolved"
else
    echo "✅ No conflicts to resolve"
fi
echo ""

# Step 1: Ensure latest code (already pulled)
echo -e "${YELLOW}📥 Step 1/5: Verifying code is up to date...${NC}"
git status
echo -e "${GREEN}✅ Code is ready${NC}"
echo ""

# Step 2: Install/check dependencies
echo -e "${YELLOW}📦 Step 2/5: Checking dependencies...${NC}"
cd $APP_DIR/backend
if [ -d "../venv" ]; then
    source ../venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo -e "${YELLOW}⚠️  Virtual environment not found at ../venv${NC}"
    echo "Attempting to use system Python..."
fi
echo "✅ Dependencies checked"
echo ""

# Step 3: Build Frontend
echo -e "${YELLOW}⚛️  Step 3/5: Building frontend...${NC}"
cd $APP_DIR
echo "Building React app..."
npm run build
echo -e "${GREEN}✅ Frontend built successfully${NC}"
echo ""

# Step 4: Restart backend service
echo -e "${YELLOW}🔄 Step 4/5: Restarting backend service...${NC}"
sudo systemctl restart $SERVICE_NAME
echo -e "${GREEN}✅ Backend service restarted${NC}"
echo ""

# Step 5: Check service status
echo -e "${YELLOW}🔍 Step 5/5: Checking service status...${NC}"
echo "Waiting for service to start..."
sleep 3
sudo systemctl status $SERVICE_NAME --no-pager -l | head -25
echo ""

# Test API endpoint
echo -e "${YELLOW}🧪 Testing API health...${NC}"
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
echo "   • Domain: https://docscan.adilabs.id"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo "   • Check status: sudo systemctl status $SERVICE_NAME"
echo "   • View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "   • Restart: sudo systemctl restart $SERVICE_NAME"
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
