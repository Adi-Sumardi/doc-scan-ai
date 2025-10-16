# Multi-Bank Adapter System - Design & Implementation

## 🎯 Tujuan

Sistem ini dibuat untuk handle **9 bank berbeda** dengan format rekening koran yang berbeda-beda, tapi **output Excel tetap sama dan rapi**.

### Bank yang Didukung:

1. **Bank Mandiri V1** - Format: Posting Date, Remark, Reference No, Debit, Credit, Balance
2. **MUFG Bank** - Format: Booking Date, Debit, Credit, Balance, Transaction Type, References, Detail
3. **Permata Bank** - Format: Post Date, Eff Date, Transaction Code, Cheque, Ref No, Description, Debit, Credit
4. **BNI V1** - Format: Tgl Trans, Uraian, Debet, Kredit, Saldo
5. **BRI** - Format: Tanggal, Uraian, Teller, Debet, Kredit, Saldo
6. **BCA Syariah** - Format: Landscape dengan banyak kolom (Tgl Efektif, Tgl Trans, Jam, Kode Trans, Keterangan, D/C, Nominal, Saldo, dll)
7. **Bank Mandiri V2** - Format: Nama, No Rek, Tgl Trans, Ket Kode, Jenis Trans, Remark, Amount, Saldo
8. **BNI V2** - Format: Posting Date, Effective Date, Branch, Journal, Description, Amount, DB/CR, Balance
9. **BSI Syariah** - Format: TrxId, Tanggal, Trx Time, D/K, Mutasi, Saldo, Keterangan

---

## 🏗️ Arsitektur Sistem

### 1. Bank Adapter Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Upload                          │
│                    (PDF Rekening Koran)                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Google Document AI OCR                       │
│              (Extract text & tables)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Bank Detector                             │
│     (Auto-detect bank dari keywords & format)                │
│                                                              │
│  - Check "PT BANK MANDIRI" → Mandiri Adapter               │
│  - Check "MUFG BANK" → MUFG Adapter                         │
│  - Check "BANK PERMATA" → Permata Adapter                   │
│  - etc...                                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Specific Bank Adapter                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Mandiri    │  │     MUFG     │  │   Permata    │     │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │     BNI      │  │     BRI      │  │ BCA Syariah  │     │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Mandiri V2  │  │   BNI V2     │  │BSI Syariah   │     │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           StandardizedTransaction Objects                    │
│                                                              │
│  Semua adapter convert ke format yang SAMA:                 │
│  - transaction_date                                          │
│  - posting_date                                              │
│  - description                                               │
│  - reference_number                                          │
│  - debit                                                     │
│  - credit                                                    │
│  - balance                                                   │
│  - bank_name                                                 │
│  - account_number                                            │
│  - etc...                                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Excel Exporter                              │
│        (Output SAMA untuk semua bank!)                       │
│                                                              │
│  Columns:                                                    │
│  - Tanggal Transaksi                                         │
│  - Tanggal Posting                                           │
│  - Keterangan                                                │
│  - Tipe Transaksi                                            │
│  - No Referensi                                              │
│  - Debit                                                     │
│  - Kredit                                                    │
│  - Saldo                                                     │
│  - Bank                                                      │
│  - No Rekening                                               │
│  - Nama Pemegang                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Struktur File

```
backend/
├── bank_adapters/
│   ├── __init__.py                 # Export semua adapters
│   ├── base.py                     # Base class & StandardizedTransaction
│   ├── detector.py                 # Auto-detect bank
│   │
│   ├── mandiri_v1.py              # Adapter Bank Mandiri V1
│   ├── mufg.py                    # Adapter MUFG Bank
│   ├── permata.py                 # Adapter Permata Bank
│   ├── bni_v1.py                  # Adapter BNI V1
│   ├── bri.py                     # Adapter BRI
│   ├── bca_syariah.py             # Adapter BCA Syariah
│   ├── mandiri_v2.py              # Adapter Bank Mandiri V2
│   ├── bni_v2.py                  # Adapter BNI V2
│   └── bsi_syariah.py             # Adapter BSI Syariah
│
├── utils/
│   └── bank_statement_processor.py  # Main processor yang gunakan adapters
│
└── routers/
    └── documents.py                 # Update endpoint untuk multi-bank
```

---

## 💻 Implementasi Detail

### 1. StandardizedTransaction (Format Output Standar)

