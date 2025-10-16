# Multi-Bank Implementation Plan

## 📋 Ringkasan

Kita perlu implement adapter untuk **9 bank berbeda** dengan output Excel yang **SAMA dan RAPI**.

## 🎯 Goals

1. ✅ Semua 9 bank bisa di-process
2. ✅ Output Excel format SAMA persis
3. ✅ Auto-detect bank dari OCR
4. ✅ Easy maintenance (1 file per bank)
5. ✅ Easy testing
6. ✅ No breaking changes ke existing system

---

## 📦 Fase Implementasi

### **Fase 1: Foundation (Sudah Selesai!)**

✅ File yang sudah dibuat:
- `backend/bank_adapters/__init__.py`
- `backend/bank_adapters/base.py` (BaseBankAdapter + StandardizedTransaction)
- `backend/bank_adapters/mandiri_v1.py` (Sample implementation)
- `MULTI_BANK_ADAPTER_DESIGN.md` (Complete design doc)

### **Fase 2: Implement Semua Bank Adapters (Estimasi: 2-3 hari)**

#### Task 2.1: Implement 8 Remaining Adapters

File yang perlu dibuat:

1. ✅ `mandiri_v1.py` - DONE
2. ⏳ `mufg.py` - MUFG Bank
3. ⏳ `permata.py` - Permata Bank
4. ⏳ `bni_v1.py` - BNI V1
5. ⏳ `bri.py` - BRI
6. ⏳ `bca_syariah.py` - BCA Syariah (Landscape format)
7. ⏳ `mandiri_v2.py` - Mandiri V2
8. ⏳ `bni_v2.py` - BNI V2
9. ⏳ `bsi_syariah.py` - BSI Syariah

#### Task 2.2: Implement BankDetector

- ⏳ `detector.py` - Auto-detect bank dari keywords

---

## 🔨 Detail Implementasi per Bank

### Bank 1: Mandiri V1 ✅ DONE

**Format:**
```
Posting Date | Remark | Reference No | Debit | Credit | Balance
```

**Detection Keywords:**
- PT BANK MANDIRI
- BANK MANDIRI (PERSERO)
- POSTING DATE

**Status:** ✅ Already implemented

---

### Bank 2: MUFG Bank ⏳ TODO

**Format:**
```
Booking Date (Value Date) | Debit | Credit | Opening/Closing Balance |
Transaction Type | Customer Reference | Bank Reference | Detail Information
```

**Detection Keywords:**
- MUFG BANK
- MITSUBISHI UFJ
- BOOKING DATE
- VALUE DATE

**Special Handling:**
- Ada 2 tanggal: Booking Date & Value Date
- Transaction Type → transaction_type
- Customer Reference → reference_number
- Bank Reference → additional_info
- Detail Information → description

**Mapping:**
```python
{
    'transaction_date': booking_date,
    'effective_date': value_date,
    'debit': debit_amount,
    'credit': credit_amount,
    'balance': balance,
    'transaction_type': transaction_type,
    'reference_number': customer_reference,
    'description': detail_information,
    'additional_info': bank_reference,
}
```

---

### Bank 3: Permata Bank ⏳ TODO

**Format:**
```
Post Date | Eff Date | Transaction Code | Cheque Number |
Ref No | Customer No | Description | Debit | Credit | Total
```

**Detection Keywords:**
- BANK PERMATA
- PERMATA BANK
- POST DATE
- EFF DATE

**Special Handling:**
- Post Date → posting_date
- Eff Date → transaction_date & effective_date
- Transaction Code → transaction_type
- Cheque Number → reference_number (jika ada, else gunakan Ref No)
- Customer No → additional_info

**Mapping:**
```python
{
    'transaction_date': eff_date,
    'posting_date': post_date,
    'effective_date': eff_date,
    'description': description,
    'transaction_type': transaction_code,
    'reference_number': cheque_number or ref_no,
    'debit': debit,
    'credit': credit,
    'balance': total,
    'additional_info': customer_no,
}
```

---

### Bank 4: BNI V1 ⏳ TODO

**Format:**
```
Tgl Trans | Uraian | Debet | Kredit | Saldo
```

**Detection Keywords:**
- BANK NEGARA INDONESIA
- PT BANK BNI
- TGL TRANS
- URAIAN

**Special Handling:**
- Format sederhana, 5 kolom saja
- Tgl Trans → transaction_date
- Uraian → description
- Debet/Kredit → ejaan Indonesia

