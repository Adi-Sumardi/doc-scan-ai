# Tax Reconciliation Module - Quick Start Guide

## 🚀 Quick Start dalam 5 Menit

### 1. Database Setup (Otomatis)

Database tables sudah otomatis ter-create saat aplikasi start. Tidak perlu migration manual.

```bash
# Start aplikasi
cd backend
python main.py
```

Output:
```
✅ Database tables created successfully
✅ Reconciliation tables: 4/4
```

---

### 2. API Endpoints

**Base URL**: `http://localhost:8000/api/reconciliation`

**Authentication**: Semua endpoints butuh JWT token (Bearer token)

---

## 📝 Common Workflows

### Workflow 1: Auto-Match dari Hasil Scan

```bash
# Step 1: Create project
curl -X POST http://localhost:8000/api/reconciliation/projects \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rekonsiliasi Q1 2024",
    "period_start": "2024-01-01T00:00:00",
    "period_end": "2024-03-31T23:59:59"
  }'

# Response: {"id": "project-123", ...}

# Step 2: Import Faktur Pajak dari hasil scan
curl -X POST http://localhost:8000/api/reconciliation/projects/project-123/import/invoices \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_result_ids": ["scan-1", "scan-2", "scan-3"]
  }'

# Response: {"imported": 45, "errors": [], "total_requested": 45}

# Step 3: Import Rekening Koran dari hasil scan
curl -X POST http://localhost:8000/api/reconciliation/projects/project-123/import/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_result_ids": ["scan-4", "scan-5"]
  }'

# Response: {"imported": 150, "errors": [], "total_requested": 150}

# Step 4: Auto-match
curl -X POST http://localhost:8000/api/reconciliation/auto-match \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-123",
    "min_confidence": 0.70
  }'

# Response:
# {
#   "matches_found": 38,
#   "high_confidence_matches": 32,
#   "medium_confidence_matches": 6,
#   "low_confidence_matches": 0,
#   "processing_time_seconds": 1.45
# }

# Step 5: Export hasil ke Excel
curl -X GET http://localhost:8000/api/reconciliation/projects/project-123/export \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output reconciliation_result.xlsx
```

---

### Workflow 2: Manual Input & Matching

```bash
# Step 1: Create project (sama seperti di atas)

# Step 2: Input Faktur Pajak manual
curl -X POST http://localhost:8000/api/reconciliation/invoices \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-123",
    "invoice_number": "INV-2024-001",
    "invoice_date": "2024-01-15T00:00:00",
    "vendor_name": "PT ABC Corporation",
    "vendor_npwp": "01.234.567.8-901.000",
    "dpp": 5000000,
    "ppn": 500000,
    "total_amount": 5500000
  }'

# Step 3: Input Transaksi Bank manual
curl -X POST http://localhost:8000/api/reconciliation/transactions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-123",
    "bank_name": "Bank Mandiri",
    "account_number": "1234567890",
    "transaction_date": "2024-01-16T00:00:00",
    "description": "Payment to PT ABC INV-2024-001",
    "credit": 5500000,
    "balance": 10000000
  }'

# Step 4: Get suggestions untuk invoice
curl -X GET http://localhost:8000/api/reconciliation/invoices/invoice-id/suggestions?limit=5 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
# [
#   {
#     "transaction": {...},
#     "score_details": {
#       "total_score": 0.95,
#       "score_amount": 1.0,
#       "score_date": 0.95,
#       "score_vendor": 1.0,
#       "score_reference": 0.80,
#       "amount_variance": 0.0,
#       "date_variance_days": 1
#     }
#   }
# ]

# Step 5: Manual match
curl -X POST http://localhost:8000/api/reconciliation/matches \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-123",
    "invoice_id": "invoice-id",
    "transaction_id": "transaction-id",
    "match_type": "manual",
    "notes": "Manual match - vendor name slightly different"
  }'

# Step 6: Confirm match
curl -X POST http://localhost:8000/api/reconciliation/matches/match-id/confirm \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📊 Monitoring & Analytics

### Get Project Status

```bash
curl -X GET http://localhost:8000/api/reconciliation/projects/project-123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "id": "project-123",
  "name": "Rekonsiliasi Q1 2024",
  "status": "active",
  "total_invoices": 45,
  "total_transactions": 150,
  "matched_count": 38,
  "unmatched_invoices": 7,
  "unmatched_transactions": 112,
  "total_invoice_amount": 247500000.0,
  "total_transaction_amount": 1250000000.0,
  "variance_amount": 1002500000.0
}
```

### List Unmatched Items

```bash
# Unmatched invoices
curl -X GET http://localhost:8000/api/reconciliation/projects/project-123/invoices?match_status=unmatched \
  -H "Authorization: Bearer YOUR_TOKEN"

# Unmatched transactions
curl -X GET http://localhost:8000/api/reconciliation/projects/project-123/transactions?match_status=unmatched \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### List All Matches

```bash
curl -X GET http://localhost:8000/api/reconciliation/projects/project-123/matches \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔧 Configuration

### Auto-Match Settings

```python
# Min confidence untuk auto-match
min_confidence = 0.70  # Default: 70%

# High confidence: ≥ 90%
# Medium confidence: 70-89%
# Low confidence: 50-69%
# No match: < 50%