```python
@dataclass
class StandardizedTransaction:
    """
    Format STANDAR untuk SEMUA bank
    Setiap adapter harus convert ke format ini
    """
    # Tanggal
    transaction_date: datetime         # Wajib
    posting_date: Optional[datetime]   # Optional
    effective_date: Optional[datetime] # Optional

    # Detail Transaksi
    description: str = ""              # Keterangan/Remark/Uraian
    transaction_type: str = ""         # Jenis transaksi
    reference_number: str = ""         # No referensi/Cheque/TrxId

    # Jumlah (DECIMAL untuk akurasi)
    debit: Decimal = Decimal('0.00')
    credit: Decimal = Decimal('0.00')
    balance: Decimal = Decimal('0.00')

    # Metadata
    branch_code: str = ""              # Kode cabang
    teller: str = ""                   # Teller (untuk BRI)
    additional_info: str = ""          # Info tambahan

    # Info Bank & Account
    bank_name: str = ""
    account_number: str = ""
    account_holder: str = ""

    # Raw data (untuk debugging)
    raw_data: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Output EXCEL yang SAMA untuk semua bank"""
        return {
            'Tanggal Transaksi': self.transaction_date.strftime('%d/%m/%Y'),
            'Tanggal Posting': self.posting_date.strftime('%d/%m/%Y') if self.posting_date else '',
            'Keterangan': self.description,
            'Tipe Transaksi': self.transaction_type,
            'No Referensi': self.reference_number,
            'Debit': float(self.debit),
            'Kredit': float(self.credit),
            'Saldo': float(self.balance),
            'Cabang': self.branch_code,
            'Info Tambahan': self.additional_info,
            'Bank': self.bank_name,
            'No Rekening': self.account_number,
            'Nama Pemegang': self.account_holder,
        }
```

### 2. Base Adapter (Template untuk semua bank)

```python
class BaseBankAdapter(ABC):
    """
    Base class yang HARUS diimplementasi oleh setiap bank
    """

    # Identitas bank
    BANK_NAME = "Unknown Bank"
    BANK_CODE = "UNKNOWN"

    # Keywords untuk auto-detection
    DETECTION_KEYWORDS = []

    @abstractmethod
    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """
        Parse OCR result → StandardizedTransaction
        WAJIB implement!
        """
        pass

    @abstractmethod
    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract nomor rekening, nama, periode
        WAJIB implement!
        """
        pass

    def detect(self, ocr_text: str) -> bool:
        """
        Check apakah ini bank yang tepat
        """
        for keyword in self.DETECTION_KEYWORDS:
            if keyword.upper() in ocr_text.upper():
                return True
        return False

    # Helper methods yang sudah disediakan:
    def clean_amount(self, amount_str: str) -> Decimal:
        """Handle: 1.000,00 atau 1,000.00"""
        ...

    def parse_date(self, date_str: str) -> datetime:
        """Parse berbagai format tanggal"""
        ...

    def to_excel_format(self) -> List[Dict[str, Any]]:
        """Convert semua transaksi ke Excel"""
        return [trans.to_dict() for trans in self.transactions]
```

### 3. Contoh Implementasi - Bank Mandiri V1

```python
class MandiriV1Adapter(BaseBankAdapter):
    """
    Bank Mandiri V1: Posting Date | Remark | Reference No | Debit | Credit | Balance
    """

    BANK_NAME = "Bank Mandiri"
    BANK_CODE = "MANDIRI_V1"

    DETECTION_KEYWORDS = [
        "PT BANK MANDIRI",
        "BANK MANDIRI (PERSERO)",
        "POSTING DATE",
        "REMARK",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """Parse Mandiri V1 format"""
        self.account_info = self.extract_account_info(ocr_result)

        # Parse dari table
        for table in ocr_result.get('tables', []):
            for row in table['rows'][1:]:  # Skip header
                cells = row['cells']

                transaction = StandardizedTransaction(
                    transaction_date=self.parse_date(cells[0]['text']),
                    posting_date=self.parse_date(cells[0]['text']),
                    description=cells[1]['text'],  # Remark
                    reference_number=cells[2]['text'],
                    debit=self.clean_amount(cells[3]['text']),
                    credit=self.clean_amount(cells[4]['text']),
                    balance=self.clean_amount(cells[5]['text']),
                    bank_name=self.BANK_NAME,
                    account_number=self.account_info['account_number'],
                    account_holder=self.account_info['account_holder'],
                )

                self.transactions.append(transaction)

        return self.transactions

    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """Extract info rekening Mandiri"""
        text = self.extract_text_from_ocr(ocr_result)

        # Extract account number: 123-45-67890123-4
        acc_match = re.search(r'(\d{3}-\d{2}-\d{8,11}-\d)', text)

        return {
            'account_number': acc_match.group(1) if acc_match else '',
            'account_holder': ...,  # Extract name
            'bank_name': self.BANK_NAME,
        }
```

