#!/bin/bash
# =============================================================================
# MySQL Database Setup for Doc Scan AI
# =============================================================================

set -e

echo "🗄️  Setting up MySQL database..."

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DB_NAME="docscan_db"
DB_USER="docuser"
DB_PASS="$1"  # Password from argument

if [ -z "$DB_PASS" ]; then
    echo -e "${RED}❌ Usage: $0 <database_password>${NC}"
    exit 1
fi

# Check if MySQL is installed
if ! command -v mysql &> /dev/null; then
    echo -e "${YELLOW}📦 Installing MySQL...${NC}"
    sudo apt update
    sudo apt install -y mysql-server
    sudo systemctl start mysql
    sudo systemctl enable mysql
fi

echo "✅ MySQL is installed"

# Create database and user
echo "📊 Creating database and user..."

sudo mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';"
sudo mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

echo -e "${GREEN}✅ Database created: ${DB_NAME}${NC}"
echo -e "${GREEN}✅ User created: ${DB_USER}${NC}"

# Test connection
if mysql -u${DB_USER} -p${DB_PASS} -e "USE ${DB_NAME};" 2>/dev/null; then
    echo -e "${GREEN}✅ Database connection test: SUCCESS${NC}"
else
    echo -e "${RED}❌ Database connection test: FAILED${NC}"
    exit 1
fi

echo ""
echo "🎉 MySQL setup complete!"
echo "   Database: ${DB_NAME}"
echo "   User: ${DB_USER}"
echo "   Connection: mysql+pymysql://${DB_USER}:${DB_PASS}@localhost:3306/${DB_NAME}"