**Mapping:**
```python
{
    'transaction_date': tgl_trans,
    'description': uraian,
    'debit': debet,
    'credit': kredit,
    'balance': saldo,
}
```

---

### Bank 5: BRI ⏳ TODO

**Format:**
```
Tanggal Transaksi | Uraian Transaksi | Teller | Debet | Kredit | Saldo
```

**Detection Keywords:**
- BANK RAKYAT INDONESIA
- PT BANK BRI
- TANGGAL TRANSAKSI
- URAIAN TRANSAKSI

**Special Handling:**
- Ada kolom Teller (unique untuk BRI)
- Teller → teller field

**Mapping:**
```python
{
    'transaction_date': tanggal_transaksi,
    'description': uraian_transaksi,
    'teller': teller,
    'debit': debet,
    'credit': kredit,
    'balance': saldo,
}
```

---

### Bank 6: BCA Syariah ⏳ TODO

**Format (LANDSCAPE!):**
```
Tanggal Efektif | Tanggal Transaksi | Jam Input | Kode Transaksi |
Keterangan | Keterangan Tambahan | D/C | Nominal | Saldo |
Nomor Referensi | Status Otorisasi | User Input | User Otorisasi | Kode Cabang
```

**Detection Keywords:**
- BCA SYARIAH
- PT BANK BCA SYARIAH
- TANGGAL EFEKTIF
- KODE TRANSAKSI

**Special Handling:**
- **LANDSCAPE format** - banyak kolom!
- **D/C parsing:**
  - D = Debit → nominal masuk ke debit
  - C = Credit → nominal masuk ke credit
- Concatenate Keterangan + Keterangan Tambahan
- Jam Input → additional_info
- Kode Cabang → branch_code

**Mapping:**
```python
def _parse_dc(dc_flag: str, nominal: Decimal):
    if dc_flag.upper() == 'D':
        return (nominal, Decimal('0.00'))  # (debit, credit)
    else:
        return (Decimal('0.00'), nominal)  # (debit, credit)

debit, credit = _parse_dc(dc_flag, nominal)

{
    'transaction_date': tanggal_transaksi,
    'effective_date': tanggal_efektif,
    'description': f"{keterangan} {keterangan_tambahan}".strip(),
    'transaction_type': kode_transaksi,
    'reference_number': nomor_referensi,
    'debit': debit,
    'credit': credit,
    'balance': saldo,
    'branch_code': kode_cabang,
    'additional_info': f"Jam: {jam_input}, User: {user_input}",
}
```

---

### Bank 7: Mandiri V2 ⏳ TODO

**Format:**
```
Nama | Nomer Rekening | Tanggal Transaksi | Ket. Kode Transaksi |
Jenis Trans | Remark | Amount | Saldo
```

**Detection Keywords:**
- PT BANK MANDIRI
- BANK MANDIRI (PERSERO)
- KET. KODE TRANSAKSI
- JENIS TRANS

**Special Handling:**
- Nama & Nomer Rekening di setiap row (redundant)
- Amount bisa debit atau credit - perlu parse dari context
- Ket. Kode Transaksi + Jenis Trans → transaction_type
- Remark → description

**Parsing Amount (Tricky!):**
```python
def _parse_amount(ket_kode: str, jenis_trans: str, amount: Decimal):
    """
    Tentukan debit/credit dari context kode transaksi
    """
    # Keywords untuk debit
    debit_keywords = ['TARIK', 'BAYAR', 'TRANSFER KE', 'POTONGAN', 'BIAYA']
    # Keywords untuk credit
    credit_keywords = ['SETOR', 'TERIMA', 'TRANSFER DARI', 'BUNGA']

    combined = f"{ket_kode} {jenis_trans}".upper()

    for keyword in debit_keywords:
        if keyword in combined:
            return (amount, Decimal('0.00'))

    for keyword in credit_keywords:
        if keyword in combined:
            return (Decimal('0.00'), amount)

    # Default: assume credit
    return (Decimal('0.00'), amount)
```

**Mapping:**
```python
debit, credit = _parse_amount(ket_kode, jenis_trans, amount)

{
    'transaction_date': tanggal_transaksi,
    'description': remark,
    'transaction_type': f"{ket_kode} - {jenis_trans}",
    'debit': debit,
    'credit': credit,
    'balance': saldo,
    'account_number': nomer_rekening,
    'account_holder': nama,
}
```

---

### Bank 8: BNI V2 ⏳ TODO

**Format:**
```
Posting Date | Effective Date | Branch | Journal |
Transaction Description | Amount | DB/CR | Balance
```

