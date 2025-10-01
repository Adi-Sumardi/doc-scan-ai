# 🔐 Google Cloud Credentials Setup Guide

## 📋 Overview

Guide untuk upload Google Cloud service account credentials ke production server.

## 📁 File Information

**File Name**: `automation-ai-pajak-c560daf6c6d1.json`  
**Source**: Local machine `/Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/`  
**Destination**: Production server `/var/www/docscan/backend/config/`

## 🚀 Upload Methods

### Method 1: Using SCP (Recommended)

```bash
# From your LOCAL machine (NOT on production server)
cd /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config

# Upload to production server
scp automation-ai-pajak-c560daf6c6d1.json docScan@YOUR_SERVER_IP:/var/www/docscan/backend/config/

# Or if using custom SSH port:
scp -P YOUR_SSH_PORT automation-ai-pajak-c560daf6c6d1.json docScan@YOUR_SERVER_IP:/var/www/docscan/backend/config/
```

### Method 2: Using SFTP

```bash
# From your LOCAL machine
sftp docScan@YOUR_SERVER_IP

# Navigate to config directory
cd /var/www/docscan/backend/config

# Upload file
put /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Exit SFTP
exit
```

### Method 3: Copy-Paste via nano/vi (If no direct file transfer)

```bash
# On LOCAL machine - Display file content
cat /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Copy the entire JSON content (Cmd+C)

# On PRODUCTION server - Create file
mkdir -p /var/www/docscan/backend/config
nano /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Paste content (Cmd+V or Right-click paste)
# Save: Ctrl+O, Enter, Ctrl+X
```

### Method 4: Using rsync (Advanced)

```bash
# From LOCAL machine
rsync -avz --progress \
  /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/automation-ai-pajak-c560daf6c6d1.json \
  docScan@YOUR_SERVER_IP:/var/www/docscan/backend/config/
```

## ✅ Verification Steps

After upload, verify on **PRODUCTION SERVER**:

```bash
# 1. Check file exists
ls -lah /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Expected output:
# -rw-r--r-- 1 docScan docScan 2.3K Oct 1 XX:XX automation-ai-pajak-c560daf6c6d1.json

# 2. Verify JSON format
head -5 /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json

# Should show JSON structure like:
# {
#   "type": "service_account",
#   "project_id": "automation-ai-pajak",
#   ...
# }

# 3. Test Google Cloud authentication
cd /var/www/docscan/backend
source ../venv/bin/activate

python3 << 'PYEOF'
import os
import json
from google.cloud import documentai_v1

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json'

try:
    # Initialize client
    client = documentai_v1.DocumentProcessorServiceClient()
    print("✅ Google Cloud Document AI client initialized successfully!")
    
    # Verify credentials file
    creds_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
    with open(creds_path) as f:
        creds = json.load(f)
        print(f"✅ Project ID: {creds.get('project_id')}")
        print(f"✅ Client Email: {creds.get('client_email')}")
    
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF
```

## 🔒 Security Best Practices

### 1. Set Proper Permissions

```bash
# On production server
cd /var/www/docscan/backend/config

# Set restrictive permissions (owner read-only)
chmod 400 automation-ai-pajak-c560daf6c6d1.json

# Set owner
chown docScan:docScan automation-ai-pajak-c560daf6c6d1.json

# Verify
ls -lah automation-ai-pajak-c560daf6c6d1.json
# Should show: -r-------- 1 docScan docScan
```

### 2. Verify .gitignore Protection

```bash
# Make sure credentials are NOT tracked by git
cd /var/www/docscan
git status

# Should NOT show:
# backend/config/automation-ai-pajak-c560daf6c6d1.json
```

### 3. Environment Variable Check

```bash
# Test .env file loads credentials path correctly
cd /var/www/docscan/backend
source ../venv/bin/activate

python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
print(f'Credentials path: {creds_path}')
print(f'File exists: {os.path.exists(creds_path)}')
"
```

## 🐛 Troubleshooting

### Issue 1: Permission Denied

```bash
# Solution: Fix permissions
sudo chown docScan:docScan /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json
chmod 400 /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json
```

### Issue 2: File Not Found Error

```bash
# Check file path in .env
cat /var/www/docscan/backend/.env | grep GOOGLE_APPLICATION_CREDENTIALS

# Verify actual file location
find /var/www/docscan -name "*.json" 2>/dev/null
```

### Issue 3: Invalid JSON Format

```bash
# Validate JSON syntax
python3 -c "import json; json.load(open('/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json'))"

# Should print nothing if valid, or error if invalid
```

### Issue 4: Google Cloud Authentication Error

```bash
# Test with explicit credentials
python3 << 'EOF'
from google.oauth2 import service_account
credentials = service_account.Credentials.from_service_account_file(
    '/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json'
)
print(f"✅ Project: {credentials.project_id}")
EOF
```

## 📝 Checklist

After uploading credentials file:

- [ ] File exists at `/var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json`
- [ ] File size is reasonable (2-3KB typical for service account JSON)
- [ ] JSON format is valid
- [ ] File permissions are `400` (read-only for owner)
- [ ] Owner is `docScan:docScan`
- [ ] Not tracked by git
- [ ] .env file has correct GOOGLE_APPLICATION_CREDENTIALS path
- [ ] Python can load credentials successfully
- [ ] Google Cloud client initializes without errors

## 🎯 Next Steps After Upload

1. **Update .env with SECRET_KEY** (see setup_production_env.sh output)
2. **Install/update dependencies**: `pip install -r requirements.txt`
3. **Test configuration loading**
4. **Restart backend service**
5. **Test OCR with Google Document AI**

## 📞 Support

If authentication fails:
1. Verify service account has Document AI API enabled
2. Check IAM permissions in Google Cloud Console
3. Ensure project ID matches: `automation-ai-pajak`
4. Verify processor ID is correct: `831a22639bf6ff6f`

---

**🔒 Remember: NEVER commit service account JSON files to git!**
