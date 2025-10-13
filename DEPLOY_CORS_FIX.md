# 🚀 Manual Deployment: CORS Fix untuk ZIP Upload

## Problem yang Diperbaiki
❌ **Error CORS di Production:**
```
Access to fetch at 'http://localhost:8000/api/upload-zip' from origin 'https://docscan.adilabs.id'
has been blocked by CORS policy: Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Root Cause:**
- ZIP upload hardcoded ke `http://localhost:8000/api/upload-zip`
- Frontend mencoba connect ke localhost padahal di production

**Fix:**
- ✅ Tambah helper function `getApiBaseUrl()` untuk auto-detect environment
- ✅ Production: gunakan relative path
- ✅ Development: gunakan `http://localhost:8000`

---

## 📋 Manual Deployment via Termius

### Step 1: Login ke VPS
```bash
ssh docScan@docscan.adilabs.id
```

### Step 2: Masuk ke Directory Aplikasi
```bash
cd /var/www/docscan
```

### Step 3: Check Current Status
```bash
git status
git log -1 --oneline
```

### Step 4: Pull Latest Code dari GitHub
```bash
git pull origin master
```

**Expected Output:**
```
Updating 3c9b322..3022bc2
Fast-forward
 src/pages/Upload.tsx | 28 +++++++++++++++++++++++++++-
 1 file changed, 27 insertions(+), 1 deletion(-)
```

### Step 5: Build Frontend (WAJIB!)
```bash
npm run build
```

**Expected Output:**
```
> doc-scan-ai@1.0.0 build
> tsc -b && vite build

vite v7.1.5 building for production...
transforming...
✓ 1552 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.63 kB │ gzip:   0.38 kB
dist/assets/index-DAudKd9j.css   47.67 kB │ gzip:   8.10 kB
dist/assets/index-Bw4oNizK.js   474.48 kB │ gzip: 133.35 kB
✓ built in 1.96s
```

⚠️ **PENTING:** Perhatikan hash file JavaScript berubah dari `CNrv0FP7` ke `Bw4oNizK`

### Step 6: Restart Backend Service
```bash
sudo systemctl restart docscan-backend
```

### Step 7: Check Service Status
```bash
sudo systemctl status docscan-backend
```

**Expected Output:**
```
● docscan-backend.service - Doc Scan AI Backend
     Loaded: loaded (/etc/systemd/system/docscan-backend.service; enabled)
     Active: active (running) since Mon 2025-10-13 21:46:57 WIB
```

Status harus **active (running)** dengan warna hijau ✅

### Step 8: Test API (Optional)
```bash
curl -s http://127.0.0.1:8000/api/health | head -20
```

---

## 🎯 Quick One-Command Deployment

Jika ingin cepat, copy-paste command ini:

```bash
cd /var/www/docscan && git pull origin master && npm run build && sudo systemctl restart docscan-backend && sudo systemctl status docscan-backend
```

---

## ✅ Cara Test Fix

### Test 1: Check File Hash di Browser
1. Buka https://docscan.adilabs.id
2. Tekan **Ctrl+Shift+C** (atau Cmd+Option+C di Mac) untuk buka DevTools
3. Klik tab **Network**
4. Reload halaman (F5 atau Cmd+R)
5. Cari file JavaScript: `index-Bw4oNizK.js` ✅
6. Jika masih `index-CNrv0FP7.js` = belum update, clear cache dan reload

### Test 2: Upload ZIP File
1. Login ke aplikasi: https://docscan.adilabs.id
2. Pilih tab **"📦 ZIP Upload (Bulk)"**
3. Select document type (misalnya: Faktur Pajak)
4. Drag & drop ZIP file atau klik Browse
5. Klik **"Upload ZIP"**

**Expected Result:**
- ✅ Upload progress muncul
- ✅ Tidak ada CORS error di console
- ✅ Toast notification: "ZIP uploaded! Processing X files..."
- ✅ Redirect ke ScanResults page

