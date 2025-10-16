# Modul Rekonsiliasi Pajak - Desain Arsitektur

## 🎯 Ringkasan Modul

**Nama Modul:** Rekonsiliasi Pajak (Tax Reconciliation)

**Tujuan:** Mencocokkan dan merekonsiliasi transaksi dari Rekening Koran dengan Faktur Pajak secara otomatis untuk mengidentifikasi perbedaan, item yang hilang, dan menghasilkan laporan rekonsiliasi yang lengkap.

**Mirip dengan:** Aplikasi Recon+ tapi terintegrasi langsung ke dalam Doc Scan AI

---

## 🏗️ Arsitektur Sistem

### 1. Skema Database

```sql
-- Tabel Proyek Rekonsiliasi
CREATE TABLE reconciliation_projects (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    status ENUM('draft', 'processing', 'completed', 'failed') DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,

    -- Statistik
    total_bank_transactions INT DEFAULT 0,
    total_invoices INT DEFAULT 0,
    matched_count INT DEFAULT 0,
    unmatched_bank_count INT DEFAULT 0,
    unmatched_invoice_count INT DEFAULT 0,
    discrepancy_count INT DEFAULT 0,

    -- Konfigurasi
    matching_tolerance_amount DECIMAL(10, 2) DEFAULT 0.00,
    matching_date_range_days INT DEFAULT 7,
    auto_match_enabled BOOLEAN DEFAULT TRUE,

    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
);

-- Tabel Transaksi Bank (dari Rekening Koran)
CREATE TABLE recon_bank_transactions (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    document_id VARCHAR(36), -- Referensi ke dokumen yang di-scan

    -- Detail Transaksi
    transaction_date DATE NOT NULL,
    posting_date DATE,
    description TEXT,
    reference_number VARCHAR(100),
    debit_amount DECIMAL(15, 2) DEFAULT 0.00,
    credit_amount DECIMAL(15, 2) DEFAULT 0.00,
    balance DECIMAL(15, 2),

    -- Status Pencocokan
    match_status ENUM('unmatched', 'matched', 'partial', 'discrepancy') DEFAULT 'unmatched',
    matched_invoice_id VARCHAR(36) NULL,
    match_confidence DECIMAL(5, 2), -- 0.00 sampai 100.00
    match_method ENUM('auto', 'manual', 'ai_suggested') NULL,
    matched_at TIMESTAMP NULL,
    matched_by VARCHAR(36) NULL,

    -- Ekstraksi AI
    extracted_vendor_name VARCHAR(255),
    extracted_invoice_number VARCHAR(100),
    ai_confidence DECIMAL(5, 2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    INDEX idx_project_id (project_id),
    INDEX idx_transaction_date (transaction_date),
    INDEX idx_match_status (match_status),
    INDEX idx_matched_invoice_id (matched_invoice_id)
);

-- Tabel Faktur Pajak
CREATE TABLE recon_tax_invoices (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    document_id VARCHAR(36), -- Referensi ke dokumen yang di-scan

    -- Detail Faktur
    invoice_number VARCHAR(100) NOT NULL,
    invoice_date DATE NOT NULL,
    tax_invoice_serial VARCHAR(50),
    vendor_name VARCHAR(255),
    vendor_npwp VARCHAR(20),
    customer_name VARCHAR(255),
    customer_npwp VARCHAR(20),

    -- Detail Keuangan
    dpp_amount DECIMAL(15, 2) NOT NULL, -- Dasar Pengenaan Pajak
    ppn_amount DECIMAL(15, 2) NOT NULL, -- Pajak Pertambahan Nilai (11%)
    total_amount DECIMAL(15, 2) NOT NULL, -- DPP + PPN

    -- Status Pencocokan
    match_status ENUM('unmatched', 'matched', 'partial', 'discrepancy') DEFAULT 'unmatched',
    matched_bank_transaction_id VARCHAR(36) NULL,
    match_confidence DECIMAL(5, 2),
    match_method ENUM('auto', 'manual', 'ai_suggested') NULL,
    matched_at TIMESTAMP NULL,
    matched_by VARCHAR(36) NULL,

    -- Ekstraksi AI
    ai_confidence DECIMAL(5, 2),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    INDEX idx_project_id (project_id),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_invoice_date (invoice_date),
    INDEX idx_match_status (match_status),
    INDEX idx_matched_bank_transaction_id (matched_bank_transaction_id)
);

-- Tabel Pencocokan (Many-to-Many untuk kasus kompleks)
CREATE TABLE recon_matches (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,

    -- Detail Pencocokan
    bank_transaction_id VARCHAR(36),
    tax_invoice_id VARCHAR(36),
    match_type ENUM('one_to_one', 'one_to_many', 'many_to_one', 'split') NOT NULL,
    match_confidence DECIMAL(5, 2) NOT NULL,
    match_method ENUM('auto', 'manual', 'ai_suggested') NOT NULL,

    -- Jumlah
    bank_amount DECIMAL(15, 2),
    invoice_amount DECIMAL(15, 2),
    difference_amount DECIMAL(15, 2),

    -- Kriteria Pencocokan yang Digunakan
    matched_by_amount BOOLEAN DEFAULT FALSE,
    matched_by_date BOOLEAN DEFAULT FALSE,
    matched_by_reference BOOLEAN DEFAULT FALSE,
    matched_by_vendor BOOLEAN DEFAULT FALSE,

    -- Status
    status ENUM('active', 'disputed', 'confirmed', 'rejected') DEFAULT 'active',
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (bank_transaction_id) REFERENCES recon_bank_transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (tax_invoice_id) REFERENCES recon_tax_invoices(id) ON DELETE CASCADE,
    INDEX idx_project_id (project_id),
    INDEX idx_match_type (match_type),
    INDEX idx_status (status)
);

-- Tabel Log Perbedaan
CREATE TABLE recon_discrepancies (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    match_id VARCHAR(36),

    discrepancy_type ENUM(
        'amount_mismatch',
        'missing_invoice',
        'missing_bank_transaction',
        'date_mismatch',
        'duplicate_entry',
        'vendor_mismatch'
    ) NOT NULL,

    severity ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    description TEXT NOT NULL,
    expected_value VARCHAR(255),
    actual_value VARCHAR(255),
    difference_amount DECIMAL(15, 2),

    -- Resolusi
    status ENUM('open', 'investigating', 'resolved', 'ignored') DEFAULT 'open',
    resolution_notes TEXT,
    resolved_at TIMESTAMP NULL,
    resolved_by VARCHAR(36) NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (match_id) REFERENCES recon_matches(id) ON DELETE SET NULL,
    INDEX idx_project_id (project_id),
    INDEX idx_discrepancy_type (discrepancy_type),
    INDEX idx_severity (severity),
    INDEX idx_status (status)
);
```

