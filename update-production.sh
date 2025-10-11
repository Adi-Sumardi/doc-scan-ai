#!/bin/bash

# Production Update Script for Doc Scan AI v2.0.0
# This script updates the production server with bug fixes

set -e  # Exit on error

echo "=========================================="
echo "Doc Scan AI - Production Update v2.0.0"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/home/yapi/doc-scan-ai"  # Change this to your actual path
BACKEND_SERVICE="docscan-backend"     # Your systemd service name
BACKUP_DIR="/home/yapi/backups"

echo -e "${BLUE}Configuration:${NC}"
echo "  Project: $PROJECT_DIR"
echo "  Service: $BACKEND_SERVICE"
echo "  Backup:  $BACKUP_DIR"
echo ""

# Function to print step
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_step "Production update script ready"
print_success "Run with: sudo ./update-production.sh"

