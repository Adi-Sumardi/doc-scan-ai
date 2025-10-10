# 📄 Preview Output PDF Bukti Potong PPh 23 & PPh 21

## ✨ Fitur Baru: PDF Export dengan Layout Profesional

Template PDF yang baru **BUKAN lagi dalam bentuk tabel**, melainkan **dokumen terstruktur** yang rapi dan profesional seperti bukti potong resmi.

---

## 🎨 Tampilan PDF PPh 23

### **Header (Centered)**
```
═══════════════════════════════════════════════════
        BUKTI PEMOTONGAN PPh PASAL 23
    INCOME TAX ARTICLE 23 WITHHOLDING CERTIFICATE
═══════════════════════════════════════════════════
```

### **📄 INFORMASI DOKUMEN** *(Section Header Biru)*
```
Nomor Bukti Potong:
     1-23/PPh-23/2024

Masa Pajak:
     Januari 2024

Tanggal Pemotongan:
     15-01-2024

Sifat Pemotongan:
     Final

Status Bukti Pemotongan:
     Normal
```

### **👤 IDENTITAS PENERIMA PENGHASILAN** *(Section Header Biru)*
```
Nama:
     PT MAJU JAYA SENTOSA

NPWP/NIK:
     01.234.567.8-901.000

NITKU:
     NITKU-001-2024
```

### **💰 OBJEK PAJAK** *(Section Header Biru)*
```
Jenis PPh:
     PPh 23

Kode Objek Pajak:
     409

Uraian Objek Pajak:
     Jasa Teknik, Manajemen, Konsultan, dan Jasa Lainnya
```

### **🧮 PERHITUNGAN PAJAK** *(Section Header Biru)*
```
┌────────────────────────────────────┬──────────────────────┐
│ Dasar Pengenaan Pajak (DPP)    :  │   Rp 10.000.000     │
│ Tarif                           :  │   2%                │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━│
│ PPh Dipotong                    :  │   Rp 200.000   ◄──  │ (Highlighted)
└────────────────────────────────────┴──────────────────────┘
```

### **📋 DOKUMEN DASAR PEMOTONGAN** *(Section Header Biru)*
```
Jenis Dokumen:
     Invoice

Tanggal Dokumen:
     10-01-2024
```

### **🏢 IDENTITAS PEMOTONG PAJAK** *(Section Header Biru)*
```
Nama:
     PT TEKNOLOGI INDONESIA

NPWP/NIK:
     02.345.678.9-012.000

NITKU/Subunit:
     NITKU-PEMOTONG-2024

Nama Penandatangan:
     Budi Santoso
```

### **Footer (Centered, Small Text)**
```
─────────────────────────────────────────────────────────
Dokumen ini dibuat secara otomatis oleh Doc-Scan AI System
pada 10-10-2025 18:01:35 UTC
─────────────────────────────────────────────────────────
```

---

## 🎨 Tampilan PDF PPh 21

Layout **sama persis** dengan PPh 23, dengan perbedaan:

### **🧮 PERHITUNGAN PAJAK** *(Dengan Penghasilan Bruto)*
```
┌────────────────────────────────────┬──────────────────────┐
│ Penghasilan Bruto               :  │   Rp 15.000.000     │
│ Dasar Pengenaan Pajak (DPP)     :  │   Rp 12.500.000     │
│ Tarif                           :  │   5%                │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━│
│ PPh Dipotong                    :  │   Rp 625.000   ◄──  │ (Highlighted)
└────────────────────────────────────┴──────────────────────┘
```

---

## 📚 Tampilan BATCH EXPORT (Multiple Documents)

Untuk batch export (beberapa dokumen sekaligus):

### **Page 1 - Header**
```
═══════════════════════════════════════════════════
        BUKTI PEMOTONGAN PPh PASAL 23
              BATCH EXPORT - 5 Dokumen
═══════════════════════════════════════════════════

╔═══════════════════════════════════════════════╗
║          DOKUMEN 1 dari 5                     ║
╚═══════════════════════════════════════════════╝

[Informasi lengkap dokumen 1 - format compact]
```

### **Page 2**
```
╔═══════════════════════════════════════════════╗
║          DOKUMEN 2 dari 5                     ║
╚═══════════════════════════════════════════════╝

[Informasi lengkap dokumen 2 - format compact]
```

**...dan seterusnya untuk dokumen 3, 4, 5**

---

## 🎨 Color Scheme & Styling

### **Warna:**
- **Section Headers:** Background biru (#4472C4) dengan teks putih
- **Title:** Biru gelap (#1F4E78)
- **Labels:** Bold hitam (#333333)
- **Values:** Hitam biasa (#000000)
- **Highlights (PPh Dipotong):** Biru (#1F4E78) dengan background abu-abu (#F0F0F0)
- **Footer:** Abu-abu muda (#999999)

### **Typography:**
- **Font:** Helvetica (Professional & Clean)
- **Title:** 18pt Bold
- **Section Headers:** 12pt Bold White
- **Labels:** 10pt Bold
- **Values:** 10pt Regular
- **Footer:** 8pt Italic

### **Layout:**
- **Page Size:** A4
- **Margins:** 20mm semua sisi
- **Spacing:** Konsisten dan rapi
- **Indentation:** 5mm untuk values

---

## 📂 File Output Lokasi

File PDF yang sudah dibuat untuk testing:
- ✅ `test_pph23_output.pdf` (4KB)
- ✅ `test_pph21_output.pdf` (4KB)

Silakan buka file tersebut untuk melihat hasil sebenarnya!

---

## 🚀 Cara Menggunakan

### **Single Document Export:**
```python
from backend.exporters.pph23_exporter import PPh23Exporter

exporter = PPh23Exporter()
exporter.export_to_pdf(result_data, 'output.pdf')
```

### **Batch Export:**
```python
from backend.exporters.pph23_exporter import PPh23Exporter

exporter = PPh23Exporter()
exporter.batch_export_to_pdf('batch_001', batch_results, 'batch_output.pdf')
```

---

## 📝 Catatan Penting

1. **Bukan Tabel:** PDF menggunakan format paragraf dan section, bukan tabel Excel-style
2. **Professional:** Tampilan seperti dokumen resmi pajak
3. **Readable:** Mudah dibaca dengan label yang jelas
4. **Compact:** Batch export menggunakan format yang lebih compact untuk hemat halaman
5. **Automatic Footer:** Setiap PDF memiliki timestamp otomatis

---

## ✅ Perbandingan Format Lama vs Baru

### **❌ Format Lama (Tabel):**
```
┌──────┬────────┬────────┬────────┬────────┐
│ No   │ Nama   │ NPWP   │ DPP    │ PPh    │
├──────┼────────┼────────┼────────┼────────┤
│ 1    │ PT ... │ 01.... │ 10M    │ 200K   │
└──────┴────────┴────────┴────────┴────────┘
```

### **✅ Format Baru (Terstruktur):**
```
📄 INFORMASI DOKUMEN
   Nomor Bukti Potong: 1-23/PPh-23/2024
   Masa Pajak: Januari 2024

👤 IDENTITAS PENERIMA
   Nama: PT MAJU JAYA SENTOSA
   NPWP: 01.234.567.8-901.000

💰 PERHITUNGAN PAJAK
   DPP        : Rp 10.000.000
   Tarif      : 2%
   PPh Dipotong: Rp 200.000
```

Jauh lebih rapi dan profesional! 🎉