---

## 🧠 Algoritma Pencocokan

### Logika Auto-Matching (Pencocokan Multi-Kriteria)

```python
class ReconciliationMatcher:
    """
    Mesin pencocokan berbasis AI untuk rekonsiliasi pajak
    Menggunakan multiple criteria dengan sistem scoring berbobot
    """

    def __init__(self, tolerance_amount: Decimal = Decimal('0.00'),
                 date_range_days: int = 7):
        self.tolerance_amount = tolerance_amount
        self.date_range_days = date_range_days

        # Bobot pencocokan
        self.weights = {
            'exact_amount': 40,      # 40 poin untuk jumlah yang sama persis
            'exact_date': 25,        # 25 poin untuk tanggal yang sama persis
            'reference_match': 20,   # 20 poin untuk nomor referensi yang cocok
            'vendor_match': 15       # 15 poin untuk kemiripan nama vendor
        }

        # Threshold confidence minimum
        self.min_confidence = 70.0  # 70% minimum untuk auto-match

    async def match_transaction(
        self,
        bank_transaction: BankTransaction,
        available_invoices: List[TaxInvoice]
    ) -> List[MatchCandidate]:
        """
        Mencari faktur yang paling cocok untuk transaksi bank
        Mengembalikan daftar kandidat yang diurutkan berdasarkan skor confidence
        """
        candidates = []

        for invoice in available_invoices:
            score = 0
            match_details = {}

            # 1. Pencocokan Jumlah (40 poin)
            amount_diff = abs(bank_transaction.credit_amount - invoice.total_amount)
            if amount_diff == 0:
                score += self.weights['exact_amount']
                match_details['amount_match'] = 'exact'
            elif amount_diff <= self.tolerance_amount:
                score += self.weights['exact_amount'] * 0.8
                match_details['amount_match'] = 'within_tolerance'
            elif amount_diff <= invoice.total_amount * 0.05:  # Toleransi 5%
                score += self.weights['exact_amount'] * 0.5
                match_details['amount_match'] = 'close'

            # 2. Pencocokan Tanggal (25 poin)
            date_diff = abs((invoice.invoice_date - bank_transaction.transaction_date).days)
            if date_diff == 0:
                score += self.weights['exact_date']
                match_details['date_match'] = 'exact'
            elif date_diff <= self.date_range_days:
                # Linear decay dalam range
                decay_factor = 1 - (date_diff / self.date_range_days)
                score += self.weights['exact_date'] * decay_factor
                match_details['date_match'] = f'dalam_{date_diff}_hari'

            # 3. Pencocokan Nomor Referensi (20 poin)
            if self._fuzzy_match(bank_transaction.extracted_invoice_number,
                                invoice.invoice_number):
                score += self.weights['reference_match']
                match_details['reference_match'] = True

            # 4. Pencocokan Nama Vendor (15 poin)
            vendor_similarity = self._calculate_string_similarity(
                bank_transaction.extracted_vendor_name,
                invoice.vendor_name
            )
            score += self.weights['vendor_match'] * vendor_similarity
            match_details['vendor_similarity'] = vendor_similarity

            # Hitung confidence akhir
            confidence = (score / 100) * 100  # Konversi ke persentase

            if confidence >= self.min_confidence:
                candidates.append(MatchCandidate(
                    invoice=invoice,
                    confidence=confidence,
                    match_details=match_details,
                    amount_difference=amount_diff
                ))

        # Urutkan berdasarkan confidence (tertinggi dulu)
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates

    def _fuzzy_match(self, str1: str, str2: str, threshold: float = 0.85) -> bool:
        """Pencocokan string fuzzy menggunakan Levenshtein distance"""
        if not str1 or not str2:
            return False

        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, str1.upper(), str2.upper()).ratio()
        return similarity >= threshold

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Menghitung rasio kemiripan antara dua string (0.0 sampai 1.0)"""
        if not str1 or not str2:
            return 0.0

        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1.upper(), str2.upper()).ratio()
```

