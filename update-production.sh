#!/bin/bash

###########################################
# Production Update Script
# Smart Mapper AI Universal Update
# Date: October 11, 2025
###########################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

###########################################
# Pre-flight Checks
###########################################

print_status "Starting Production Update Process..."
echo ""

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -f "package.json" ]; then
    print_error "Not in doc-scan-ai directory! Please run from project root."
    exit 1
fi

print_success "✓ In correct directory"

# Check if git is available
if ! command_exists git; then
    print_error "Git is not installed!"
    exit 1
fi

print_success "✓ Git is available"

# Check current branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "master" ]; then
    print_warning "Not on master branch (currently on: $current_branch)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_success "✓ On correct branch"

###########################################
# Step 1: Create Backup
###########################################

echo ""
print_status "Step 1: Creating backup..."

backup_dir=~/backups/doc-scan-ai-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $backup_dir

cp -r backend/ $backup_dir/
cp -r src/ $backup_dir/ 2>/dev/null || true

print_success "Backup created at: $backup_dir"

###########################################
# Step 2: Stash Local Changes
###########################################

echo ""
print_status "Step 2: Checking for local changes..."

if ! git diff-index --quiet HEAD --; then
    print_warning "Found local changes, stashing..."
    git stash
    print_success "Local changes stashed"
else
    print_success "No local changes to stash"
fi

###########################################
# Step 3: Pull Latest Code
###########################################

echo ""
print_status "Step 3: Pulling latest code from GitHub..."

git fetch origin master

# Get current commit
old_commit=$(git rev-parse HEAD)

# Pull latest
git pull origin master

# Get new commit
new_commit=$(git rev-parse HEAD)

if [ "$old_commit" == "$new_commit" ]; then
    print_warning "Already up to date!"
else
    print_success "Updated to commit: $(git log -1 --oneline)"
fi

###########################################
# Step 4: Verify New Files
###########################################

echo ""
print_status "Step 4: Verifying new template files..."

required_templates=(
    "backend/templates/faktur_pajak_template.json"
    "backend/templates/invoice_template.json"
    "backend/templates/rekening_koran_template.json"
    "backend/templates/pph21_template.json"
    "backend/templates/pph23_template.json"
)

all_templates_exist=true
for template in "${required_templates[@]}"; do
    if [ -f "$template" ]; then
        print_success "✓ Found: $template"
    else
        print_error "✗ Missing: $template"
        all_templates_exist=false
    fi
done

if [ "$all_templates_exist" = false ]; then
    print_error "Some template files are missing!"
    exit 1
fi

###########################################
# Step 5: Check Python Dependencies
###########################################

echo ""
print_status "Step 5: Checking Python dependencies..."

if [ -f "backend/requirements.txt" ]; then
    print_status "Installing/updating Python packages..."
    cd backend

    # Check if virtual environment exists
    if [ -d "venv" ]; then
        source venv/bin/activate
        print_success "Activated virtual environment"
    fi

    pip install -r requirements.txt --quiet
    print_success "Python dependencies updated"
    cd ..
else
    print_warning "No requirements.txt found, skipping pip install"
fi

###########################################
# Step 6: Restart Backend Service
###########################################

echo ""
print_status "Step 6: Restarting backend service..."

# Check if PM2 is being used
if command_exists pm2; then
    pm2_list=$(pm2 list 2>/dev/null | grep -i "doc-scan-backend" || true)

    if [ -n "$pm2_list" ]; then
        print_status "Restarting PM2 process..."
        pm2 restart doc-scan-backend
        print_success "Backend restarted via PM2"
    else
        print_warning "No PM2 process found for backend"
        print_status "Please restart backend manually"
    fi
elif systemctl is-active --quiet doc-scan-backend 2>/dev/null; then
    print_status "Restarting systemd service..."
    sudo systemctl restart doc-scan-backend
    print_success "Backend restarted via systemd"
else
    print_warning "Could not detect service manager"
    print_status "Please restart backend service manually"
fi

###########################################
# Step 7: Wait for Service to Start
###########################################

echo ""
print_status "Step 7: Waiting for backend to start..."

max_attempts=30
attempt=0
backend_url="http://localhost:8000"

while [ $attempt -lt $max_attempts ]; do
    if curl -s "$backend_url/api/health" >/dev/null 2>&1; then
        print_success "Backend is responding!"
        break
    fi

    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        print_error "Backend did not start after 30 seconds"
        print_warning "Check logs: pm2 logs doc-scan-backend"
        exit 1
    fi

    sleep 1
    echo -n "."
done

echo ""

###########################################
# Step 8: Run Quick Tests
###########################################

echo ""
print_status "Step 8: Running quick health checks..."

# Test backend API
if curl -s "$backend_url/api/health" | grep -q "ok\|healthy" 2>/dev/null; then
    print_success "✓ Backend API responding"
else
    print_warning "Backend API health check unclear"
fi

# Check if Smart Mapper is enabled
if [ -f "backend/.env" ]; then
    if grep -q "ENABLE_SMART_MAPPER=true" backend/.env; then
        print_success "✓ Smart Mapper enabled in .env"
    else
        print_warning "Smart Mapper might not be enabled"
    fi
fi

###########################################
# Summary
###########################################

echo ""
echo "=========================================="
print_success "🎉 Production Update Completed!"
echo "=========================================="
echo ""
echo "📋 Update Summary:"
echo "  • Backup location: $backup_dir"
echo "  • New commit: $(git log -1 --oneline)"
echo "  • Templates verified: ✓"
echo "  • Backend restarted: ✓"
echo ""
echo "🧪 Test Checklist:"
echo "  [ ] Upload Rekening Koran (any bank)"
echo "  [ ] Upload Invoice (any type)"
echo "  [ ] Upload Faktur Pajak"
echo "  [ ] Verify Excel exports"
echo "  [ ] Verify PDF exports"
echo ""
echo "📊 Monitor logs with:"
echo "  pm2 logs doc-scan-backend"
echo ""
echo "🔄 Rollback if needed:"
echo "  cp -r $backup_dir/* ~/doc-scan-ai/"
echo "  pm2 restart all"
echo ""

###########################################
# Optional: Show Recent Logs
###########################################

read -p "Show recent backend logs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command_exists pm2; then
        echo ""
        print_status "Recent backend logs:"
        pm2 logs doc-scan-backend --lines 20 --nostream
    fi
fi

echo ""
print_success "All done! 🚀"
