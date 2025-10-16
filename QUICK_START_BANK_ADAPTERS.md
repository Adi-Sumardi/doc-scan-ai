# Quick Start - Multi-Bank Adapters 🚀

## 🎯 Apa yang Udah Dibuat?

Sistem adapter yang bisa handle **9 bank berbeda** dengan output Excel yang **SAMA dan RAPI**!

### ✅ Bank yang Didukung:

1. ✅ **Bank Mandiri V1** - Format: Posting Date, Remark, Reference No, Debit, Credit, Balance
2. ✅ **Bank Mandiri V2** - Format: Nama, No Rek, Tgl Trans, Ket Kode, Jenis Trans, Remark, Amount, Saldo
3. ✅ **MUFG Bank** - Format: Booking Date, Value Date, Debit, Credit, Balance, Transaction Type
4. ✅ **Permata Bank** - Format: Post Date, Eff Date, Transaction Code, Description, Debit, Credit
5. ✅ **BNI V1** - Format: Tgl Trans, Uraian, Debet, Kredit, Saldo
6. ✅ **BNI V2** - Format: Posting Date, Effective Date, Branch, Journal, Description, Amount, DB/CR
7. ✅ **BRI** - Format: Tanggal, Uraian, Teller, Debet, Kredit, Saldo
8. ✅ **BCA Syariah** - Format: Landscape dengan 14 kolom (Tgl Efektif, Tgl Trans, Kode Trans, D/C, dll)
9. ✅ **BSI Syariah** - Format: TrxId, Tanggal, Trx Time, D/K, Mutasi, Saldo, Keterangan

---

## 📁 File Structure

```
backend/
├── bank_adapters/
│   ├── __init__.py           # ✅ Main exports & helper functions
│   ├── base.py               # ✅ Base adapter & StandardizedTransaction
│   ├── detector.py           # ✅ Auto-detect bank
│   ├── mandiri_v1.py         # ✅ Bank Mandiri V1
│   ├── mandiri_v2.py         # ✅ Bank Mandiri V2
│   ├── mufg.py               # ✅ MUFG Bank
│   ├── permata.py            # ✅ Permata Bank
│   ├── bni_v1.py             # ✅ BNI V1
│   ├── bni_v2.py             # ✅ BNI V2
│   ├── bri.py                # ✅ BRI
│   ├── bca_syariah.py        # ✅ BCA Syariah
│   └── bsi_syariah.py        # ✅ BSI Syariah
└── test_bank_adapters.py     # ✅ Test suite
```

---

## 🚀 Cara Pakai

### 1. Simple Usage (Auto-detect)

```python
from bank_adapters import detect_bank

# Upload rekening koran
ocr_result = google_document_ai.process(pdf_file)

# Auto-detect bank
adapter = detect_bank(ocr_result)

if adapter:
    print(f"Bank terdeteksi: {adapter.BANK_NAME}")

    # Parse transaksi
    transactions = adapter.parse(ocr_result)

    # Convert ke Excel format (SAMA untuk semua bank!)
    excel_data = adapter.to_excel_format()

    # Get summary
    summary = adapter.get_summary()
    print(f"Total transaksi: {summary['transaction_count']}")
    print(f"Total Debit: Rp {summary['total_debit']:,.2f}")
    print(f"Total Credit: Rp {summary['total_credit']:,.2f}")
else:
    print("Bank tidak terdeteksi!")
```

### 2. One-Liner Usage

```python
from bank_adapters import process_bank_statement

# Super simple!
result = process_bank_statement(ocr_result)

if result['success']:
    print(f"Bank: {result['bank_name']}")
    print(f"Transaksi: {len(result['transactions'])}")

    # Langsung dapat Excel data!
    excel_data = result['transactions']
else:
    print(f"Error: {result['error']}")
```

### 3. Manual Bank Selection