---

## 🚀 API Endpoints

### Manajemen Proyek

```python
# POST /api/reconciliation/projects
# Buat proyek rekonsiliasi baru
{
    "project_name": "Rekonsiliasi Pajak Q1 2025",
    "description": "Mencocokkan transaksi bank dengan faktur untuk Q1",
    "matching_tolerance_amount": 0.00,
    "matching_date_range_days": 7,
    "auto_match_enabled": true
}

# GET /api/reconciliation/projects
# Tampilkan semua proyek (dengan pagination dan filter)

# GET /api/reconciliation/projects/{project_id}
# Dapatkan detail proyek beserta statistik

# PATCH /api/reconciliation/projects/{project_id}
# Update pengaturan proyek

# DELETE /api/reconciliation/projects/{project_id}
# Hapus proyek dan semua data terkait
```

### Import Data

```python
# POST /api/reconciliation/projects/{project_id}/import/bank-statements
# Upload dokumen rekening koran (import batch)
# Otomatis ekstrak transaksi menggunakan pipeline OCR yang sudah ada

# POST /api/reconciliation/projects/{project_id}/import/tax-invoices
# Upload dokumen faktur pajak (import batch)
# Otomatis ekstrak data faktur menggunakan pipeline OCR yang sudah ada

# GET /api/reconciliation/projects/{project_id}/data
# Lihat transaksi bank dan faktur yang sudah diimport
# Query params: type=bank|invoice, status=matched|unmatched, page, limit
```

### Operasi Pencocokan

```python
# POST /api/reconciliation/projects/{project_id}/match/auto
# Jalankan algoritma pencocokan otomatis pada semua item yang belum dicocokkan
# Returns: jumlah match yang ditemukan, distribusi confidence

# POST /api/reconciliation/projects/{project_id}/match/manual
# Cocokkan transaksi bank dengan faktur secara manual
{
    "bank_transaction_id": "uuid",
    "tax_invoice_id": "uuid",
    "notes": "Manual match - pembayaran parsial"
}

# GET /api/reconciliation/projects/{project_id}/match/suggestions
# Dapatkan saran pencocokan dari AI dengan skor confidence
# Query params: bank_transaction_id atau tax_invoice_id

# DELETE /api/reconciliation/projects/{project_id}/match/{match_id}
# Batalkan pencocokan yang sudah dilakukan sebelumnya
```