### 4. Bank Detector (Auto-Detect Bank)

```python
class BankDetector:
    """
    Auto-detect bank dari OCR result
    """

    # Registry semua adapters
    ADAPTERS = [
        MandiriV1Adapter,
        MandiriV2Adapter,
        MufgBankAdapter,
        PermataBankAdapter,
        BniV1Adapter,
        BniV2Adapter,
        BriAdapter,
        BcaSyariahAdapter,
        BsiSyariahAdapter,
    ]

    @classmethod
    def detect(cls, ocr_result: Dict[str, Any]) -> Optional[BaseBankAdapter]:
        """
        Auto-detect bank dan return adapter yang sesuai

        Returns:
            Instance of specific BankAdapter atau None
        """
        # Extract text untuk detection
        text = cls._extract_text(ocr_result)

        # Try setiap adapter
        for adapter_class in cls.ADAPTERS:
            adapter = adapter_class()
            if adapter.detect(text):
                print(f"✓ Detected: {adapter.BANK_NAME} ({adapter.BANK_CODE})")
                return adapter

        print("✗ Bank tidak terdeteksi! Gunakan generic adapter.")
        return None

    @classmethod
    def detect_bank_name(cls, ocr_result: Dict[str, Any]) -> str:
        """Quick detect bank name saja (untuk logging)"""
        adapter = cls.detect(ocr_result)
        return adapter.BANK_NAME if adapter else "Unknown Bank"
```

---

## 🔧 Mapping Detail Setiap Bank

### Bank 1: Mandiri V1

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Posting Date | transaction_date & posting_date |
| Remark | description |
| Reference No | reference_number |
| Debit | debit |
| Credit | credit |
| Balance | balance |

### Bank 2: MUFG Bank

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Booking Date (Value Date) | transaction_date |
| Value Date | effective_date |
| Debit | debit |
| Credit | credit |
| Opening/Closing Balance | balance |
| Transaction Type | transaction_type |
| Customer Reference | reference_number |
| Bank Reference | additional_info |
| Detail Information | description |

### Bank 3: Permata Bank

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Post Date | posting_date |
| Eff Date | transaction_date & effective_date |
| Transaction Code | transaction_type |
| Cheque Number | reference_number (jika ada) |
| Ref No | reference_number |
| Customer No | additional_info |
| Description | description |
| Debit | debit |
| Credit | credit |
| Total | balance |

### Bank 4: BNI V1

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Tgl Trans | transaction_date |
| Uraian | description |
| Debet | debit |
| Kredit | credit |
| Saldo | balance |

### Bank 5: BRI

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Tanggal Transaksi | transaction_date |
| Uraian Transaksi | description |
| Teller | teller |
| Debet | debit |
| Kredit | credit |
| Saldo | balance |

### Bank 6: BCA Syariah (Landscape)

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Tanggal Efektif | effective_date |
| Tanggal Transaksi | transaction_date |
| Jam Input | additional_info (concat) |
| Kode Transaksi | transaction_type |
| Keterangan | description |
| Keterangan Tambahan | description (concat) |
| D/C | (parse untuk debit/credit) |
| Nominal | debit atau credit (tergantung D/C) |
| Saldo | balance |
| Nomor Referensi | reference_number |
| Kode Cabang | branch_code |

**Special handling untuk D/C:**
- D = Debit → nominal masuk ke `debit`
- C = Credit → nominal masuk ke `credit`

### Bank 7: Mandiri V2

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Nama | account_holder |
| Nomer Rekening | account_number |
| Tanggal Transaksi | transaction_date |
| Ket. Kode Transaksi | transaction_type |
| Jenis Trans | transaction_type (concat) |
| Remark | description |
| Amount | debit atau credit (parse dari context) |
| Saldo | balance |

### Bank 8: BNI V2

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| Posting Date | posting_date |
| Effective Date | transaction_date & effective_date |
| Branch | branch_code |
| Journal | reference_number |
| Transaction Description | description |
| Amount | (parse dari DB/CR) |
| DB/CR | (parse untuk debit/credit) |
| Balance | balance |

**Special handling untuk DB/CR:**
- DB = Debit → amount masuk ke `debit`
- CR = Credit → amount masuk ke `credit`

### Bank 9: BSI Syariah