**Detection Keywords:**
- BANK NEGARA INDONESIA
- PT BANK BNI
- POSTING DATE
- EFFECTIVE DATE
- DB/CR

**Special Handling:**
- **DB/CR parsing:**
  - DB = Debit → amount masuk ke debit
  - CR = Credit → amount masuk ke credit
- Branch → branch_code
- Journal → reference_number

**Mapping:**
```python
def _parse_db_cr(db_cr_flag: str, amount: Decimal):
    if db_cr_flag.upper() in ['DB', 'DEBIT', 'D']:
        return (amount, Decimal('0.00'))
    else:
        return (Decimal('0.00'), amount)

debit, credit = _parse_db_cr(db_cr, amount)

{
    'transaction_date': effective_date,
    'posting_date': posting_date,
    'effective_date': effective_date,
    'description': transaction_description,
    'reference_number': journal,
    'debit': debit,
    'credit': credit,
    'balance': balance,
    'branch_code': branch,
}
```

---

### Bank 9: BSI Syariah ⏳ TODO

**Format:**
```
TrxId | Tanggal | Trx Time | D/K | Mutasi | Saldo | Keterangan
```

**Detection Keywords:**
- BANK SYARIAH INDONESIA
- BSI SYARIAH
- PT BSI
- TRX TIME
- D/K

**Special Handling:**
- **D/K parsing:**
  - D = Debit → mutasi masuk ke debit
  - K = Kredit → mutasi masuk ke credit
- TrxId → reference_number
- Trx Time → additional_info

**Mapping:**
```python
def _parse_dk(dk_flag: str, mutasi: Decimal):
    if dk_flag.upper() in ['D', 'DEBIT']:
        return (mutasi, Decimal('0.00'))
    else:
        return (Decimal('0.00'), mutasi)

debit, credit = _parse_dk(dk, mutasi)

{
    'transaction_date': tanggal,
    'description': keterangan,
    'reference_number': trx_id,
    'debit': debit,
    'credit': credit,
    'balance': saldo,
    'additional_info': f"Time: {trx_time}",
}
```

---

## 🔍 BankDetector Implementation

```python
# backend/bank_adapters/detector.py

from typing import Optional, Dict, Any
from .base import BaseBankAdapter
from .mandiri_v1 import MandiriV1Adapter
from .mandiri_v2 import MandiriV2Adapter
from .mufg import MufgBankAdapter
from .permata import PermataBankAdapter
from .bni_v1 import BniV1Adapter
from .bni_v2 import BniV2Adapter
from .bri import BriAdapter
from .bca_syariah import BcaSyariahAdapter
from .bsi_syariah import BsiSyariahAdapter


class BankDetector:
    """
    Auto-detect bank dari OCR result
    """

    # Registry semua adapters (ORDER MATTERS!)
    ADAPTERS = [
        # Mandiri V2 harus di-check SEBELUM V1 (keywords lebih spesifik)
        MandiriV2Adapter,
        MandiriV1Adapter,

        # BNI V2 sebelum V1
        BniV2Adapter,
        BniV1Adapter,

        # Bank lain
        MufgBankAdapter,
        PermataBankAdapter,
        BriAdapter,
        BcaSyariahAdapter,
        BsiSyariahAdapter,
    ]

    @classmethod
    def detect(cls, ocr_result: Dict[str, Any]) -> Optional[BaseBankAdapter]:
        """
        Auto-detect bank dan return adapter yang sesuai

        Args:
            ocr_result: Raw OCR result dari Google Document AI

        Returns:
            Instance of specific BankAdapter atau None jika tidak terdeteksi
        """
        # Extract text untuk detection
        text = cls._extract_text(ocr_result)

        # Try setiap adapter
        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class()
            if adapter.detect(text):
                print(f"✓ Detected: {adapter.BANK_NAME} ({adapter.BANK_CODE})")
                return adapter

        print("✗ Bank tidak terdeteksi! Gunakan generic adapter atau manual selection.")
        return None

    @classmethod
    def detect_bank_name(cls, ocr_result: Dict[str, Any]) -> str:
        """
        Quick detect bank name saja (untuk logging/display)

        Args:
            ocr_result: Raw OCR result

        Returns:
            Bank name atau "Unknown Bank"
        """
        adapter = cls.detect(ocr_result)
        return adapter.BANK_NAME if adapter else "Unknown Bank"

    @classmethod
    def _extract_text(cls, ocr_result: Dict[str, Any]) -> str:
        """
        Extract full text dari OCR result untuk detection
        """
        if 'text' in ocr_result:
            return ocr_result['text']

        # Try to extract from pages
        text_parts = []
        if 'pages' in ocr_result:
            for page in ocr_result.get('pages', []):
                if 'blocks' in page:
                    for block in page.get('blocks', []):
                        if 'text' in block:
                            text_parts.append(block['text'])

        return '\n'.join(text_parts)

    @classmethod
    def get_supported_banks(cls) -> list:
        """
        Get list of supported banks

        Returns:
            List of dict dengan bank info
        """
        return [
            {
                'code': adapter.BANK_CODE,
                'name': adapter.BANK_NAME,
                'keywords': adapter.DETECTION_KEYWORDS,
            }
            for adapter in [a() for a in cls.ADAPTERS]
        ]
```