### Analisis & Laporan

```python
# GET /api/reconciliation/projects/{project_id}/analysis
# Dapatkan analisis komprehensif:
# - Statistik pencocokan
# - Ringkasan perbedaan
# - Breakdown item yang tidak cocok
# - Ringkasan rekonsiliasi jumlah

# GET /api/reconciliation/projects/{project_id}/discrepancies
# Tampilkan semua perbedaan dengan filter
# Query params: type, severity, status, page, limit

# POST /api/reconciliation/projects/{project_id}/discrepancies/{discrepancy_id}/resolve
# Tandai perbedaan sebagai terselesaikan
{
    "resolution_notes": "Dikonfirmasi dengan tim accounting - perbedaan waktu"
}

# GET /api/reconciliation/projects/{project_id}/export
# Export laporan rekonsiliasi
# Query params: format=excel|pdf|csv
# Returns laporan komprehensif dengan:
# - Transaksi yang cocok
# - Transaksi bank yang tidak cocok
# - Faktur yang tidak cocok
# - Perbedaan
# - Statistik ringkasan
```

---

## 💻 Komponen UI Frontend

### 1. Dashboard Proyek

```
┌─────────────────────────────────────────────────────────────┐
│  Proyek Rekonsiliasi Pajak                       [+ Baru]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Rekonsiliasi Pajak Q1 2025                 [Lihat]      │
│     Status: Selesai                                          │
│     ✓ 156/160 Cocok (97.5%)                                 │
│     ⚠️  4 Perbedaan                                          │
│     Dibuat: 15 Jan 2025                                      │
│                                                              │
│  📊 Pencocokan Bank-Faktur Feb 2025            [Lihat]      │
│     Status: Sedang Diproses                                  │
│     ✓ 45/89 Cocok (50.6%)                                   │
│     ⏳ Memproses...                                          │
│     Dibuat: 1 Feb 2025                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Tampilan Detail Proyek

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Rekonsiliasi Pajak Q1 2025          [Pengaturan] [⋮]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Trans Bank   │  │ Faktur Pajak │  │ Tercocok     │     │
│  │     160      │  │     158      │  │     156      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Belum Cocok  │  │ Perbedaan    │  │ Akurasi      │     │
│  │      4       │  │      4       │  │    97.5%     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  [Import Rek. Koran] [Import Faktur Pajak]                  │
│  [Jalankan Auto-Match] [Export Laporan]                     │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  Tab: [Tercocok] [Bank Belum Cocok] [Faktur Belum Cocok]   │
│       [Perbedaan] [Semua Transaksi]                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Transaksi Tercocok (156)                      [Filter ▼]   │
│  ┌────────────────────────────────────────────────────────┐│
│  │ Tanggal    Jumlah Bank  No Faktur  Confidence  Aksi   ││
│  ├────────────────────────────────────────────────────────┤│
│  │ 05/01/2025 Rp 5.550.000 FP-001/25     98%    [Lihat] ││
│  │ ✓ Auto-match | Vendor: PT ABC | DPP: 5.000.000       ││
│  │                                                         ││
│  │ 07/01/2025 Rp 3.330.000 FP-002/25     95%    [Lihat] ││
│  │ ✓ Auto-match | Vendor: CV XYZ | DPP: 3.000.000       ││
│  └────────────────────────────────────────────────────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3. Interface Pencocokan (Manual Match)

```
┌─────────────────────────────────────────────────────────────┐
│  Cocokkan Transaksi                                  [×]    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🏦 Transaksi Bank                                           │
│  Tanggal: 10 Jan 2025                                       │
│  Jumlah: Rp 8.880.000                                       │
│  Keterangan: Transfer dari PT SEJAHTERA                      │
│  Referensi: TRX-20250110-001                                │
│                                                              │
│  ────────────────────────────────────────────────────────   │
│                                                              │
│  🧾 Saran Pencocokan (3)                                     │
│                                                              │
│  ● FP-010/2025 - PT SEJAHTERA ABADI         [Pilih]        │
│    Tanggal: 09/01/25 | Jumlah: Rp 8.880.000                │
│    Confidence: 96% ⭐⭐⭐⭐⭐                                   │
│    ✓ Jumlah sama | ✓ Tanggal dalam 1 hari | ✓ Vendor cocok│
│                                                              │
│  ○ FP-011/2025 - PT SEJAHTERA JAYA          [Pilih]        │
│    Tanggal: 08/01/25 | Jumlah: Rp 8.800.000                │
│    Confidence: 78% ⭐⭐⭐⭐                                     │
│    ~ Jumlah mendekati (beda: 80rb) | ✓ Vendor mirip        │
│                                                              │
│  ○ FP-009/2025 - PT MAKMUR SEJAHTERA        [Pilih]        │
│    Tanggal: 10/01/25 | Jumlah: Rp 8.000.000                │
│    Confidence: 65% ⭐⭐⭐                                      │
│    ~ Selisih jumlah: 880rb | ✓ Tanggal sama                │
│                                                              │
│  [Cari Faktur Lain]                                         │
│                                                              │
│  Catatan (opsional):                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│                            [Batal] [Konfirmasi Pencocokan]  │
└─────────────────────────────────────────────────────────────┘
```

### 4. Tampilan Detail Perbedaan

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Detail Perbedaan                                 [×]    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Tipe: Perbedaan Jumlah                                     │
│  Tingkat: Sedang                                            │
│  Status: Terbuka                                            │
│                                                              │
│  🏦 Transaksi Bank                                           │
│  Tanggal: 15 Jan 2025                                       │
│  Jumlah: Rp 11.100.000                                      │
│  Keterangan: Pembayaran Invoice #INV-2025-001               │
│                                                              │
│  🧾 Faktur yang Dicocokkan                                   │
│  Faktur: FP-015/2025                                        │
│  Tanggal: 14 Jan 2025                                       │
│  Jumlah: Rp 11.000.000                                      │
│  Vendor: PT MAJU BERSAMA                                    │
│                                                              │
│  💰 Selisih: Rp 100.000 (0,91%)                             │
│                                                              │
│  Kemungkinan Penyebab:                                      │
│  • Biaya transfer bank termasuk dalam pembayaran            │
│  • Pembayaran parsial dari saldo sebelumnya                 │
│  • Pembulatan konversi mata uang                            │
│  • Kesalahan input data                                     │
│                                                              │
│  Catatan Resolusi:                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [Tandai Terselesaikan] [Batalkan Match] [Hubungi Support] │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Format Export

### Struktur Export Excel

```
Sheet 1: Ringkasan
┌──────────────────────────────────────────────────┐
│ Laporan Rekonsiliasi Pajak                      │
│ Proyek: Rekonsiliasi Pajak Q1 2025              │
│ Periode: 1 Jan 2025 sampai 31 Mar 2025          │
│ Dibuat: 1 Apr 2025 10:30 WIB                    │
├──────────────────────────────────────────────────┤
│ Statistik:                                       │
│ Total Transaksi Bank:           160             │
│ Total Faktur Pajak:             158             │
│ Berhasil Dicocokkan:            156 (97,5%)     │
│ Transaksi Bank Belum Cocok:       4             │
│ Faktur Belum Cocok:                2             │
│ Perbedaan:                         4             │
│                                                  │
│ Ringkasan Jumlah:                                │
│ Total Kredit Bank:          Rp 1.245.680.000    │
│ Total Jumlah Faktur:        Rp 1.244.500.000    │
│ Selisih:                    Rp     1.180.000    │
│ Selisih %:                           0,09%       │
└──────────────────────────────────────────────────┘

