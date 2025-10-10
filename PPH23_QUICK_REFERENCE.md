# Quick Reference: PPh 23 System

## Untuk Pengguna

### Cara Upload PPh 23
1. Buka halaman Upload
2. Pilih jenis dokumen: **"Bukti Potong PPh 23"**
3. Upload 1-10 file PDF (bisa multiple files sekaligus)
4. Tunggu proses AI (Smart Mapper GPT-4o akan extract data otomatis)
5. Lihat hasil di halaman Scan Results

### Cara Download Excel
**Single Document:**
- Buka Scan Results
- Klik "Download Excel" pada dokumen yang diinginkan
- File Excel akan terdownload dengan 20 kolom data

**Multiple Documents (Batch):**
- Buka Dashboard
- Cari batch PPh 23 yang sudah diproses
- Klik "Download All (Excel)"
- Semua dokumen PPh 23 akan jadi 1 file Excel

### Format Excel Output
Excel file akan memiliki **20 kolom**:
1. Nomor Bukti Potong
2. Masa Pajak (bulan/tahun)
3. Sifat Pemotongan (Final/Tidak Final)
4. Status Bukti Pemotongan (Normal/Pembetulan/Pembatalan)
5. NPWP/NIK Penerima
6. Nama Penerima
7. NITKU Penerima
8. Jenis PPh (default: PPh 23)
9. Kode Objek Pajak (01-99)
10. Objek Pajak (deskripsi jenis penghasilan)
11. **DPP** (Dasar Pengenaan Pajak/Bruto)
12. **Tarif** (% pajak)
13. **PPh** (jumlah pajak yang dipotong)
14. Jenis Dokumen Dasar (Invoice/Faktur/Kontrak)
15. Tanggal Dokumen Dasar
16. NPWP/NIK Pemotong
17. NITKU/Subunit Pemotong
18. Nama Pemotong
19. Tanggal Potong
20. Nama Penandatangan

### Catatan Penting
- ✅ PPh 23 **hanya export Excel** (tidak ada PDF)
- ✅ Semua data di-extract otomatis oleh AI (GPT-4o)
- ✅ Jika ada field yang tidak terdeteksi, akan muncul "N/A"
- ✅ Format angka dan tanggal akan dirapikan otomatis
- ✅ NPWP akan di-normalize ke format standar

---

## For Developers

### File Locations
```
backend/
├── exporters/
│   └── pph23_exporter.py          # PPh 23 exporter (20 columns, Excel-only)
├── templates/
│   └── pph23_template.json        # Smart Mapper schema for PPh 23
└── routers/
    └── exports.py                 # Export endpoints (updated)

frontend/
└── src/pages/
    └── Upload.tsx                 # Already has PPh 23 configured
```

### API Endpoints
**Single Export:**
```
GET /api/exports/{result_id}/{format}
- format: "excel" (PDF not supported for PPh 23)
- Returns: Excel file with 20 columns
```

**Batch Export:**
```
GET /api/exports/batch/{batch_id}/{format}
- format: "excel" (PDF not supported for PPh 23)
- Auto-detects all-PPh23 batches
- Returns: Single Excel file with all documents
```

### Smart Mapper Schema
Template file: `backend/templates/pph23_template.json`

Expected structure from GPT-4o:
```json
{
  "dokumen": { /* nomor, masa_pajak, tanggal, sifat_pemotongan, status */ },
  "penerima": { /* npwp, nama, nitku */ },
  "pemotong": { /* npwp, nama, nitku, penandatangan */ },
  "objek_pajak": { /* jenis_pph, kode, objek */ },
  "financials": { /* dpp, tarif, pph */ },
  "dokumen_dasar": { /* jenis, tanggal */ }
}
```

### Exporter Methods
```python
from exporters.pph23_exporter import PPh23Exporter

exporter = PPh23Exporter()

# Single document export
exporter.export_to_excel(result_data, "output.xlsx")

# Batch export
exporter.export_batch_to_excel(results_list, "batch_output.xlsx")

# Convert Smart Mapper to structured
structured = exporter._convert_smart_mapped_to_structured(smart_mapped_data)
```

### Testing
```bash
# Check for syntax errors
python3 -m py_compile backend/exporters/pph23_exporter.py

# Manual test
cd backend
python3 -c "
from exporters.pph23_exporter import PPh23Exporter
e = PPh23Exporter()
print(f'Columns: {len(e.columns)} (expected: 20)')
print(e.columns)
"
```

### Troubleshooting

**Problem: Excel export shows "N/A" for financial data**
- Check Smart Mapper output has `financials` section
- Verify field names match: `dpp`, `tarif`, `pph` (case-insensitive)
- Check `extracted_data['smart_mapped']['financials']`

**Problem: Document type not recognized**
- Verify document_type is one of: `pph23`, `pph 23`, `pph_23`
- Check ExportFactory registration in `export_factory.py`

**Problem: Upload page doesn't show PPh 23**
- Check `documentTypes` array in `src/pages/Upload.tsx`
- Should have entry with `id: 'pph23'`

**Problem: Batch export uses wrong template**
- Check all documents in batch have same document_type
- Router detects document type at line ~176 in `exports.py`
- Must be exact match: `pph23` or `pph 23`

### Code Quality
- ✅ No lint errors
- ✅ No duplicate methods
- ✅ No unused imports
- ✅ Type hints where applicable
- ✅ Comprehensive error logging
- ✅ Follows existing patterns (Faktur Pajak exporter)

### Integration Points
1. **Smart Mapper** - Extracts structured data from PDF
2. **Export Factory** - Routes document type to correct exporter
3. **Export Router** - Handles single/batch export requests
4. **Upload Page** - Presents PPh 23 as selectable document type
5. **Scan Results** - Displays extracted PPh 23 data

---

## System Architecture

```
┌─────────────────┐
│   User Upload   │ (1-10 PPh 23 PDFs)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Google Doc AI  │ (OCR + Entity Extraction)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Smart Mapper    │ (GPT-4o structures data)
│   (GPT-4o)      │ → 6 sections, 20 fields
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Database Store  │ (smart_mapped field)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Export Request  │ (user clicks download)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PPh23Exporter   │ (converts to 20 columns)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Excel File     │ (20 columns with styling)
└─────────────────┘
```

---

## Environment Requirements
- ✅ Python 3.10+
- ✅ openpyxl (Excel export)
- ✅ OpenAI API key (for Smart Mapper GPT-4o)
- ✅ Google Cloud credentials (for Document AI OCR)

---

## Version History
- **v1.0** (2025-01-07) - Initial PPh 23 implementation
  - 20-column Excel export
  - Smart Mapper GPT-4o integration
  - Single and batch export support
  - No PDF export (Excel-only per requirement)
