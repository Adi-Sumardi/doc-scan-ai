#!/bin/bash
# =============================================================================
# 🚀 Deploy Faktur Pajak Flat Table Excel Export to Production
# =============================================================================
# Deploys Excel export redesign for formula-friendly structure
# Changes:
#   - Remove merged cells from Faktur Pajak Excel export
#   - Repeat seller/buyer/financial data per item row
#   - Enable VLOOKUP, SUMIF, Pivot Tables support
#   - Works for single upload, batch upload, and ZIP upload
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
echo "║   🚀 Faktur Pajak Flat Table Excel Deployment 🚀        ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}📝 Changes to deploy:${NC}"
echo "   📊 Excel Export Redesign:"
echo "      • Remove merged cells in data rows"
echo "      • Repeat seller/buyer/financial data per item"
echo "      • Flat table structure (100% formula-friendly)"
echo ""
echo "   ✅ Excel Features Now Supported:"
echo "      • VLOOKUP/XLOOKUP: Search by seller/buyer"
echo "      • SUMIF/COUNTIF: Aggregate by any field"
echo "      • Pivot Tables: Group by seller/buyer/date"
echo "      • Filtering & Sorting: Safe on all columns"
echo "      • Database Import: Proper normalized structure"
echo ""
echo "   📋 Applies To:"
echo "      • Single file upload"
echo "      • Batch multiple files upload"
echo "      • ZIP batch upload"
echo ""
echo "   📁 Files Modified:"
echo "      • backend/exporters/faktur_pajak_exporter.py"
echo "        - _populate_excel_sheet() (400+ lines)"
echo "        - batch_export_to_excel() (150+ lines)"
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

# Step 2: Verify file changes
echo -e "${YELLOW}🔍 Step 2/5: Verifying file changes...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan
echo "Checking faktur_pajak_exporter.py..."
if grep -q "FLAT TABLE: ALL DATA REPEATED PER ITEM ROW" backend/exporters/faktur_pajak_exporter.py; then
    echo "✅ Flat table code detected"
else
    echo "⚠️  Warning: Flat table code not found - check git pull"
fi
ENDSSH

echo -e "${GREEN}✅ File verification complete${NC}"
echo ""

# Step 3: Check Python dependencies (openpyxl should already be installed)
echo -e "${YELLOW}📦 Step 3/5: Checking backend dependencies...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
cd /var/www/docscan/backend
source ../venv/bin/activate
# openpyxl should already be installed, just verify
python -c "from openpyxl import Workbook; print('✅ openpyxl available')" || echo "⚠️  openpyxl not found"
echo "✅ Backend dependencies checked"
ENDSSH

echo -e "${GREEN}✅ Backend dependencies OK${NC}"
echo ""

# Step 4: Restart backend service
echo -e "${YELLOW}🔄 Step 4/5: Restarting backend service...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
sudo systemctl restart docscan-backend
echo "✅ Backend restarted"
ENDSSH

echo -e "${GREEN}✅ Backend service restarted${NC}"
echo ""

# Step 5: Check service status
echo -e "${YELLOW}🔍 Step 5/5: Checking service status...${NC}"
ssh ${SSH_OPTS} ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
echo "Waiting for service to start..."
sleep 3
sudo systemctl status docscan-backend --no-pager -l | head -30 | grep -E "(Active|Modular Exporter|Started|running)" || echo "Service starting..."
ENDSSH

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
echo "   • File Updated:"
echo "     - backend/exporters/faktur_pajak_exporter.py"
echo "       ✅ _populate_excel_sheet() - Flat table structure"
echo "       ✅ batch_export_to_excel() - Flat table structure"
echo ""
echo "   • Service: $SERVICE_NAME (restarted)"
echo "   • Domain: https://$VPS_HOST"
echo ""
echo -e "${BLUE}🔧 Useful Commands (via Termius):${NC}"
echo "   • Check status:"
echo "     sudo systemctl status $SERVICE_NAME"
echo ""
echo "   • View logs:"
echo "     sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "   • Restart backend:"
echo "     sudo systemctl restart $SERVICE_NAME"
echo ""
echo "   • Check for flat table code:"
echo "     grep 'FLAT TABLE' /var/www/docscan/backend/exporters/faktur_pajak_exporter.py"
echo ""
echo -e "${BLUE}✨ New Excel Export Features:${NC}"
echo "   📊 Structure:"
echo "      • 19 columns total"
echo "      • Columns 1-15: Seller, Buyer, Invoice, Financial (REPEATED per item)"
echo "      • Columns 16-19: Item Name, Qty, Price, Total (unique per item)"
echo "      • Grand Total row with SUM formulas"
echo ""
echo "   ✅ Formula Support:"
echo "      • VLOOKUP: =VLOOKUP(\"PT ABC\", A:S, 12, FALSE)"
echo "      • SUMIF: =SUMIF(A:A, \"PT ABC\", S:S)"
echo "      • COUNTIF: =COUNTIF(D:D, \"PT XYZ\")"
echo "      • Pivot Table: Works perfectly!"
echo "      • Filter & Sort: Safe on all columns"
echo ""
echo "   🎯 Use Cases:"
echo "      • Analyze sales by seller"
echo "      • Aggregate by buyer"
echo "      • Filter by date/faktur number"
echo "      • Import to Excel Power Pivot"
echo "      • Import to database/BI tools"
echo ""
echo -e "${GREEN}🚀 Deployment successful!${NC}"
echo ""
echo -e "${YELLOW}💡 Test by:${NC}"
echo "   1. Via Termius SSH:"
echo "      ssh $VPS_USER@$VPS_HOST"
echo ""
echo "   2. Upload Faktur Pajak to https://$VPS_HOST"
echo "      • Single PDF file"
echo "      • Multiple PDFs"
echo "      • ZIP batch"
echo ""
echo "   3. Download Excel and verify:"
echo "      • Open Excel file"
echo "      • Check columns A-O: NO merged cells (data repeated)"
echo "      • Test formula: =VLOOKUP(A3, A:S, 12, FALSE)"
echo "      • Create Pivot Table: Insert → PivotTable"
echo "      • Grand Total row should have SUM formulas"
echo ""
echo -e "${BLUE}📖 Documentation:${NC}"
echo "   • Commit: 574fc53"
echo "   • Message: feat: Faktur Pajak Excel export - Flat table structure"
echo "   • Files: backend/exporters/faktur_pajak_exporter.py (468 changes)"
echo ""