Sheet 2: Transaksi Tercocok
[Tanggal | Jumlah Bank | No Faktur | Jumlah Faktur | Vendor | Confidence | Metode Match]

Sheet 3: Transaksi Bank Belum Cocok
[Tanggal | Jumlah | Keterangan | Referensi | Alasan]

Sheet 4: Faktur Pajak Belum Cocok
[No Faktur | Tanggal | Jumlah | Vendor | Alasan]

Sheet 5: Perbedaan
[Tipe | Jumlah Bank | Jumlah Faktur | Selisih | Tingkat | Status]
```

---

## 🔄 Integrasi dengan Sistem yang Ada

### Gunakan Ulang Komponen yang Sudah Ada

1. **Pipeline OCR** - Sudah berjalan sempurna
   - Gunakan endpoint `/api/documents/process` yang ada untuk ekstrak Rekening Koran
   - Gunakan endpoint `/api/documents/process` yang ada untuk ekstrak Faktur Pajak
   - Tidak perlu menulis ulang logika OCR!

2. **Batch Processing** - Sudah handle 100+ file
   - Gunakan ulang `batch_processor.py` untuk bulk import
   - Import 20 rekening koran + 50 faktur sekaligus

3. **Database** - Tambah tabel baru di samping yang sudah ada
   - Tetap gunakan tabel `documents`, `users`, `processing_results` yang sudah ada
   - Tambah tabel rekonsiliasi baru

4. **AI Smart Mapper** - Sudah ekstrak field secara cerdas
   - Extend untuk ekstrak nama vendor dari keterangan bank
   - Ekstrak referensi faktur dari catatan transaksi

### File Backend Baru yang Perlu Dibuat

```
backend/
├── reconciliation/
│   ├── __init__.py
│   ├── models.py              # Model SQLAlchemy untuk tabel rekon
│   ├── schemas.py             # Schema Pydantic untuk API
│   ├── matcher.py             # Engine algoritma pencocokan
│   ├── analyzer.py            # Analisis statistik
│   └── exporter.py            # Pembuatan laporan
├── routers/
│   └── reconciliation.py      # Route FastAPI
└── alembic/
    └── versions/
        └── xxx_add_reconciliation_tables.py
