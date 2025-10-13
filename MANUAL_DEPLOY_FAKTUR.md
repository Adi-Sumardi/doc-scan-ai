# 🚀 Manual Deployment: Faktur Pajak Enhancement

## Update yang Dilakukan

### Backend (Faktur Pajak Exporter):
- ✅ Tambah Column 12: **Nilai Barang** (harga satuan per item, rata kiri)
- ✅ Tambah Column 13: **Total Nilai Barang** (qty × unit_price)
- ✅ Menampilkan SEMUA harga item dalam format numbered list
- ✅ Helper functions baru: `_calculate_nilai_barang_satuan()`, `_parse_price()`

### Frontend (DocumentContext):
- ✅ Fix ZIP upload navigation - add batch to state if not exists
- ✅ Mencegah error "Batch not found" saat navigasi dari ZIP upload

---

## 📋 Langkah Manual Deployment via Termius

### Step 1: Login ke VPS
```bash
ssh docScan@docscan.adilabs.id
```

### Step 2: Masuk ke Directory Aplikasi
```bash
cd /var/www/docscan
```

### Step 3: Pull Latest Code dari GitHub
```bash
git pull origin master
```
Output yang diharapkan:
```
remote: Enumerating objects: 5, done.
remote: Counting objects: 100% (5/5), done.
remote: Compressing objects: 100% (3/3), done.
remote: Total 3 (delta 2), reused 3 (delta 2), pack-reused 0
Unpacking objects: 100% (3/3), done.
From https://github.com/Adi-Sumardi/doc-scan-ai
   b874b0e..75981dc  master     -> origin/master
Updating b874b0e..75981dc
Fast-forward
 backend/exporters/faktur_pajak_exporter.py | 228 ++++++++++++++++++++++-------
 src/context/DocumentContext.tsx            |  13 +-
 2 files changed, 156 insertions(+), 72 deletions(-)
```

### Step 4: Build Frontend (PENTING!)
```bash
npm run build
```
⚠️ **WAJIB dilakukan** karena ada perubahan di `DocumentContext.tsx`

Output yang diharapkan:
```
> doc-scan-ai@0.0.0 build
> tsc -b && vite build

vite v5.x.x building for production...
✓ xxxx modules transformed.
dist/index.html                   x.xx kB │ gzip: x.xx kB
dist/assets/index-xxxxxxxx.js    xxx.xx kB │ gzip: xx.xx kB
dist/assets/index-xxxxxxxx.css    xx.xx kB │ gzip: x.xx kB
✓ built in x.xxs
```

### Step 5: Restart Backend Service
```bash
sudo systemctl restart docscan-backend
```

### Step 6: Check Service Status (Optional)
```bash
sudo systemctl status docscan-backend
```
Output yang diharapkan:
```
● docscan-backend.service - Doc Scan AI Backend
     Loaded: loaded (/etc/systemd/system/docscan-backend.service; enabled)
     Active: active (running) since Mon 2025-10-13 21:37:09 WIB
```

Jika statusnya **active (running)** dengan warna hijau, berarti berhasil! ✅

### Step 6: Test API (Optional)
```bash
curl -s http://127.0.0.1:8000/health
```

---

## 🎯 Shortcut - One Command Deployment

Jika ingin cepat, jalankan semua sekaligus:

```bash
cd /var/www/docscan && git pull origin master && npm run build && sudo systemctl restart docscan-backend && sudo systemctl status docscan-backend
```

⚠️ **PENTING**: Perintah di atas sudah termasuk `npm run build` untuk build frontend!

---

## 🔍 Troubleshooting

### Jika git pull gagal (authentication error):
```bash
# Cek remote URL
git remote -v

# Pastikan menggunakan HTTPS (bukan SSH)
git remote set-url origin https://github.com/Adi-Sumardi/doc-scan-ai.git
```

### Jika service gagal start:
```bash
# Lihat error log
sudo journalctl -u docscan-backend -n 50 --no-pager

# Atau lihat real-time logs
sudo journalctl -u docscan-backend -f
```

### Jika masih error, restart manual:
```bash
# Stop service
sudo systemctl stop docscan-backend

# Start service
sudo systemctl start docscan-backend

# Check status
sudo systemctl status docscan-backend
```

---

## ✅ Cara Test Fitur Baru

1. Login ke aplikasi: https://docscan.adilabs.id
2. Upload dokumen Faktur Pajak (atau pilih dokumen existing)
3. Setelah processing selesai, klik **Export Excel**
4. Buka file Excel yang di-download
5. Cek kolom baru:
   - **Column L (12)**: Nilai Barang - harga satuan per item (rata kiri)
   - **Column M (13)**: Total Nilai Barang - grand total

### Format Expected:

**Jika 1 item:**
- Column L: `Rp 5.000.000`
- Column M: `Rp 5.000.000`

**Jika multiple items:**
- Column L:
  ```
  1. Rp 5.000.000
  2. Rp 3.000.000
  3. Rp 7.500.000
  ```
- Column M: `Rp 15.500.000` (total semua)

---

## 📝 File yang Berubah

1. `backend/exporters/faktur_pajak_exporter.py` - Main changes
2. `src/context/DocumentContext.tsx` - Fix ZIP upload navigation

---

## 🔗 Commit Reference

Commit: `75981dc`
Message: "feat: Enhance Faktur Pajak Excel export with separate unit price and total columns"

---

## 📞 Support

Jika ada masalah:
1. Check logs: `sudo journalctl -u docscan-backend -f`
2. Check service: `sudo systemctl status docscan-backend`
3. Restart service: `sudo systemctl restart docscan-backend`