---

## 🔧 Integration dengan Existing System

### Update `backend/utils/bank_statement_processor.py`

```python
from bank_adapters import BankDetector, StandardizedTransaction

class BankStatementProcessor:
    """
    Main processor untuk rekening koran (updated untuk multi-bank)
    """

    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process rekening koran document

        Args:
            pdf_path: Path ke PDF rekening koran

        Returns:
            Dict dengan hasil processing
        """
        # 1. OCR with Google Document AI
        ocr_result = self.ocr_engine.process(pdf_path)

        # 2. Auto-detect bank
        adapter = BankDetector.detect(ocr_result)

        if not adapter:
            return {
                'success': False,
                'error': 'Bank tidak terdeteksi. Silakan pilih bank secara manual.',
                'supported_banks': BankDetector.get_supported_banks(),
            }

        # 3. Parse transaksi
        try:
            transactions = adapter.parse(ocr_result)
        except Exception as e:
            return {
                'success': False,
                'error': f'Error parsing {adapter.BANK_NAME}: {str(e)}',
            }

        # 4. Get summary
        summary = adapter.get_summary()

        # 5. Convert ke Excel format
        excel_data = adapter.to_excel_format()

        return {
            'success': True,
            'bank': adapter.BANK_NAME,
            'bank_code': adapter.BANK_CODE,
            'account_number': summary['account_number'],
            'account_holder': summary['account_holder'],
            'transaction_count': len(transactions),
            'total_debit': summary['total_debit'],
            'total_credit': summary['total_credit'],
            'opening_balance': summary['opening_balance'],
            'closing_balance': summary['closing_balance'],
            'transactions': excel_data,
        }

    def process_with_bank(self, pdf_path: str, bank_code: str) -> Dict[str, Any]:
        """
        Process dengan bank yang sudah dipilih manual

        Args:
            pdf_path: Path ke PDF
            bank_code: Bank code (e.g., "MANDIRI_V1")

        Returns:
            Dict dengan hasil processing
        """
        # Find adapter by code
        adapter = self._get_adapter_by_code(bank_code)

        if not adapter:
            return {
                'success': False,
                'error': f'Bank code tidak valid: {bank_code}',
            }

        # Process
        ocr_result = self.ocr_engine.process(pdf_path)
        transactions = adapter.parse(ocr_result)

        # ... (sama seperti di atas)
```

### Update API Endpoint

```python
# backend/routers/documents.py

from bank_adapters import BankDetector

@router.post("/api/documents/rekening-koran/upload")
async def upload_rekening_koran(
    file: UploadFile,
    bank_code: Optional[str] = None,  # Optional: manual selection
    user_id: str = Depends(get_current_user_id)
):
    """
    Upload rekening koran dengan auto-detect bank
    """

    # Save uploaded file
    pdf_path = await save_upload(file)

    # Process
    processor = BankStatementProcessor()

    if bank_code:
        # Manual selection
        result = processor.process_with_bank(pdf_path, bank_code)
    else:
        # Auto-detect
        result = processor.process_document(pdf_path)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Save to database
    # ... (save transactions, summary, etc)

    return {
        'message': 'Berhasil memproses rekening koran',
        'bank': result['bank'],
        'account_number': result['account_number'],
        'transaction_count': result['transaction_count'],
        'summary': {
            'total_debit': result['total_debit'],
            'total_credit': result['total_credit'],
            'opening_balance': result['opening_balance'],
            'closing_balance': result['closing_balance'],
        },
    }

@router.get("/api/documents/rekening-koran/supported-banks")
async def get_supported_banks():
    """
    Get list of supported banks
    """
    return {
        'banks': BankDetector.get_supported_banks()
    }
```

---

## ✅ Testing Plan

### 1. Unit Tests (per adapter)