```python
from bank_adapters import BankDetector

# User pilih bank manual (misalnya dari dropdown)
adapter = BankDetector.get_adapter_by_code('MANDIRI_V1')

if adapter:
    transactions = adapter.parse(ocr_result)
    excel_data = adapter.to_excel_format()
```

### 4. Get Supported Banks

```python
from bank_adapters import get_supported_banks

banks = get_supported_banks()

for bank in banks:
    print(f"{bank['name']} ({bank['code']})")
    print(f"  Keywords: {bank['keywords'][:3]}")
```

---

## 📊 Output Excel Format (SAMA untuk SEMUA bank!)

```python
excel_data = adapter.to_excel_format()

# excel_data adalah list of dict dengan struktur:
{
    'Tanggal Transaksi': '15/01/2025',
    'Tanggal Posting': '15/01/2025',
    'Keterangan': 'Transfer dari PT ABC',
    'Tipe Transaksi': 'TRANSFER',
    'No Referensi': 'REF001',
    'Debit': 0.00,
    'Kredit': 1000000.00,
    'Saldo': 5000000.00,
    'Cabang': '0001',
    'Info Tambahan': 'Time: 10:30',
    'Bank': 'Bank Mandiri',
    'No Rekening': '123-45-67890123-4',
    'Nama Pemegang': 'PT CONTOH COMPANY',
}
```

### Export ke Excel

```python
import pandas as pd

# Convert ke DataFrame
df = pd.DataFrame(excel_data)

# Save ke Excel
df.to_excel('rekening_koran.xlsx', index=False)

# Atau dengan formatting
with pd.ExcelWriter('rekening_koran.xlsx', engine='openpyxl') as writer:
    # Summary sheet
    summary_df = pd.DataFrame([adapter.get_summary()])
    summary_df.to_excel(writer, sheet_name='Ringkasan', index=False)

    # Transactions sheet
    df.to_excel(writer, sheet_name='Transaksi', index=False)
```

---

## 🧪 Testing

### Run Test Suite

```bash
cd backend
python test_bank_adapters.py
```

Output:
```
🚀 Bank Adapters Test Suite
============================================================

🧪 Testing imports...
✓ All imports successful!

🧪 Testing adapter instantiation...
✓ Bank Mandiri (MANDIRI_V2)
  Keywords: ['PT BANK MANDIRI', 'BANK MANDIRI (PERSERO)']
✓ Bank Mandiri (MANDIRI_V1)
  Keywords: ['PT BANK MANDIRI', 'BANK MANDIRI (PERSERO)']
...

📊 Test Summary
============================================================
✓ PASS - Imports
✓ PASS - Adapter Instantiation
✓ PASS - Detection Logic
✓ PASS - StandardizedTransaction
✓ PASS - Helper Functions

Total: 5/5 tests passed (100.0%)

🎉 All tests passed! Bank adapters are ready to use!
```

---

## 🔍 Debug Detection

Kalau detection gagal, gunakan test mode:

```python
from bank_adapters import BankDetector

result = BankDetector.test_detection(ocr_result)

print(f"Text length: {result['text_length']}")
print(f"Text preview: {result['text_preview']}")
print(f"Detected: {result['detected_bank']}")

print("\nDetection scores:")
for score in result['detection_scores']:
    print(f"  {score['bank_name']}: {score['match_percentage']:.1f}%")
    print(f"    Matched keywords: {score['matched_keywords']}")
```

---

## 💡 Special Cases

### 1. BCA Syariah (Landscape Format)

BCA Syariah punya banyak kolom (sampai 14!). Adapter handle semua kolom dan extract yang penting:

```python
# BCA Syariah fields:
- Tanggal Efektif → effective_date
- Tanggal Transaksi → transaction_date
- Kode Transaksi → transaction_type
- D/C flag → parsed ke debit/credit
- Kode Cabang → branch_code
- Jam Input, User → additional_info
```

### 2. Mandiri V2 (Amount Parsing)

Mandiri V2 punya "Amount" yang bisa debit atau credit. Adapter auto-detect dari context:

```python
# Keywords untuk Debit:
'TARIK', 'BAYAR', 'TRANSFER KE', 'POTONGAN', 'BIAYA', 'ATM WITHDRAWAL'

# Keywords untuk Credit:
'SETOR', 'TERIMA', 'TRANSFER DARI', 'BUNGA', 'DEPOSIT', 'PENERIMAAN'
```

### 3. BNI V2 & BSI (DB/CR Flag)

Ada flag DB/CR atau D/K untuk distinguish:

```python
# BNI V2:
'DB' atau 'DEBIT' → debit
'CR' atau 'CREDIT' → credit

# BSI:
'D' → debit
'K' → kredit
```

---

## 🛠️ Troubleshooting

### Bank tidak terdeteksi?

1. **Check text extraction:**
   ```python
   text = adapter._extract_text(ocr_result)
   print(text[:500])  # Print 500 chars pertama
   ```

2. **Check keywords:**
   ```python
   from bank_adapters import get_supported_banks

   banks = get_supported_banks()
   for bank in banks:
       print(f"{bank['name']}: {bank['keywords']}")
   ```

3. **Manual override:**
   ```python
   # Kalau auto-detect gagal, pilih manual
   adapter = BankDetector.get_adapter_by_code('MANDIRI_V1')
   ```

### Parsing error?

1. **Check OCR result structure:**
   ```python
   print(ocr_result.keys())  # Should have 'tables' or 'pages'
   ```

2. **Check table structure:**
   ```python
   if 'tables' in ocr_result:
       for table in ocr_result['tables']:
           print(f"Rows: {len(table['rows'])}")
           print(f"Cols: {len(table['rows'][0]['cells'])}")
   ```

3. **Use raw_data for debugging:**
   ```python
   for trans in transactions:
       print(trans.raw_data)  # See original parsed data
   ```

---

## 📚 Next Steps

### Integrasi ke Main App

File yang perlu diupdate:

1. **backend/utils/bank_statement_processor.py**
   - Import bank_adapters
   - Gunakan BankDetector.detect()
   - Return standardized format

2. **backend/routers/documents.py**
   - Add endpoint untuk rekening koran
   - Support auto-detect & manual selection
   - Return Excel data

3. **frontend/src/pages/Upload.tsx**
   - Add bank selection dropdown (optional)
   - Show detected bank
   - Download Excel result

### Sample Integration Code

```python
# backend/routers/documents.py

from bank_adapters import BankDetector, process_bank_statement

@router.post("/api/documents/rekening-koran/upload")
async def upload_rekening_koran(
    file: UploadFile,
    bank_code: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Upload dan process rekening koran"""

    # Save file
    pdf_path = await save_upload(file)

    # OCR dengan Google Document AI
    ocr_result = await ocr_engine.process(pdf_path)

    # Process dengan bank adapter
    result = process_bank_statement(ocr_result, bank_code=bank_code)

    if not result['success']:
        raise HTTPException(400, detail=result['error'])

    # Save to database
    await save_transactions(
        user_id=user_id,
        bank_name=result['bank_name'],
        transactions=result['transactions'],
        summary=result['summary'],
    )

    return {
        'success': True,
        'bank': result['bank_name'],
        'summary': result['summary'],
        'download_url': f'/api/documents/rekening-koran/download/{doc_id}',
    }
```

---

## 🎉 Summary

**Yang udah dibuat:**
- ✅ 9 bank adapters (complete!)
- ✅ Auto-detection system
- ✅ Standardized output format
- ✅ Test suite
- ✅ Helper functions
- ✅ Documentation

**Keuntungan:**
- ✅ Output Excel SAMA untuk semua bank
- ✅ Easy maintenance (1 file per bank)
- ✅ Auto-detect bank dari OCR
- ✅ Scalable (tambah bank baru tinggal copy template)
- ✅ Type-safe dengan Decimal untuk currency

**Ready to use!** 🚀

Tinggal integrate ke main app dan testing dengan real samples! 💪
