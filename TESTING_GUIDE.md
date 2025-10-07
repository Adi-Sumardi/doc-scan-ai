# 🧪 Quick Testing Guide - Structured Data Export

## 🎯 Purpose
Verify that the new structured data extraction and table export features work correctly with Indonesian Faktur Pajak documents.

---

## ⚡ Quick Start

### 1. Start Local Backend
```bash
cd /Users/yapi/Adi/App-Dev/doc-scan-ai/backend
source ../doc_scan_env/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Frontend (New Terminal)
```bash
cd /Users/yapi/Adi/App-Dev/doc-scan-ai
npm run dev
```

### 3. Open Browser
```
http://localhost:5173
```

---

## 📋 Test Checklist

### Test 1: Single Document Upload & Extraction ✅

**Steps**:
1. Upload a Faktur Pajak PDF
2. Wait for processing to complete
3. Check backend console logs for:
   ```
   ✅ Structured fields extracted: X fields populated
   ```
4. Open result in split view
5. Verify document preview shows on left
6. Verify extracted data shows on right

**Expected Fields** (check logs or database):
- ✅ nama (company name with PT/CV/UD)
- ✅ tanggal (date in any format)
- ✅ npwp (XX.XXX.XXX.X-XXX.XXX format)
- ✅ nomor_faktur (XXX.XXX-XX.XXXXXXXX format)
- ✅ alamat (address with Jl, Gedung, etc.)
- ✅ dpp (tax base amount with Rp)
- ✅ ppn (VAT amount)
- ✅ total (total amount)
- ✅ invoice (alternative invoice number)
- ✅ nama_barang_jasa (goods/services description)

**Pass Criteria**: At least 6-8 fields extracted correctly

---

### Test 2: Single Excel Export ✅

**Steps**:
1. Click "Download Excel" button for uploaded document
2. Open downloaded .xlsx file in Excel/LibreOffice

**Verify**:
- ✅ **Row 1**: Title "📋 DOKUMEN PAJAK - DATA TERSTRUKTUR" merged across columns
- ✅ **Row 2**: 10 column headers with blue background (#1e40af), white text
  - Nama | Tgl | NPWP | Nomor Faktur | Alamat | DPP | PPN | Total | Invoice | Nama Barang/Jasa
- ✅ **Row 3**: Single data row with light blue background (#dbeafe)
- ✅ **All 10 columns** have values (or "N/A" if not found)
- ✅ **Borders**: Thin black lines around all cells
- ✅ **Column widths**: Auto-sized (20, 12, 20, 18, 35, 15, 15, 15, 15, 40)
- ✅ **Row 5+**: Document metadata (filename, doc type, confidence)

**Pass Criteria**: Table format is professional and all data visible

---

### Test 3: Single PDF Export ✅

**Steps**:
1. Click "Download PDF" button for uploaded document
2. Open downloaded .pdf file

**Verify**:
- ✅ **Title**: "📋 DOKUMEN PAJAK - DATA TERSTRUKTUR" centered at top
- ✅ **Table Header**: 10 columns with blue background, white text, 7pt font
- ✅ **Data Row**: 10 values with light blue background, black text, 6pt font
- ✅ **Table Fit**: All columns visible without overflow on A4 portrait page
- ✅ **Readability**: Font is small but readable (6-7pt)
- ✅ **Truncation**: Alamat and Nama Barang/Jasa may be truncated to 30 chars (acceptable)
- ✅ **Document Info**: Metadata section below table

**Pass Criteria**: Table fits on page, all columns readable

---

### Test 4: Batch Excel Export ✅

**Steps**:
1. Upload 3-5 Faktur Pajak PDFs
2. Select all documents in results list
3. Click "Batch Export" → "Download Excel"
4. Open downloaded batch .xlsx file

**Verify**:
- ✅ **Single Sheet**: "Batch Documents" (not separate sheets per document)
- ✅ **Row 1**: Batch info header (Batch ID, Total, Export Date) merged across columns
- ✅ **Row 2**: 10 column headers with blue background
- ✅ **Row 3+**: One data row per document
- ✅ **Alternating Colors**: Light blue (#dbeafe) and white rows
- ✅ **All Documents**: Each uploaded document has a row
- ✅ **Data Quality**: Check at least 2-3 rows have correct field values

**Pass Criteria**: Consolidated table with all documents, professional formatting

---

### Test 5: Batch PDF Export ✅

**Steps**:
1. Use same batch from Test 4
2. Click "Batch Export" → "Download PDF"
3. Open downloaded batch .pdf file

**Verify**:
- ✅ **Title**: Batch ID, Total docs, Export date centered at top
- ✅ **Single Table**: One multi-row table (not separate sections per document)
- ✅ **Row 1**: 10 column headers with blue background, 7pt font
- ✅ **Row 2+**: One data row per document, 6pt font
- ✅ **Alternating Colors**: Light blue and white rows
- ✅ **Table Fit**: All documents fit on available pages without overflow
- ✅ **Readability**: Font is small but all data visible

**Pass Criteria**: Consolidated table with all documents fitting on pages

---

## 🔍 Database Verification (Optional)

### Check Structured Data Storage

```bash
# Connect to database
sqlite3 backend/doc_scan_dev.db  # or MySQL connection

# Query recent results
SELECT 
    original_filename,
    document_type,
    json_extract(extracted_data, '$.structured_data.nama') as nama,
    json_extract(extracted_data, '$.structured_data.npwp') as npwp,
    json_extract(extracted_data, '$.structured_data.nomor_faktur') as nomor_faktur,
    json_extract(extracted_data, '$.structured_data.total') as total
