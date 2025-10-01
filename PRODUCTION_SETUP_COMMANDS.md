# 🎯 Quick Production Setup Commands

Jalankan command ini **DI SERVER PRODUCTION** untuk setup lengkap environment.

---

## 📥 **STEP 1: Pull Latest Code**

```bash
cd /var/www/docscan
git pull origin master
```

**Expected output:**
```
Updating 87eeb87..e22f767
Fast-forward
 GOOGLE_CLOUD_SETUP.md      | 283 +++++++++++++++++++
 setup_production_env.sh    | 171 ++++++++++++
 2 files changed, 454 insertions(+)
```

---

## 🔧 **STEP 2: Run Setup Script**

```bash
cd /var/www/docscan
bash setup_production_env.sh
```

**Script akan:**
- ✅ Backup `.env` lama (jika ada)
- ✅ Create `.env` baru dengan Google Cloud config
- ✅ Set permissions yang benar
- ✅ Tampilkan next steps

---

## 🔐 **STEP 3: Generate SECRET_KEY**

```bash
# Generate new secure key
NEW_KEY=$(openssl rand -hex 32)

# Update .env file
sed -i "s/REPLACE_THIS_WITH_SECURE_KEY_GENERATED_BY_OPENSSL/$NEW_KEY/g" /var/www/docscan/backend/.env

# Verify key updated
grep "^SECRET_KEY=" /var/www/docscan/backend/.env
```

**Expected output:**
```
SECRET_KEY=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

---

## 📤 **STEP 4: Upload Google Cloud Credentials**

### **Option A: From Local Machine (SCP)**

**Run this on YOUR LOCAL MACHINE** (not on server):

```bash
# Copy file to production
scp /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/automation-ai-pajak-c560daf6c6d1.json \
    docScan@YOUR_SERVER_IP:/var/www/docscan/backend/config/
```

### **Option B: Manual Copy-Paste**

**On local machine:**
```bash
cat /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/automation-ai-pajak-c560daf6c6d1.json
```

**Copy output, then on production server:**
```bash
mkdir -p /var/www/docscan/backend/config
nano /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json
# Paste content, save (Ctrl+O, Enter, Ctrl+X)
```

---

## ✅ **STEP 5: Set Credentials Permissions**

```bash
cd /var/www/docscan/backend/config
chmod 400 automation-ai-pajak-c560daf6c6d1.json
chown docScan:docScan automation-ai-pajak-c560daf6c6d1.json

# Verify
ls -lah automation-ai-pajak-c560daf6c6d1.json
```

**Expected:**
```
-r-------- 1 docScan docScan 2.3K Oct  1 XX:XX automation-ai-pajak-c560daf6c6d1.json
```

---

## 📦 **STEP 6: Install Dependencies**

```bash
cd /var/www/docscan
source venv/bin/activate
pip install -r backend/requirements.txt
```

**Key packages to verify:**
```bash
pip list | grep -E "slowapi|google-cloud-documentai|google-cloud-storage|google-auth"
```

**Expected:**
```
google-auth                 2.23.0
google-cloud-documentai     2.26.0
google-cloud-storage        2.10.0
slowapi                     0.1.9
```

---

## 🧪 **STEP 7: Test Configuration**

```bash
cd /var/www/docscan/backend
source ../venv/bin/activate

# Test .env loads
python3 << 'EOF'
from dotenv import load_dotenv
import os

load_dotenv()