| Field Bank | Mapping ke Standard |
|------------|-------------------|
| TrxId | reference_number |
| Tanggal | transaction_date |
| Trx Time | additional_info |
| D/K | (parse untuk debit/kredit) |
| Mutasi | debit atau credit (tergantung D/K) |
| Saldo | balance |
| Keterangan | description |

**Special handling untuk D/K:**
- D = Debit → mutasi masuk ke `debit`
- K = Kredit → mutasi masuk ke `credit`

---

## 📊 Output Excel Standar (SAMA untuk Semua Bank!)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ REKENING KORAN - [BANK NAME]                                                │
│ No Rekening: [ACCOUNT_NUMBER]                                               │
│ Nama: [ACCOUNT_HOLDER]                                                      │
│ Periode: [START_DATE] s/d [END_DATE]                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│ Tanggal     │ Tgl      │ Keterangan        │ Tipe    │ No Ref  │ Debit     │
│ Transaksi   │ Posting  │                   │ Trans   │         │           │
├─────────────┼──────────┼───────────────────┼─────────┼─────────┼───────────┤
│ 01/01/2025  │01/01/2025│ Transfer Masuk    │ Transfer│ T001    │         - │
│ 02/01/2025  │02/01/2025│ Tarik Tunai ATM   │ ATM     │ A002    │   500,000 │
│ 03/01/2025  │03/01/2025│ Pembayaran Utils  │ Payment │ P003    │   250,000 │
└─────────────┴──────────┴───────────────────┴─────────┴─────────┴───────────┘

│ Kredit      │ Saldo        │ Cabang │ Info Tambahan │ Bank         │
│             │              │        │               │              │
├─────────────┼──────────────┼────────┼───────────────┼──────────────┤
│  1,000,000  │  1,000,000   │  0001  │               │ Bank Mandiri │
│         -   │    500,000   │  0001  │ ATM BNI       │ Bank Mandiri │
│         -   │    250,000   │  0001  │ PLN           │ Bank Mandiri │
└─────────────┴──────────────┴────────┴───────────────┴──────────────┘
```

**Kolom Excel (Sama untuk semua bank):**
1. Tanggal Transaksi
2. Tanggal Posting
3. Keterangan
4. Tipe Transaksi
5. No Referensi
6. Debit
7. Kredit
8. Saldo
9. Cabang
10. Info Tambahan
11. Bank
12. No Rekening
13. Nama Pemegang

---

## 🚀 Cara Pakai

### 1. Upload & Auto-Detect

```python
from bank_adapters import BankDetector

# User upload rekening koran
ocr_result = google_document_ai.process_document(pdf_file)

# Auto-detect bank
adapter = BankDetector.detect(ocr_result)

if adapter:
    # Parse transaksi
    transactions = adapter.parse(ocr_result)

    # Export ke Excel (format SAMA!)
    excel_data = adapter.to_excel_format()

    # Get summary
    summary = adapter.get_summary()
    print(f"Bank: {summary['bank_name']}")
    print(f"Total Transaksi: {summary['transaction_count']}")
    print(f"Total Debit: Rp {summary['total_debit']:,.2f}")
    print(f"Total Credit: Rp {summary['total_credit']:,.2f}")
```

### 2. Manual Specify Bank

```python
from bank_adapters import MandiriV1Adapter, MufgBankAdapter

# Jika user tau ini Bank Mandiri
adapter = MandiriV1Adapter()
transactions = adapter.parse(ocr_result)

# Atau MUFG Bank
adapter = MufgBankAdapter()
transactions = adapter.parse(ocr_result)
```

### 3. Export ke Excel

```python
import pandas as pd

# Get data dalam format Excel
excel_data = adapter.to_excel_format()

# Convert ke DataFrame
df = pd.DataFrame(excel_data)

# Export ke Excel dengan formatting
with pd.ExcelWriter('rekening_koran.xlsx', engine='openpyxl') as writer:
    # Summary sheet
    summary_df = pd.DataFrame([adapter.get_summary()])
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    # Transactions sheet
    df.to_excel(writer, sheet_name='Transaksi', index=False)

    # Format numbers
    workbook = writer.book
    worksheet = writer.sheets['Transaksi']

    # Format currency columns
    currency_format = workbook.add_format({'num_format': '#,##0.00'})
    worksheet.set_column('F:H', 15, currency_format)  # Debit, Kredit, Saldo