```python
# tests/test_adapters/test_mandiri_v1.py

def test_mandiri_v1_detection():
    adapter = MandiriV1Adapter()
    text = "PT BANK MANDIRI (PERSERO) TBK\nPOSTING DATE | REMARK"
    assert adapter.detect(text) == True

def test_mandiri_v1_parsing():
    adapter = MandiriV1Adapter()
    ocr_result = load_sample('mandiri_v1_sample.json')
    transactions = adapter.parse(ocr_result)

    assert len(transactions) > 0
    assert all(t.bank_name == "Bank Mandiri" for t in transactions)

def test_mandiri_v1_amount_cleaning():
    adapter = MandiriV1Adapter()
    assert adapter.clean_amount("1.000.000,00") == Decimal("1000000.00")
    assert adapter.clean_amount("500,50") == Decimal("500.50")

# Repeat for all 9 banks...
```

### 2. Integration Tests

```python
def test_all_banks_same_output_format():
    """Pastikan semua bank output Excel dengan format yang SAMA"""

    for adapter_class in BankDetector.ADAPTERS:
        adapter = adapter_class()
        ocr_result = load_sample(f'{adapter.BANK_CODE.lower()}_sample.json')
        transactions = adapter.parse(ocr_result)
        excel_data = adapter.to_excel_format()

        # Check columns
        expected_columns = [
            'Tanggal Transaksi', 'Tanggal Posting', 'Keterangan',
            'Tipe Transaksi', 'No Referensi', 'Debit', 'Kredit',
            'Saldo', 'Cabang', 'Info Tambahan', 'Bank',
            'No Rekening', 'Nama Pemegang'
        ]

        assert list(excel_data[0].keys()) == expected_columns
```

### 3. Detection Tests

```python
def test_bank_detection_accuracy():
    """Test detection accuracy untuk semua bank"""

    test_cases = [
        ('mandiri_v1_sample.json', 'MANDIRI_V1'),
        ('mandiri_v2_sample.json', 'MANDIRI_V2'),  # Important: V2 before V1!
        ('mufg_sample.json', 'MUFG'),
        ('permata_sample.json', 'PERMATA'),
        ('bni_v1_sample.json', 'BNI_V1'),
        ('bni_v2_sample.json', 'BNI_V2'),
        ('bri_sample.json', 'BRI'),
        ('bca_syariah_sample.json', 'BCA_SYARIAH'),
        ('bsi_syariah_sample.json', 'BSI_SYARIAH'),
    ]

    for sample_file, expected_code in test_cases:
        ocr_result = load_sample(sample_file)
        adapter = BankDetector.detect(ocr_result)

        assert adapter is not None, f"Failed to detect {sample_file}"
        assert adapter.BANK_CODE == expected_code
```

---

## 📝 Checklist

### Fase 2.1: Implement Adapters

- [x] mandiri_v1.py
- [ ] mufg.py
- [ ] permata.py
- [ ] bni_v1.py
- [ ] bri.py
- [ ] bca_syariah.py
- [ ] mandiri_v2.py
- [ ] bni_v2.py
- [ ] bsi_syariah.py

### Fase 2.2: Implement Detector

- [ ] detector.py

### Fase 2.3: Integration

- [ ] Update bank_statement_processor.py
- [ ] Update documents.py router
- [ ] Add new API endpoints

### Fase 2.4: Testing

- [ ] Unit tests untuk 9 adapters
- [ ] Integration tests
- [ ] Detection accuracy tests
- [ ] Manual testing dengan real documents

### Fase 2.5: Documentation

- [ ] API documentation
- [ ] User guide (cara upload per bank)
- [ ] Troubleshooting guide

---

## 🚀 Timeline

**Total Estimasi: 2-3 hari kerja**

- **Hari 1:** Implement 5 adapters (MUFG, Permata, BNI V1, BRI, Mandiri V2)
- **Hari 2:** Implement 3 adapters (BNI V2, BCA Syariah, BSI) + Detector
- **Hari 3:** Integration, testing, bug fixes

---

## 💡 Tips untuk Implementation

1. **Start dengan yang sederhana** (BNI V1, BRI) → confidence boost
2. **Test dengan real samples** ASAP → catch edge cases early
3. **Logging is your friend** → print detected bank, parsed count, errors
4. **Handle missing fields gracefully** → default to empty string, not error
5. **Date parsing is tricky** → try multiple formats
6. **Amount cleaning is critical** → test with various formats

---

Siap untuk mulai implementasi? Mau gue lanjutkan buat semua adapter sekarang? 🚀