print("=== Environment Configuration ===")
print(f"✅ Database: {os.getenv('DATABASE_URL')[:50]}...")
print(f"✅ Google Project: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"✅ Processor ID: {os.getenv('GOOGLE_PROCESSOR_ID')}")
print(f"✅ Cloud OCR: {os.getenv('ENABLE_CLOUD_OCR')}")
print(f"✅ Credentials: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
print(f"✅ SECRET_KEY: {os.getenv('SECRET_KEY')[:20]}...")

# Check credentials file exists
creds_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if os.path.exists(creds_file):
    print(f"✅ Credentials file found: {creds_file}")
else:
    print(f"❌ Credentials file NOT found: {creds_file}")
EOF
```

---

## 🤖 **STEP 8: Test Google Cloud Connection**

```bash
cd /var/www/docscan/backend
source ../venv/bin/activate

python3 << 'EOF'
import os
import json
from google.cloud import documentai_v1
from dotenv import load_dotenv

load_dotenv()

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

try:
    # Initialize client
    client = documentai_v1.DocumentProcessorServiceClient()
    print("✅ Google Cloud Document AI client initialized!")
    
    # Load credentials
    with open(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')) as f:
        creds = json.load(f)
        print(f"✅ Project ID: {creds['project_id']}")
        print(f"✅ Client Email: {creds['client_email']}")
    
    print("\n🎉 Google Cloud Document AI is READY!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n⚠️  Check:")
    print("  1. Credentials file path in .env")
    print("  2. Credentials file permissions")
    print("  3. JSON file format")
EOF
```

---

## 🔄 **STEP 9: Restart Backend**

```bash
# Stop existing process
pkill -f "uvicorn main:app"
sleep 2

# Start new process
cd /var/www/docscan/backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Wait for startup
sleep 5

# Check process
ps aux | grep "uvicorn main:app" | grep -v grep
```

---

## ✨ **STEP 10: Verify Backend Running**

```bash
# Check health endpoint
curl -s http://localhost:8000/api/health | python3 -m json.tool

# Check API docs (if enabled)
curl -s http://localhost:8000/docs | head -20

# Check logs
tail -50 /var/www/docscan/backend/backend.log
```

**Expected health response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-01T...",
  "version": "1.0.0"
}
```

---

## 🎯 **COMPLETE SETUP IN ONE GO**

**Run all commands sequentially:**

```bash
#!/bin/bash
# Complete production setup

cd /var/www/docscan

# 1. Pull code
echo "📥 Pulling latest code..."
git pull origin master

# 2. Run setup script
echo "🔧 Setting up environment..."
bash setup_production_env.sh

# 3. Generate SECRET_KEY
echo "🔐 Generating SECRET_KEY..."
NEW_KEY=$(openssl rand -hex 32)
sed -i "s/REPLACE_THIS_WITH_SECURE_KEY_GENERATED_BY_OPENSSL/$NEW_KEY/g" backend/.env

echo ""
echo "⚠️  MANUAL STEP REQUIRED:"
echo "Upload Google Cloud credentials to:"
echo "  /var/www/docscan/backend/config/automation-ai-pajak-c560daf6c6d1.json"
echo ""
echo "Use SCP from local machine:"
echo "  scp /Users/yapi/Adi/App-Dev/doc-scan-ai/backend/config/automation-ai-pajak-c560daf6c6d1.json \\"
echo "      docScan@YOUR_SERVER_IP:/var/www/docscan/backend/config/"
echo ""
read -p "Press Enter after uploading credentials file..."

# 4. Set permissions
echo "🔒 Setting credentials permissions..."
chmod 400 backend/config/automation-ai-pajak-c560daf6c6d1.json
chown docScan:docScan backend/config/automation-ai-pajak-c560daf6c6d1.json

# 5. Install dependencies
echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r backend/requirements.txt

# 6. Test configuration
echo "🧪 Testing configuration..."
cd backend
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ Config loaded')"

# 7. Restart backend
echo "🔄 Restarting backend..."
pkill -f "uvicorn main:app"
sleep 2
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
sleep 5

# 8. Verify
echo "✅ Verifying backend..."
curl -s http://localhost:8000/api/health

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Check logs: tail -f /var/www/docscan/backend/backend.log"
```

---

## 📋 **Quick Verification Checklist**

```bash
# Run this to verify everything
cd /var/www/docscan

echo "1. .env file:"
ls -lah backend/.env

echo -e "\n2. Credentials file:"
ls -lah backend/config/automation-ai-pajak-c560daf6c6d1.json

echo -e "\n3. Backend process:"
ps aux | grep "uvicorn" | grep -v grep

echo -e "\n4. Health check:"
curl -s http://localhost:8000/api/health

echo -e "\n5. Recent logs:"
tail -20 backend/backend.log
```

---

## 🆘 **Troubleshooting**

### If backend won't start:
```bash
cd /var/www/docscan/backend
source ../venv/bin/activate
python3 -c "import main"  # Check for import errors
```

### If Google Cloud fails:
```bash
python3 -c "import google.cloud.documentai_v1; print('✅ Module installed')"
ls -lah backend/config/*.json
```

### View detailed logs:
```bash
tail -100 /var/www/docscan/backend/backend.log
tail -50 /var/www/docscan/backend/logs/audit.log
```

---

**🎯 After completion, backend should be running with:**
- ✅ New production .env configuration
- ✅ Google Cloud Document AI enabled
- ✅ Secure SECRET_KEY
- ✅ All dependencies installed
- ✅ Service running on port 8000
