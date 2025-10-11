# Deploy Data Loading Fix to Production

## Issue Fixed
Batch IDs not displaying in Dashboard, Documents, and History pages due to race condition between authentication and data loading.

## Root Cause
DocumentContext was loading data before AuthContext finished initializing the token, causing 401 errors and empty data arrays.

## Fix Applied
- DocumentContext now waits for authentication to complete before loading data
- Improved error handling to prevent empty arrays on auth errors
- Added detailed logging for debugging

## Deployment Steps

### Step 1: Connect to Production Server (Termius)
```bash
ssh docScan@docscan.adilabs.id
```

### Step 2: Backup Current Production
```bash
cd /var/www/docscan
sudo -u docScan cp -r dist dist.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 3: Pull Latest Changes
```bash
sudo -u docScan git fetch origin
sudo -u docScan git reset --hard origin/master
sudo -u docScan git pull origin master
```

### Step 4: Build Frontend
```bash
cd /var/www/docscan
sudo -u docScan npm install
sudo -u docScan npm run build
```

### Step 5: Restart Services
```bash
# Restart backend
sudo systemctl restart docscan-backend

# Restart nginx
sudo systemctl restart nginx

# Verify services are running
sudo systemctl status docscan-backend
sudo systemctl status nginx
```

### Step 6: Verify Fix
1. Open browser: https://docscan.adilabs.id
2. Open DevTools Console (F12)
3. Login and check for:
   - `🔄 Auth ready, loading data...` message
   - `✅ Loaded X batches` message
   - `✅ Loaded X results` message
4. Navigate to Dashboard, Documents, and History pages
5. Verify batch IDs are now displaying

### Step 7: Check Logs (if issues persist)
```bash
# Backend logs
sudo journalctl -u docscan-backend -n 50 --no-pager

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log
```

## Quick Copy-Paste Commands for Termius

### Complete Deployment
```bash
# Navigate to project
cd /var/www/docscan

# Backup
sudo -u docScan cp -r dist dist.backup.$(date +%Y%m%d_%H%M%S)

# Pull latest
sudo -u docScan git fetch origin && sudo -u docScan git reset --hard origin/master && sudo -u docScan git pull origin master

# Build
sudo -u docScan npm install && sudo -u docScan npm run build

# Restart services
sudo systemctl restart docscan-backend && sudo systemctl restart nginx

# Check status
echo "=== Backend Status ===" && sudo systemctl status docscan-backend --no-pager && echo "" && echo "=== Nginx Status ===" && sudo systemctl status nginx --no-pager
```

### Verify Data Loading
Open browser console and check for these log messages:
```
🔄 Auth ready, loading data...
[API Request] GET /api/batches
[API Response] 200 /api/batches
✅ Loaded 37 batches
[API Request] GET /api/results
[API Response] 200 /api/results
✅ Loaded X results
```

## Rollback (if needed)
```bash
cd /var/www/docscan
# Find backup
ls -la dist.backup.*
# Restore (replace with actual backup timestamp)
sudo -u docScan rm -rf dist
sudo -u docScan cp -r dist.backup.YYYYMMDD_HHMMSS dist
sudo systemctl restart nginx
```

## Technical Details

### What Changed
**File: `src/context/DocumentContext.tsx`**

Before:
```tsx
React.useEffect(() => {
  refreshAllData();  // Called immediately, before auth ready!
}, []);
```

After:
```tsx
const { isLoading: authLoading, isAuthenticated } = useAuth();

React.useEffect(() => {
  // Wait for auth to finish loading
  if (!authLoading && isAuthenticated) {
    console.log('🔄 Auth ready, loading data...');
    refreshAllData();
  }
}, [authLoading, isAuthenticated]);
```

### Why This Fixes It
1. **Before**: Data fetch happens immediately → no token → 401 error → empty arrays
2. **After**: Data fetch waits for auth → token available → 200 success → data loads

## Success Indicators
- ✅ Dashboard shows batch statistics
- ✅ Recent batches section populated
- ✅ Documents page shows all scanned documents
- ✅ History page shows batch list
- ✅ Console shows successful data loading logs
- ✅ No 401 errors in browser network tab
