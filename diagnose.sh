#!/bin/bash

# Production Diagnostic Script for Doc Scan AI
# Usage: ./diagnose.sh

echo "==================================="
echo "Doc Scan AI - Production Diagnostics"
echo "==================================="
echo ""
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# 1. Check Backend Process
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Backend Process Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
BACKEND_RUNNING=$(ps aux | grep -E "(uvicorn|python.*main)" | grep -v grep | wc -l)
if [ $BACKEND_RUNNING -gt 0 ]; then
    print_status 0 "Backend is RUNNING"
    ps aux | grep -E "(uvicorn|python.*main)" | grep -v grep | head -n 3
else
    print_status 1 "Backend is NOT RUNNING!"
    echo "  ${YELLOW}→ Try: sudo systemctl restart docscan-backend${NC}"
fi
echo ""

# 2. Check Nginx
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Nginx Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v systemctl &> /dev/null; then
    if systemctl is-active --quiet nginx; then
        print_status 0 "Nginx is RUNNING"
    else
        print_status 1 "Nginx is NOT RUNNING!"
        echo "  ${YELLOW}→ Try: sudo systemctl restart nginx${NC}"
    fi
else
    echo "  ${YELLOW}⚠${NC} systemctl not available, checking process..."
    if pgrep nginx > /dev/null; then
        print_status 0 "Nginx process found"
    else
        print_status 1 "Nginx process not found!"
    fi
fi
echo ""

# 3. Check Database File
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Database Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "backend/database.db" ]; then
    print_status 0 "Database file exists"
    ls -lh backend/database.db

    # Check database size
    DB_SIZE=$(stat -f%z backend/database.db 2>/dev/null || stat -c%s backend/database.db 2>/dev/null)
    if [ $DB_SIZE -gt 8192 ]; then
        print_status 0 "Database has data (size: $DB_SIZE bytes)"
    else
        print_status 1 "Database appears empty (size: $DB_SIZE bytes)"
    fi

    # Check permissions
    DB_PERMS=$(stat -f%A backend/database.db 2>/dev/null || stat -c%a backend/database.db 2>/dev/null)
    if [ "$DB_PERMS" = "644" ] || [ "$DB_PERMS" = "664" ] || [ "$DB_PERMS" = "666" ]; then
        print_status 0 "Database permissions OK ($DB_PERMS)"
    else
        print_status 1 "Database permissions may be wrong ($DB_PERMS)"
        echo "  ${YELLOW}→ Try: sudo chmod 644 backend/database.db${NC}"
    fi
else
    print_status 1 "Database file NOT found!"
    echo "  ${YELLOW}→ Database should be at: backend/database.db${NC}"
fi
echo ""

# 4. Check Folders
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Folder Permissions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for folder in "backend/uploads" "backend/results" "backend/exports"; do
    if [ -d "$folder" ]; then
        print_status 0 "$folder exists"
        ls -ld "$folder"
    else
        print_status 1 "$folder NOT found!"
        echo "  ${YELLOW}→ Try: mkdir -p $folder && chmod 755 $folder${NC}"
    fi
done
echo ""

# 5. Check Backend Logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Recent Backend Logs (last 15 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "backend/server.log" ]; then
    print_status 0 "Log file found"
    echo ""
    tail -n 15 backend/server.log
else
    print_status 1 "No server.log found"
    echo "  ${YELLOW}⚠${NC} Backend may be logging to stdout/stderr"
    echo "  ${YELLOW}→ Try: journalctl -u docscan-backend -n 20${NC}"
fi
echo ""

# 6. Check Nginx Logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Recent Nginx Errors (last 10 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "/var/log/nginx/error.log" ]; then
    print_status 0 "Nginx error log found"
    echo ""
    sudo tail -n 10 /var/log/nginx/error.log 2>/dev/null || tail -n 10 /var/log/nginx/error.log
else
    print_status 1 "Nginx error log not found"
fi
echo ""

# 7. Test API Health
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. API Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v curl &> /dev/null; then
    # Try localhost first
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        print_status 0 "Backend API responding (localhost:8000)"
    else
        print_status 1 "Backend API not responding on localhost:8000 (HTTP $HTTP_CODE)"
    fi

    # Try production domain
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://docscan.adilabs.id/api/health 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        print_status 0 "Production API responding (docscan.adilabs.id)"
    else
        print_status 1 "Production API not responding (HTTP $HTTP_CODE)"
    fi
else
    echo "  ${YELLOW}⚠${NC} curl not available"
fi
echo ""

# 8. Check System Resources
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. System Resources"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Disk space
echo "Disk Space:"
df -h | grep -E "(Filesystem|/$|/home)" || df -h | head -n 2

# Memory
echo ""
echo "Memory:"
free -h 2>/dev/null || vm_stat | head -n 5

# Load average
echo ""
echo "Load Average:"
uptime
echo ""

# 9. Check Network Connectivity
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. Network Connectivity"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v nc &> /dev/null; then
    if nc -z localhost 8000 2>/dev/null; then
        print_status 0 "Port 8000 is open (backend)"
    else
        print_status 1 "Port 8000 is not accessible"
    fi

    if nc -z localhost 80 2>/dev/null; then
        print_status 0 "Port 80 is open (nginx)"
    else
        print_status 1 "Port 80 is not accessible"
    fi
else
    echo "  ${YELLOW}⚠${NC} nc (netcat) not available"
fi
echo ""

# 10. Summary & Recommendations
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "10. Recommendations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ISSUES=0

if [ $BACKEND_RUNNING -eq 0 ]; then
    echo "${RED}!${NC} Backend is not running"
    echo "   → sudo systemctl restart docscan-backend"
    ISSUES=$((ISSUES + 1))
fi

if [ ! -f "backend/database.db" ]; then
    echo "${RED}!${NC} Database file missing"
    echo "   → Check backend configuration"
    ISSUES=$((ISSUES + 1))
fi

if [ ! -d "backend/uploads" ] || [ ! -d "backend/results" ]; then
    echo "${RED}!${NC} Required folders missing"
    echo "   → mkdir -p backend/{uploads,results,exports}"
    echo "   → sudo chown -R www-data:www-data backend/"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "${GREEN}✓${NC} No critical issues detected!"
    echo ""
    echo "If batches still not showing, check:"
    echo "1. Browser console (F12) for frontend errors"
    echo "2. API authentication (token valid?)"
    echo "3. Database has actual batch data"
else
    echo ""
    echo "${YELLOW}⚠${NC} Found $ISSUES critical issue(s)"
    echo ""
    echo "Quick fix commands:"
    echo "  sudo systemctl restart docscan-backend"
    echo "  sudo systemctl restart nginx"
    echo "  sudo chown -R www-data:www-data backend/"
    echo "  sudo chmod -R 755 backend/"
    echo "  sudo chmod 644 backend/*.db"
fi

echo ""
echo "==================================="
echo "Diagnostics Complete"
echo "==================================="
echo ""
echo "For detailed troubleshooting, see: PRODUCTION_DEBUG.md"