```

---

## ✅ Testing Strategy

### 1. Unit Test per Bank

```python
# test_mandiri_v1.py
def test_mandiri_v1_parsing():
    """Test Mandiri V1 adapter"""
    adapter = MandiriV1Adapter()

    # Load sample OCR result
    ocr_result = load_sample('mandiri_v1_sample.json')

    # Parse
    transactions = adapter.parse(ocr_result)

    # Assertions
    assert len(transactions) > 0
    assert adapter.BANK_NAME == "Bank Mandiri"
    assert all(t.bank_name == "Bank Mandiri" for t in transactions)
    assert all(isinstance(t.debit, Decimal) for t in transactions)

# test_mufg.py, test_permata.py, dst...
```

### 2. Integration Test

```python
def test_all_banks_same_output():
    """Test bahwa semua bank output format yang SAMA"""

    banks = [
        ('mandiri_v1', MandiriV1Adapter),
        ('mufg', MufgBankAdapter),
        ('permata', PermataBankAdapter),
        # ... semua bank
    ]

    for bank_name, adapter_class in banks:
        adapter = adapter_class()
        ocr_result = load_sample(f'{bank_name}_sample.json')
        transactions = adapter.parse(ocr_result)

        # Test output Excel
        excel_data = adapter.to_excel_format()

        # Semua harus punya kolom yang sama
        expected_columns = [
            'Tanggal Transaksi', 'Tanggal Posting', 'Keterangan',
            'Tipe Transaksi', 'No Referensi', 'Debit', 'Kredit',
            'Saldo', 'Cabang', 'Info Tambahan', 'Bank',
            'No Rekening', 'Nama Pemegang'
        ]

        assert list(excel_data[0].keys()) == expected_columns
```

### 3. Detection Test

```python
def test_bank_detection():
    """Test auto-detection"""

    test_cases = [
        ('mandiri_v1_sample.json', 'MANDIRI_V1'),
        ('mufg_sample.json', 'MUFG'),
        ('permata_sample.json', 'PERMATA'),
        # ... dst
    ]

    for sample_file, expected_code in test_cases:
        ocr_result = load_sample(sample_file)
        adapter = BankDetector.detect(ocr_result)

        assert adapter is not None
        assert adapter.BANK_CODE == expected_code
```

---

## 🎯 Keuntungan System Ini

### 1. **Maintenance Mudah**
- Setiap bank punya file terpisah
- Ganti 1 bank tidak ganggu yang lain
- Clear separation of concerns

### 2. **Easy to Extend**
- Tambah bank baru? Copy template, sesuaikan parsing
- Tidak perlu ubah core system

### 3. **Consistent Output**
- Semua bank → format Excel SAMA
- User tidak bingung
- Easy untuk reporting & reconciliation

### 4. **Auto-Detection**
- User tidak perlu pilih bank manual
- System detect otomatis dari keywords
- Fallback ke generic adapter jika tidak kenal

### 5. **Type Safety**
- Pakai Decimal untuk currency (no floating point errors)
- Strict typing dengan dataclass
- Less bugs di production

### 6. **Testable**
- Each adapter can be tested independently
- Mock OCR results untuk testing
- Easy to add test cases

---

## 📝 Template untuk Tambah Bank Baru

```python
# new_bank.py
from typing import Dict, Any, List
from .base import BaseBankAdapter, StandardizedTransaction

class NewBankAdapter(BaseBankAdapter):
    """
    Adapter untuk [BANK NAME]
    Format: [describe format here]
    """

    BANK_NAME = "[Bank Name]"
    BANK_CODE = "BANKCODE"

    DETECTION_KEYWORDS = [
        "[KEYWORD 1]",
        "[KEYWORD 2]",
    ]

    def parse(self, ocr_result: Dict[str, Any]) -> List[StandardizedTransaction]:
        """Parse OCR result"""
        self.account_info = self.extract_account_info(ocr_result)

        # TODO: Parse logic here
        # Loop through tables/text
        # Create StandardizedTransaction objects

        return self.transactions

    def extract_account_info(self, ocr_result: Dict[str, Any]) -> Dict[str, str]:
        """Extract account info"""
        # TODO: Extract account number, holder name, etc
        return {
            'account_number': '',
            'account_holder': '',
        }
```

Lalu tambahkan ke `__init__.py` dan `detector.py`!

---

## 🚧 Next Steps

1. ✅ Create base adapter & StandardizedTransaction
2. ⏳ Implement 9 bank adapters
3. ⏳ Create BankDetector
4. ⏳ Update main processor
5. ⏳ Update API endpoints
6. ⏳ Testing dengan real samples
7. ⏳ Deploy & monitor

---

Dengan system ini, lu bisa handle **ratusan bank** kalau perlu! Tinggal tambah adapter baru, output tetap SAMA dan RAPIH! 🚀