# Date tolerance
date_tolerance = 7  # ±7 hari
```

### Scoring Weights

```python
WEIGHT_AMOUNT = 0.50      # 50% dari total score
WEIGHT_DATE = 0.25        # 25% dari total score
WEIGHT_VENDOR = 0.15      # 15% dari total score
WEIGHT_REFERENCE = 0.10   # 10% dari total score
```

---

## 📁 Excel Export Format

Export menghasilkan file Excel dengan 6 sheets:

1. **Summary** - Overview proyek & statistik
2. **Matched Pairs** - Invoice + Transaction yang sudah match
3. **Unmatched Invoices** - Faktur yang belum match (red)
4. **Unmatched Transactions** - Transaksi yang belum match (red)
5. **All Invoices** - Complete list semua faktur
6. **All Transactions** - Complete list semua transaksi

Color coding:
- 🟢 Green: Matched (auto atau manual)
- 🔵 Blue: High confidence match (≥90%)
- 🟡 Yellow: Medium confidence match (70-89%)
- 🟠 Orange: Low confidence match (50-69%)
- 🔴 Red: Unmatched

---

## 🐛 Troubleshooting

### Problem: Import failed dengan error

**Solution**: Pastikan scan_result_ids valid dan document_type sesuai:
- Faktur Pajak: `document_type = "faktur_pajak"`
- Rekening Koran: `document_type = "rekening_koran"`

### Problem: Auto-match tidak menemukan match

**Possible causes**:
1. Amount variance terlalu besar (>10%)
2. Date variance terlalu jauh (>7 hari)
3. Vendor name tidak similar
4. Invoice number tidak ada di transaction reference

**Solution**:
- Lower `min_confidence` (e.g., 0.50)
- Check unmatched items dan lakukan manual match
- Use suggestions endpoint untuk lihat scoring details

### Problem: Export failed

**Solution**:
- Pastikan openpyxl installed: `pip install openpyxl`
- Check exports directory exists dan writable
- Verify project_id valid

---

## 🎯 Best Practices

### 1. Import Strategy

**Recommended**:
```
1. Import semua Faktur Pajak dulu
2. Import semua Rekening Koran
3. Run auto-match
4. Review unmatched items
5. Manual match sisanya
6. Confirm high-confidence matches
7. Export hasil
```

### 2. Match Review Workflow

**Priority order**:
1. Review & confirm high confidence matches (≥90%)
2. Review medium confidence matches (70-89%)
3. Check suggestions untuk unmatched invoices
4. Manual match sisanya
5. Investigate items yang tidak bisa match

### 3. Quality Checks

Before exporting:
- ✅ Check total invoice amount vs transaction amount
- ✅ Verify variance is acceptable
- ✅ Confirm all high-value items are matched
- ✅ Review disputed items
- ✅ Validate unmatched items adalah legitimate

---

## 📞 API Reference Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/projects` | POST | Create project |
| `/projects` | GET | List projects |
| `/projects/{id}` | GET | Get project |
| `/projects/{id}` | DELETE | Archive project |
| `/invoices` | POST | Create invoice |
| `/projects/{id}/invoices` | GET | List invoices |
| `/transactions` | POST | Create transaction |
| `/projects/{id}/transactions` | GET | List transactions |
| `/auto-match` | POST | Auto-match |
| `/invoices/{id}/suggestions` | GET | Get suggestions |
| `/matches` | POST | Manual match |
| `/matches/{id}` | DELETE | Unmatch |
| `/matches/{id}/confirm` | POST | Confirm match |
| `/projects/{id}/import/invoices` | POST | Bulk import invoices |
| `/projects/{id}/import/transactions` | POST | Bulk import transactions |
| `/projects/{id}/export` | GET | Export to Excel |

---

## 🎓 Matching Algorithm Examples

### Example 1: Perfect Match (98%)

Invoice:
```
Number: INV-2024-001
Date: 2024-01-15
Vendor: PT ABC Corp
Amount: 5,000,000
```

Transaction:
```
Date: 2024-01-15
Description: "Payment to PT ABC Corp INV-2024-001"
Credit: 5,000,000
```

Scoring:
- Amount: 1.00 (exact) × 50% = 0.50
- Date: 1.00 (same) × 25% = 0.25
- Vendor: 1.00 (exact) × 15% = 0.15
- Reference: 0.80 (in desc) × 10% = 0.08
- **Total: 0.98 (98%)** ✅ HIGH CONFIDENCE

### Example 2: Good Match (89%)

Invoice:
```
Number: INV-2024-002
Date: 2024-01-20
Vendor: PT XYZ Indonesia
Amount: 10,000,000
```

Transaction:
```
Date: 2024-01-21
Description: "Transfer to PT XYZ"
Credit: 10,000,000
```

Scoring:
- Amount: 1.00 (exact) × 50% = 0.50
- Date: 0.95 (1 day) × 25% = 0.24
- Vendor: 1.00 (similar) × 15% = 0.15
- Reference: 0.00 (not found) × 10% = 0.00
- **Total: 0.89 (89%)** ✅ MEDIUM CONFIDENCE

### Example 3: Poor Match (40%)

Invoice:
```
Number: INV-2024-003
Date: 2024-01-25
Vendor: PT AAA Corp
Amount: 15,000,000
```

Transaction:
```
Date: 2024-01-25
Description: "Transfer to PT BBB Corp"
Credit: 9,000,000
```

Scoring:
- Amount: 0.10 (40% diff) × 50% = 0.05
- Date: 1.00 (same) × 25% = 0.25
- Vendor: 0.40 (different) × 15% = 0.06
- Reference: 0.00 (not found) × 10% = 0.00
- **Total: 0.40 (40%)** ❌ NO MATCH

---

## ✅ Checklist: Production Deployment

- [ ] Database tables created
- [ ] Authentication configured
- [ ] CORS settings untuk frontend
- [ ] Export directory writable
- [ ] openpyxl installed
- [ ] Test auto-match dengan real data
- [ ] Verify Excel export
- [ ] Set up monitoring
- [ ] Configure backup strategy
- [ ] Document user training

---

**Version**: 1.0.0
**Last Updated**: 2024-10-16
**Status**: ✅ Production Ready

🎉 **Selamat menggunakan Tax Reconciliation Module!**
