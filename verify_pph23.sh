#!/bin/bash
# PPh 23 System Verification Script

echo "🔍 Verifying PPh 23 Implementation..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0

# Check 1: PPh 23 Exporter exists
echo -n "1. Checking PPh 23 Exporter file... "
if [ -f "backend/exporters/pph23_exporter.py" ]; then
    echo -e "${GREEN}✓ EXISTS${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ MISSING${NC}"
    ((FAIL++))
fi

# Check 2: Smart Mapper template exists
echo -n "2. Checking PPh 23 Smart Mapper template... "
if [ -f "backend/templates/pph23_template.json" ]; then
    echo -e "${GREEN}✓ EXISTS${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ MISSING${NC}"
    ((FAIL++))
fi

# Check 3: Python syntax check
echo -n "3. Checking Python syntax... "
if python3 -m py_compile backend/exporters/pph23_exporter.py 2>/dev/null; then
    echo -e "${GREEN}✓ VALID${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ SYNTAX ERROR${NC}"
    ((FAIL++))
fi

# Check 4: JSON syntax check
echo -n "4. Checking JSON template syntax... "
if python3 -c "import json; json.load(open('backend/templates/pph23_template.json'))" 2>/dev/null; then
    echo -e "${GREEN}✓ VALID${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ INVALID JSON${NC}"
    ((FAIL++))
fi

# Check 5: Exporter has 20 columns
echo -n "5. Checking PPh 23 columns count... "
COLUMN_COUNT=$(grep -c '\"' backend/exporters/pph23_exporter.py | head -1)
if grep -q '"Nama Penandatangan"' backend/exporters/pph23_exporter.py; then
    echo -e "${GREEN}✓ 20 COLUMNS${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ INCORRECT${NC}"
    ((FAIL++))
fi

# Check 6: Export Factory registration
echo -n "6. Checking Export Factory registration... "
if grep -q 'pph23.*PPh23Exporter' backend/exporters/export_factory.py; then
    echo -e "${GREEN}✓ REGISTERED${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ NOT REGISTERED${NC}"
    ((FAIL++))
fi

# Check 7: Router handles PPh 23
echo -n "7. Checking export router integration... "
if grep -q "pph23.*PPh23Exporter" backend/routers/exports.py; then
    echo -e "${GREEN}✓ INTEGRATED${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ MISSING INTEGRATION${NC}"
    ((FAIL++))
fi

# Check 8: Frontend has PPh 23 configured
echo -n "8. Checking frontend Upload page... "
if grep -q "id: 'pph23'" src/pages/Upload.tsx; then
    echo -e "${GREEN}✓ CONFIGURED${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ NOT CONFIGURED${NC}"
    ((FAIL++))
fi

# Check 9: Template has required sections
echo -n "9. Checking template structure... "
if grep -q '"dokumen"' backend/templates/pph23_template.json && \
   grep -q '"penerima"' backend/templates/pph23_template.json && \
   grep -q '"pemotong"' backend/templates/pph23_template.json && \
   grep -q '"objek_pajak"' backend/templates/pph23_template.json && \
   grep -q '"financials"' backend/templates/pph23_template.json; then
    echo -e "${GREEN}✓ ALL SECTIONS PRESENT${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ MISSING SECTIONS${NC}"
    ((FAIL++))
fi

# Check 10: Exporter has Smart Mapper integration
echo -n "10. Checking Smart Mapper integration... "
if grep -q '_convert_smart_mapped_to_structured' backend/exporters/pph23_exporter.py; then
    echo -e "${GREEN}✓ INTEGRATED${NC}"
    ((PASS++))
else
    echo -e "${RED}✗ NOT INTEGRATED${NC}"
    ((FAIL++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Results: ${GREEN}${PASS} passed${NC} | ${RED}${FAIL} failed${NC}"

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! PPh 23 system is ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some checks failed. Please review the errors above.${NC}"
    exit 1
fi