FROM scan_results
ORDER BY created_at DESC
LIMIT 5;
```

**Expected**: See extracted field values for recent uploads

---

## 🐛 Common Issues & Solutions

### Issue: No Fields Extracted (All "N/A")

**Diagnosis**:
```bash
# Check backend logs
tail -f backend/backend.log | grep "Structured fields"

# Should see:
# ✅ Structured fields extracted: X fields populated
```

**Possible Causes**:
1. Document is not Faktur Pajak format
2. OCR quality is poor (low confidence)
3. Regex patterns don't match document layout

**Solution**:
- Try different Faktur Pajak document
- Check raw OCR text in database
- Review regex patterns in `extract_structured_fields()`

---

### Issue: Excel/PDF Won't Download

**Diagnosis**:
```bash
# Check backend logs for export errors
tail -f backend/backend.log | grep "export"
```

**Possible Causes**:
1. openpyxl or reportlab not installed
2. File permissions issue
3. Export path doesn't exist

**Solution**:
```bash
# Reinstall export libraries
pip install openpyxl reportlab

# Check exports directory exists
ls -la backend/exports/

# If not, create it
mkdir -p backend/exports
```

---

### Issue: PDF Columns Overflow

**Observation**: Table doesn't fit on A4 page

**Solution Options**:
1. **Reduce column widths** in `create_enhanced_pdf_export()`:
   ```python
   col_widths = [0.8*inch, 0.5*inch, ...]  # Reduce from current
   ```

2. **Increase truncation** for long fields:
   ```python
   structured.get('alamat', 'N/A')[:25]  # Reduce from 30
   ```

3. **Switch to landscape** (in doc definition):
   ```python
   doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), ...)
   ```

---

### Issue: Fonts Too Small in PDF

**Observation**: 6pt font is hard to read

**Solution**:
1. **Increase font size** (may cause overflow):
   ```python
   ('FONTSIZE', (0, 0), (-1, 0), 8),  # Headers: 7→8pt
   ('FONTSIZE', (0, 1), (-1, -1), 7),  # Data: 6→7pt
   ```

2. **Reduce column count** (requires redesign):
   - Combine columns (e.g., DPP+PPN+Total into "Amounts")
   - Remove less critical columns

---

## 📊 Sample Test Data

### Good Test Documents
- **Faktur Pajak** with clear company name (PT/CV prefix)
- **Tax invoices** with NPWP format XX.XXX.XXX.X-XXX.XXX
- **Documents** with Nomor Faktur XXX.XXX-XX.XXXXXXXX format
- **Invoices** with clear DPP/PPN/Total amounts

### Expected Extraction Rates
- **Nama**: 90%+ (most documents have company name)
- **Tanggal**: 85%+ (dates are common)
- **NPWP**: 80%+ (tax documents usually have this)
- **Nomor Faktur**: 75%+ (specific format may not always match)
- **Alamat**: 70%+ (addresses vary widely)
- **DPP/PPN/Total**: 80%+ (financial amounts usually present)
- **Invoice**: 50%+ (alternative number format)
- **Nama Barang/Jasa**: 60%+ (description may be abbreviated)

---

## ✅ Success Criteria Summary

### Minimum Acceptable Performance
- ✅ At least **6 out of 10 fields** extracted per document
- ✅ **Excel tables** display correctly with blue headers and light blue data
- ✅ **PDF tables** fit on page with all 10 columns visible
- ✅ **Batch exports** create consolidated tables (not separate sections)
- ✅ **No errors** in backend logs during export generation

### Ideal Performance
- ✅ **8+ out of 10 fields** extracted per document
- ✅ All formatting matches design (colors, fonts, borders)
- ✅ Fast export generation (< 5 seconds for single document)
- ✅ Professional appearance suitable for client delivery
- ✅ Users can analyze data in Excel (filters, sorts, pivot tables)

---

## 🚀 Production Testing (After VPS Deploy)

### Once Deployed to docscan.adilabs.id

1. **Upload Test Documents**:
   - Use real Faktur Pajak PDFs from tax processing work
   - Upload at least 5-10 different documents

2. **Share with Tax Team**:
   - Get feedback on field extraction accuracy
   - Ask if any critical fields are missing
   - Check if table format meets their needs

3. **Monitor Performance**:
   - Check backend logs for any extraction errors
   - Monitor export generation time
   - Watch for any memory/CPU issues with large batches

4. **Iterate Based on Feedback**:
   - Add more regex patterns if certain fields not extracting
   - Adjust column widths/fonts if readability issues
   - Consider adding new fields if requested

---

## 📝 Testing Log Template

```
Date: _______________
Tester: _______________

Test 1 - Upload & Extraction: ☐ Pass ☐ Fail
  Fields extracted: ___/10
  Notes: _______________________________________________

Test 2 - Excel Export: ☐ Pass ☐ Fail
  Table format correct: ☐ Yes ☐ No
  Notes: _______________________________________________

Test 3 - PDF Export: ☐ Pass ☐ Fail
  Fits on page: ☐ Yes ☐ No
  Notes: _______________________________________________

Test 4 - Batch Excel: ☐ Pass ☐ Fail
  Documents tested: ___
  Notes: _______________________________________________

Test 5 - Batch PDF: ☐ Pass ☐ Fail
  Documents tested: ___
  Notes: _______________________________________________

Overall Status: ☐ Ready for Production ☐ Needs Work
Blocker Issues: _______________________________________________
```

---

**Good luck with testing! 🎉**

If you encounter any issues, refer to the troubleshooting section or check the backend logs for detailed error messages.