```

### File Frontend Baru yang Perlu Dibuat

```
src/
├── pages/
│   └── Reconciliation/
│       ├── Dashboard.tsx           # Daftar proyek
│       ├── ProjectDetail.tsx       # Tampilan rekon utama
│       ├── MatchingInterface.tsx   # UI pencocokan manual
│       └── DiscrepancyView.tsx     # Detail perbedaan
├── components/
│   └── Reconciliation/
│       ├── StatCard.tsx
│       ├── TransactionTable.tsx
│       ├── MatchSuggestion.tsx
│       └── ConfidenceScore.tsx
└── api/
    └── reconciliation.ts           # Fungsi API client
```

---

## 🎨 Alur Pengguna

### Workflow Lengkap

```
1. Buat Proyek
   ↓
2. Import Rekening Koran (upload ZIP)
   → OCR ekstrak semua transaksi otomatis
   ↓
3. Import Faktur Pajak (upload ZIP)
   → OCR ekstrak semua data faktur otomatis
   ↓
4. Jalankan Auto-Match
   → AI cocokkan berdasarkan jumlah, tanggal, referensi, vendor
   → Tampilkan skor confidence
   ↓
5. Review Saran
   → Terima match dengan confidence tinggi (>95%)
   → Review match dengan confidence sedang (70-95%)
   → Cocokkan manual untuk item dengan confidence rendah
   ↓
6. Handle Perbedaan
   → Investigasi perbedaan jumlah
   → Selesaikan item yang hilang
   → Tambahkan catatan untuk audit trail
   ↓
7. Export Laporan
   → Excel dengan breakdown detail
   → PDF ringkasan untuk manajemen
   → CSV untuk import ke software accounting
```

---

## 💡 Fitur Pintar

### 1. Enhancement Berbasis AI

```python
# Gunakan GPT-4o untuk pencocokan nama vendor yang cerdas
async def ai_match_vendor_names(bank_description: str, invoice_vendors: List[str]):
    """
    GPT membantu mencocokkan keterangan bank yang berantakan
    dengan nama vendor yang bersih

    Contoh:
    Bank: "TRF DR PT SEJAHTERA ABD TBK CAB JKT"
    Faktur: ["PT SEJAHTERA ABADI", "PT SEJAHTERA JAYA", "CV SEJAHTERA"]
    AI: "PT SEJAHTERA ABADI" (confidence: 92%)
    """
    prompt = f"""
    Cocokkan keterangan transaksi bank ini dengan vendor yang paling mungkin:

    Keterangan bank: {bank_description}

    Vendor yang mungkin:
    {'\n'.join(f'{i+1}. {v}' for i, v in enumerate(invoice_vendors))}

    Kembalikan hasil match terbaik dengan skor confidence (0-100).
    """
    # Gunakan integrasi GPT Smart Mapper yang sudah ada
    return await smart_mapper.query(prompt)
```

### 2. Penanganan Split Transaction

```
Transaksi Bank: Rp 16.650.000
Kemungkinan Match:
  - Faktur A: Rp 11.100.000 (66,7%)
  - Faktur B: Rp  5.550.000 (33,3%)
  Total: Rp 16.650.000 ✓