**Jika masih error:**
- Clear browser cache (Ctrl+Shift+Delete)
- Hard reload (Ctrl+Shift+R atau Cmd+Shift+R)
- Check DevTools Console untuk error messages

---

## 🔍 Troubleshooting

### Problem 1: Git Pull Error
```bash
# Cek remote URL
git remote -v

# Set ke HTTPS jika belum
git remote set-url origin https://github.com/Adi-Sumardi/doc-scan-ai.git

# Try pull lagi
git pull origin master
```

### Problem 2: npm run build Error
```bash
# Check Node.js version
node -v
npm -v

# Clean install dependencies
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Problem 3: Service Gagal Start
```bash
# Lihat error logs
sudo journalctl -u docscan-backend -n 50 --no-pager

# Atau real-time logs
sudo journalctl -u docscan-backend -f

# Force restart
sudo systemctl stop docscan-backend
sudo systemctl start docscan-backend
sudo systemctl status docscan-backend
```

### Problem 4: Browser Masih Cache File Lama
```bash
# Di browser:
# 1. Open DevTools (F12)
# 2. Right-click pada Reload button
# 3. Pilih "Empty Cache and Hard Reload"

# Atau:
# Ctrl+Shift+Delete → Clear cache → Reload
```

### Problem 5: 502 Bad Gateway Error
```bash
# Check if backend is running
sudo systemctl status docscan-backend

# Check backend logs
sudo journalctl -u docscan-backend -f

# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Restart both
sudo systemctl restart docscan-backend
sudo systemctl restart nginx
```

---

## 📝 Files yang Berubah

### Commit: `3022bc2`
**File:** `src/pages/Upload.tsx`

**Changes:**
```typescript
// BEFORE (Hardcoded):
const response = await fetch('http://localhost:8000/api/upload-zip', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

// AFTER (Dynamic):
const apiBaseUrl = getApiBaseUrl();
const uploadUrl = `${apiBaseUrl}/api/upload-zip`;

const response = await fetch(uploadUrl, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

**New Helper Function:**
```typescript
const getApiBaseUrl = (): string => {
  // Production: docscan.adilabs.id → empty string (relative path)
  // Development: localhost → http://localhost:8000
  // Environment variable: VITE_API_URL → use that
};
```

---

## 🔗 Related Commits

1. **75981dc** - feat: Enhance Faktur Pajak Excel export (13 columns)
2. **3c9b322** - docs: Add deployment guides
3. **3022bc2** - fix: Use dynamic API URL for ZIP upload (CORS fix) ⭐ **← Current**

---

## 📞 Verification Commands

### Check Current Commit
```bash
git log -1 --oneline
# Expected: 3022bc2 fix: Use dynamic API URL for ZIP upload to support production environment
```

### Check File Content
```bash
grep -A 5 "getApiBaseUrl" src/pages/Upload.tsx
# Should show the new helper function
```

### Check Built Files
```bash
ls -lh dist/assets/index-*.js
# Should show: index-Bw4oNizK.js (new hash)
```

### Check Service Status
```bash
sudo systemctl is-active docscan-backend
# Should return: active
```

---

## ✅ Success Indicators

After deployment, you should see:
- ✅ Git commit: `3022bc2`
- ✅ Built file: `dist/assets/index-Bw4oNizK.js`
- ✅ Service status: `active (running)`
- ✅ No CORS errors in browser console
- ✅ ZIP upload works without errors

---

## 🚀 Post-Deployment Test

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Open** https://docscan.adilabs.id
3. **Login** with your credentials
4. **Go to Upload page** → ZIP Upload tab
5. **Upload a ZIP file** with multiple documents
6. **Verify** no CORS errors in console (F12)
7. **Check** redirect to ScanResults page
8. **Confirm** all files are processing

If all steps pass → **Deployment successful!** 🎉
