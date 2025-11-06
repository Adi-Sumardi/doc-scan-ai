# Demo Files untuk PPN Reconciliation

## 📋 Overview

File-file demo ini dibuat untuk testing fitur PPN Reconciliation dengan data yang realistic dan memiliki match rate yang tinggi.

## 📊 File yang Tersedia

### 1. Demo_Faktur_Pajak.xlsx
- **Total Rows**: 40
- **Struktur**:
  - 20 rows Point A (PT DEMO COMPANY sebagai penjual)
  - 20 rows Point B (PT DEMO COMPANY sebagai pembeli)
- **Columns**: Nomor Faktur, Tanggal Faktur, Masa Pajak, Tahun Pajak, Status, NPWP Penjual, Nama Penjual, NPWP Pembeli, Nama Pembeli, DPP, PPN, Total
- **Period**: Januari - Maret 2024

### 2. Demo_Bukti_Potong.xlsx
- **Total Rows**: 40
- **Matching Logic**:
  - 30 rows yang NPWP Pemotongnya match dengan NPWP Pembeli di Point A
  - 10 rows dengan NPWP random (tidak match)
- **Expected Match Rate**: ~75% (15/20 dari Point A)
- **Columns**: Nomor Bukti Potong, Tanggal, NPWP Pemotong, Nama Pemotong, NPWP Yang Dipotong, Nama Yang Dipotong, Jenis Penghasilan, Jumlah Bruto, Tarif, PPh Dipotong
- **Jenis Penghasilan**: Jasa Teknik, Jasa Manajemen, Jasa Konsultan, Sewa Gedung, Jasa Konstruksi

### 3. Demo_Rekening_Koran.xlsx
- **Total Rows**: 40
- **Matching Logic**:
  - 25 rows payment out (debet) yang match dengan Point B berdasarkan tanggal dan total amount
  - 15 rows transaksi random (tidak match)
- **Expected Match Rate**: ~62.5% (12-13/20 dari Point B)
- **Columns**: Tanggal, Keterangan, Cabang, Debet, Kredit, Saldo, Referensi
- **Starting Balance**: Rp 100,000,000

## 🎯 Cara Menggunakan

### Step 1: Buat Project Baru
1. Buka aplikasi di `http://localhost:5173/ppn-reconciliation`
2. Klik "Create New Project"
3. Isi form:
   - **Project Name**: Demo PPN Reconciliation
   - **Period**: 01/01/2024 - 31/03/2024
   - **Company NPWP**: `01.234.567.8-901.000` ⚠️ **PENTING: Gunakan NPWP ini!**

### Step 2: Upload File Demo
1. Pada halaman project detail, upload ketiga file:
   - **Point A & B**: Upload `Demo_Faktur_Pajak.xlsx`
   - **Point C**: Upload `Demo_Bukti_Potong.xlsx`
   - **Point E**: Upload `Demo_Rekening_Koran.xlsx`

### Step 3: Run Reconciliation
1. Klik tombol "Run Reconciliation"
2. Tunggu proses selesai

### Step 4: Review Results
Setelah reconciliation selesai, Anda akan melihat:

#### Expected Summary:
- **Point A vs C**:
  - Total Point A: 20
  - Total Point C: 30 (lebih banyak karena ada duplikat)
  - Matched: ~15 (75% match rate)
  - Unmatched A: ~5
  - Unmatched C: ~15

- **Point B vs E**:
  - Total Point B: 20
  - Total Point E: 25 (hanya payment out)
  - Matched: ~12-13 (62.5% match rate)
  - Unmatched B: ~7-8
  - Unmatched E: ~12-13

### Step 5: Export Excel
1. Klik tombol "Export Excel"
2. File Excel akan didownload dengan 4 sheets:
   - **Sheet 1: Summary** - Ringkasan project dan statistik
   - **Sheet 2: Point A vs C - Matched** - Data yang match antara Faktur Keluaran dan Bukti Potong
   - **Sheet 3: Point B vs E - Matched** - Data yang match antara Faktur Masukan dan Rekening Koran
   - **Sheet 4: Unmatched Items** - Semua data yang tidak match, dipisah per point

## 🔍 Matching Logic

### Point A vs Point C
Match berdasarkan **NPWP Pembeli**:
- NPWP Pembeli di Faktur Pajak (Point A) = NPWP Pemotong di Bukti Potong (Point C)
- Contoh: `02.100.200.1-300.000` di Point A akan match dengan Bukti Potong yang memiliki NPWP Pemotong yang sama

### Point B vs Point E
Match berdasarkan **Tanggal dan Amount**:
- Tanggal transaksi di Faktur Pajak (Point B) = Tanggal di Rekening Koran (Point E)
- Total (DPP + PPN) di Point B = Jumlah Debet di Point E
- Keterangan di Rekening Koran mencantumkan nama penjual dari Point B

## 📝 Notes

- **Company NPWP**: Sangat penting untuk menggunakan NPWP `01.234.567.8-901.000` agar splitting Point A/B berfungsi dengan benar
- **Date Format**: Semua tanggal menggunakan format DD/MM/YYYY
- **Currency Format**: Semua nilai mata uang dalam Rupiah (IDR)
- **Match Rate**: Match rate tidak akan 100% karena dirancang untuk menunjukkan skenario realistic dimana ada beberapa transaksi yang tidak match

## 🔄 Generate Ulang File Demo

Jika Anda ingin generate ulang file demo dengan data berbeda, jalankan:

```bash
python generate_demo_files.py
```

Script ini akan membuat file baru dengan data random namun tetap menjaga logic matching yang sama.

## ⚠️ Troubleshooting

### Match Rate Terlalu Rendah
- Pastikan Company NPWP yang digunakan adalah `01.234.567.8-901.000`
- Cek apakah file yang di-upload adalah file yang benar

### File Tidak Bisa Di-upload
- Pastikan format file adalah `.xlsx` atau `.xls`
- Cek ukuran file tidak terlalu besar
- Pastikan struktur columns sesuai dengan yang diharapkan

### Export Excel Hanya Menunjukkan 2 Sheets
- Issue ini sudah diperbaiki
- Pastikan backend sudah di-reload setelah fix
- Sheet 3 dan 4 sekarang akan selalu muncul, meskipun data kosong akan menampilkan "No data" message