AI menyarankan: Ini adalah pembayaran gabungan untuk 2 faktur!
Aksi: Buat match tipe "many_to_one"
```

### 3. Tracking Pembayaran Parsial

```
Faktur FP-050/2025: Rp 55.500.000
Pembayaran Bank:
  - 10/01/2025: Rp 27.750.000 (DP 50%)
  - 15/02/2025: Rp 27.750.000 (Pelunasan 50%)
Status: Sebagian cocok → Cocok penuh
```

### 4. Deteksi Duplikat

```
⚠️ Peringatan: Kemungkinan duplikat!
Faktur FP-100/2025 sepertinya cocok dengan:
  - Transaksi bank #1 (20 Jan 2025)
  - Transaksi bank #2 (21 Jan 2025)
Jumlah sama: Rp 11.100.000
Kemungkinan penyebab: Keterlambatan posting bank
```

---

## 🚀 Fase Implementasi

### Fase 1: Pencocokan Inti (2 minggu)
- [ ] Skema database & migrasi
- [ ] CRUD dasar untuk proyek, transaksi, faktur
- [ ] Algoritma auto-match sederhana (jumlah + tanggal saja)
- [ ] Interface pencocokan manual
- [ ] Export Excel dasar

### Fase 2: Pencocokan Pintar (1 minggu)
- [ ] Algoritma pencocokan advanced dengan scoring
- [ ] Pencocokan nama vendor dengan AI
- [ ] Kalkulasi skor confidence
- [ ] UI saran pencocokan
- [ ] Deteksi perbedaan

### Fase 3: Fitur Advanced (1 minggu)
- [ ] Penanganan split transaction
- [ ] Tracking pembayaran parsial
- [ ] Deteksi duplikat
- [ ] Laporan enhanced (PDF + ringkasan)
- [ ] Audit trail & catatan

### Fase 4: Polish & Optimasi (1 minggu)
- [ ] Optimasi performa untuk 1000+ transaksi
- [ ] Filter & pencarian advanced
- [ ] Operasi bulk (bulk match, bulk unmatch)
- [ ] Kustomisasi template export
- [ ] Dokumentasi pengguna

**Total Timeline: 5 minggu untuk implementasi penuh**

---

## 💰 Value Proposition

### Kenapa Ini Lebih Baik dari Recon+

1. **OCR Terintegrasi** - Tidak perlu input manual!
   - Recon+ butuh import CSV (kerja manual)
   - Aplikasi kita: Upload PDF → Auto ekstrak → Auto cocokkan

2. **Berbasis AI** - Pencocokan lebih pintar
   - Fuzzy matching nama vendor
   - Ekstraksi referensi pintar
   - Belajar dari pencocokan Anda

3. **Platform All-in-One**
   - Sudah punya scanning dokumen
   - Sudah punya batch processing
   - Tinggal tambah rekonsiliasi = solusi lengkap

4. **UX Lebih Baik**
   - UI React modern
   - Progress real-time
   - Skor confidence visual

5. **Cost-Effective**
   - Tidak perlu langganan terpisah
   - Gunakan infrastruktur yang sudah ada
   - Biaya marginal: hanya panggilan GPT API

---

## 📈 Tambahan Pricing

### Harga Modul

**Opsi 1: Termasuk dalam Paket Pro**
- Tambahkan Rekonsiliasi sebagai fitur premium
- Paket Pro: Rp 500.000/bulan (semua fitur)

**Opsi 2: Add-On Terpisah**
- Aplikasi Dasar: Rp 300.000/bulan
- Modul Rekonsiliasi: +Rp 150.000/bulan
- Total: Rp 450.000/bulan

**Opsi 3: Berbasis Transaksi**
- Rp 50/transaksi yang cocok
- Contoh: 200 match/bulan = Rp 10.000

**Rekomendasi: Opsi 1** (paling sederhana, nilai terbaik)

---

## 🎯 Metrik Kesuksesan

### KPI untuk Dilacak

1. **Match Rate**: Target 95%+ auto-match
2. **Akurasi**: Target 99%+ pencocokan benar
3. **Penghematan Waktu**:
   - Rekon manual: ~8 jam untuk 100 transaksi
   - Otomatis: ~15 menit
   - **Penghematan: Pengurangan waktu 96,875%**
4. **Kepuasan User**: Skor NPS >50

---

## 🔒 Keamanan & Compliance

### Perlindungan Data

- Semua data rekonsiliasi dienkripsi saat istirahat
- Audit trail untuk semua pencocokan/perubahan manual
- Kontrol akses level pengguna (kepemilikan proyek)
- Retensi data sesuai GDPR (auto-delete setelah 1 tahun)
- Backup sebelum operasi bulk

### Fitur Audit

- Riwayat lengkap semua pencocokan/pembatalan
- Siapa mencocokkan apa dan kapan
- Data OCR asli tetap tersimpan
- Export termasuk audit trail

---

## 📝 Contoh Response API

### Dapatkan Proyek dengan Statistik

```json
{
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "project_name": "Rekonsiliasi Pajak Q1 2025",
  "status": "completed",
  "statistics": {
    "total_bank_transactions": 160,
    "total_tax_invoices": 158,
    "matched_count": 156,
    "match_rate": 97.5,
    "unmatched_bank_count": 4,
    "unmatched_invoice_count": 2,
    "discrepancy_count": 4,
    "total_bank_amount": 1245680000,
    "total_invoice_amount": 1244500000,
    "variance": 1180000,
    "variance_percentage": 0.09
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-04-01T15:45:00Z",
  "completed_at": "2025-04-01T15:45:00Z"
}
```

### Dapatkan Saran Pencocokan

```json
{
  "bank_transaction_id": "abc-123",
  "bank_transaction": {
    "date": "2025-01-10",
    "amount": 8880000,
    "description": "Transfer dari PT SEJAHTERA",
    "reference": "TRX-20250110-001"
  },
  "suggestions": [
    {
      "invoice_id": "inv-456",
      "invoice_number": "FP-010/2025",
      "invoice_date": "2025-01-09",
      "vendor_name": "PT SEJAHTERA ABADI",
      "total_amount": 8880000,
      "confidence": 96.0,
      "match_details": {
        "amount_match": "exact",
        "date_match": "dalam_1_hari",
        "vendor_similarity": 0.92,
        "reference_match": false
      },
      "recommendation": "auto_match"
    },
    {
      "invoice_id": "inv-789",
      "invoice_number": "FP-011/2025",
      "invoice_date": "2025-01-08",
      "vendor_name": "PT SEJAHTERA JAYA",
      "total_amount": 8800000,
      "confidence": 78.0,
      "match_details": {
        "amount_match": "close",
        "amount_difference": 80000,
        "date_match": "dalam_2_hari",
        "vendor_similarity": 0.85
      },
      "recommendation": "manual_review"
    }
  ]
}
```

---

## 🎓 Dokumentasi Pengguna (akan dibuat)

### Topik Bantuan

1. **Memulai dengan Rekonsiliasi Pajak**
2. **Memahami Skor Confidence Pencocokan**
3. **Cara Menangani Perbedaan**
4. **Best Practice untuk Import Dokumen**
5. **Menginterpretasi Laporan Rekonsiliasi**
6. **Troubleshooting Masalah Umum**

---

## ✅ Strategi Testing

### Unit Test

```python
# Test algoritma pencocokan
def test_exact_amount_match():
    """Harus memberikan 100% confidence untuk jumlah + tanggal + vendor yang sama persis"""

def test_partial_amount_match():
    """Harus memberikan 80% confidence untuk jumlah dalam toleransi"""

def test_date_range_decay():
    """Confidence harus menurun secara linear dalam rentang tanggal"""

# Test edge case
def test_split_transaction_detection():
    """Harus mendeteksi ketika beberapa faktur berjumlah sama dengan jumlah bank"""

def test_duplicate_detection():
    """Harus menandai kemungkinan pencocokan duplikat"""
```

### Integration Test

```python
# Test workflow rekonsiliasi lengkap
async def test_complete_reconciliation_flow():
    """
    1. Buat proyek
    2. Import rekening koran (via OCR)
    3. Import faktur pajak (via OCR)
    4. Jalankan auto-match
    5. Verifikasi statistik
    6. Export laporan
    """
```

### Performance Test

```python
# Test dengan dataset besar
async def test_reconcile_1000_transactions():
    """Harus selesai dalam <30 detik"""

async def test_concurrent_matching():
    """Beberapa pengguna melakukan rekonsiliasi secara bersamaan"""
```

---

Desain ini memberikan Anda **modul rekonsiliasi production-ready, tingkat enterprise** yang terintegrasi sempurna dengan aplikasi Doc Scan AI yang sudah ada! 🚀

Mau gue lanjutkan dengan implementasi Fase 1? Atau ada yang mau diubah dari desain ini?
