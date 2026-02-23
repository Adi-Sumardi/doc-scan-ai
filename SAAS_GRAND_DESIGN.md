# Doc Scan AI - Grand Design SaaS

## Executive Summary

Transformasi Doc Scan AI dari aplikasi internal menjadi platform SaaS dengan model **token-based billing** yang mirip dengan emergent.sh. User membeli token (credits) dan menggunakannya untuk scan dokumen.

---

## 1. Business Model

### 1.1 Token-Based System

```
1 Token = 1 Halaman Dokumen yang Diproses
```

**Perhitungan Biaya Internal (Cost per Page):**

| Komponen | Biaya per 1000 halaman | Biaya per halaman |
|----------|------------------------|-------------------|
| Google Document AI OCR | $1.50 | $0.0015 |
| AI Extraction (GPT-4o/Claude) | ~$5.00 | $0.005 |
| Server & Infrastructure | ~$0.50 | $0.0005 |
| **Total Cost** | **~$7.00** | **~$0.007** |

**Harga Jual Token (dengan margin 3-5x):**
- Cost: Rp 110/halaman (asumsi $1 = Rp 16,000)
- Harga jual: Rp 300-500/halaman (margin 170-350%)

---

## 2. Pricing Tiers

### 2.1 Paket Token (Top-Up)

| Paket | Jumlah Token | Harga | Harga/Token | Diskon |
|-------|--------------|-------|-------------|--------|
| **Starter** | 100 tokens | Rp 50,000 | Rp 500 | - |
| **Basic** | 500 tokens | Rp 200,000 | Rp 400 | 20% |
| **Professional** | 2,000 tokens | Rp 600,000 | Rp 300 | 40% |
| **Business** | 10,000 tokens | Rp 2,500,000 | Rp 250 | 50% |
| **Enterprise** | 50,000 tokens | Rp 10,000,000 | Rp 200 | 60% |

### 2.2 Subscription Plans (Opsional)

| Plan | Token/Bulan | Harga/Bulan | Bonus | Fitur |
|------|-------------|-------------|-------|-------|
| **Free** | 10 | Gratis | - | Basic OCR, Watermark |
| **Starter** | 200 | Rp 99,000 | +20 bonus | Full OCR, No watermark |
| **Pro** | 1,000 | Rp 399,000 | +150 bonus | + Priority processing |
| **Business** | 5,000 | Rp 1,499,000 | +1,000 bonus | + API Access, Team |
| **Enterprise** | Custom | Custom | Custom | + SLA, Dedicated support |

---

## 3. Token Consumption Rules

### 3.1 Per Document Type

| Tipe Dokumen | Token/Halaman | Keterangan |
|--------------|---------------|------------|
| **Faktur Pajak** | 1 token | Standard extraction |
| **Rekening Koran** | 2 token | Complex table extraction |
| **Invoice** | 1 token | Standard extraction |
| **KTP/ID Card** | 1 token | Single page |
| **Kontrak/Agreement** | 1 token | Per halaman |
| **Custom Document** | 2 token | AI-powered extraction |

### 3.2 Bonus Token Events

| Event | Bonus Token |
|-------|-------------|
| Sign up (new user) | 20 tokens FREE |
| Referral (per user) | 50 tokens |
| Review di Google/Socmed | 30 tokens |
| First purchase bonus | +10% tokens |

---

## 4. System Architecture

### 4.1 New Database Schema

```sql
-- Users Table (extend existing)
ALTER TABLE users ADD COLUMN token_balance INT DEFAULT 0;
ALTER TABLE users ADD COLUMN subscription_plan VARCHAR(50) DEFAULT 'free';
ALTER TABLE users ADD COLUMN subscription_expires_at DATETIME;

-- Token Transactions
CREATE TABLE token_transactions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    transaction_type ENUM('purchase', 'usage', 'bonus', 'refund', 'expired') NOT NULL,
    amount INT NOT NULL,  -- positive for credit, negative for debit
    balance_after INT NOT NULL,
    description TEXT,
    reference_id VARCHAR(36),  -- batch_id for usage, payment_id for purchase
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Token Packages
CREATE TABLE token_packages (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    token_amount INT NOT NULL,
    price_idr DECIMAL(15,2) NOT NULL,
    price_usd DECIMAL(10,2),
    discount_percent INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Payments
CREATE TABLE payments (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    package_id VARCHAR(36),
    amount_idr DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(50),  -- midtrans, xendit, manual
    payment_status ENUM('pending', 'success', 'failed', 'expired') DEFAULT 'pending',
    payment_reference VARCHAR(255),
    token_granted INT DEFAULT 0,
    paid_at DATETIME,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (package_id) REFERENCES token_packages(id)
);

-- Subscription Plans
CREATE TABLE subscription_plans (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    monthly_tokens INT NOT NULL,
    bonus_tokens INT DEFAULT 0,
    price_monthly_idr DECIMAL(15,2) NOT NULL,
    features JSON,
    is_active BOOLEAN DEFAULT TRUE
);

-- User Subscriptions
CREATE TABLE user_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    plan_id VARCHAR(36) NOT NULL,
    status ENUM('active', 'cancelled', 'expired') DEFAULT 'active',
    current_period_start DATETIME,
    current_period_end DATETIME,
    tokens_remaining INT DEFAULT 0,
    auto_renew BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);
```

### 4.2 API Endpoints (New)

```python
# Token Management
GET  /api/tokens/balance          # Get user token balance
GET  /api/tokens/history          # Get transaction history
POST /api/tokens/estimate         # Estimate tokens needed for upload

# Packages & Pricing
GET  /api/packages                # List available packages
GET  /api/packages/{id}           # Package details

# Payments
POST /api/payments/create         # Create payment (Midtrans/Xendit)
POST /api/payments/callback       # Payment gateway callback
GET  /api/payments/history        # User payment history

# Subscriptions
GET  /api/subscriptions/plans     # List subscription plans
POST /api/subscriptions/subscribe # Subscribe to plan
POST /api/subscriptions/cancel    # Cancel subscription
```

### 4.3 Token Deduction Flow

```
User Upload Files
       ↓
Estimate Tokens Required
       ↓
Check Token Balance ──→ Insufficient? ──→ Show "Buy Tokens" Modal
       ↓
Deduct Tokens (PENDING)
       ↓
Process Documents
       ↓
Success? ──→ Yes: Confirm Token Deduction
         └─→ No: Refund Tokens
```

---

## 5. Payment Gateway Integration

### 5.1 Recommended: Midtrans

**Pros:**
- Paling populer di Indonesia
- Support: GoPay, OVO, DANA, Bank Transfer, Credit Card, Indomaret
- Fee: 2.9% + Rp 2,000 (varies by method)

**Integration:**
```python
# Backend: payments.py
import midtransclient

snap = midtransclient.Snap(
    is_production=True,
    server_key='YOUR_SERVER_KEY',
    client_key='YOUR_CLIENT_KEY'
)

def create_payment(user_id, package_id, amount):
    param = {
        "transaction_details": {
            "order_id": f"DCSCAN-{uuid4()}",
            "gross_amount": amount
        },
        "customer_details": {
            "email": user.email,
            "first_name": user.name
        }
    }
    return snap.create_transaction(param)
```

### 5.2 Alternative: Xendit

**Pros:**
- Modern API
- Virtual Account, E-Wallet, Cards
- Fee: 2.5% - 4%

---

## 6. Frontend UI/UX Changes

### 6.1 New Components

```
1. Token Balance Widget (Header)
   ┌─────────────────────────────┐
   │ 🪙 1,250 Tokens  [Top Up]  │
   └─────────────────────────────┘

2. Package Selection Modal
   ┌─────────────────────────────────────────┐
   │        Pilih Paket Token                │
   ├─────────────────────────────────────────┤
   │  ○ Starter   100 tokens   Rp 50.000    │
   │  ● Basic     500 tokens   Rp 200.000 ★ │
   │  ○ Pro       2000 tokens  Rp 600.000   │
   └─────────────────────────────────────────┘
   │           [Bayar Sekarang]              │
   └─────────────────────────────────────────┘

3. Upload Token Estimation
   ┌─────────────────────────────────────────┐
   │ 📁 15 files selected                    │
   │ 📄 Estimated: 23 pages                  │
   │ 🪙 Tokens needed: 23                    │
   │ 💰 Your balance: 1,250                  │
   │                                         │
   │         [Upload & Process]              │
   └─────────────────────────────────────────┘

4. Insufficient Balance Modal
   ┌─────────────────────────────────────────┐
   │ ⚠️ Token Tidak Cukup                    │
   │                                         │
   │ Dibutuhkan: 50 tokens                   │
   │ Saldo Anda: 23 tokens                   │
   │ Kurang: 27 tokens                       │
   │                                         │
   │ [Beli Token]  [Upgrade Plan]            │
   └─────────────────────────────────────────┘
```

### 6.2 New Pages

1. `/pricing` - Halaman pricing & packages
2. `/dashboard/tokens` - Token balance & history
3. `/dashboard/billing` - Payment history & invoices
4. `/dashboard/subscription` - Manage subscription

---

## 7. Revenue Projection

### 7.1 Assumptions

- Target: 100 active users dalam 6 bulan
- Average usage: 500 pages/user/month
- Average price: Rp 350/page

### 7.2 Monthly Revenue Projection

| Bulan | Users | Pages/Month | Revenue |
|-------|-------|-------------|---------|
| 1 | 10 | 5,000 | Rp 1,750,000 |
| 3 | 30 | 15,000 | Rp 5,250,000 |
| 6 | 100 | 50,000 | Rp 17,500,000 |
| 12 | 300 | 150,000 | Rp 52,500,000 |

### 7.3 Cost Analysis (Month 6)

| Item | Cost/Month |
|------|------------|
| Google Document AI | Rp 1,200,000 |
| OpenAI/Claude API | Rp 4,000,000 |
| Server (VPS) | Rp 500,000 |
| Payment Gateway Fee (~3%) | Rp 525,000 |
| **Total Cost** | **Rp 6,225,000** |
| **Revenue** | **Rp 17,500,000** |
| **Net Profit** | **Rp 11,275,000** |
| **Margin** | **64%** |

---

## 8. Implementation Roadmap

### Phase 1: Foundation (2-3 minggu)
- [ ] Database schema untuk tokens & payments
- [ ] Token balance API endpoints
- [ ] Token deduction on document processing
- [ ] Basic token balance UI

### Phase 2: Payment Integration (2 minggu)
- [ ] Midtrans integration
- [ ] Package purchase flow
- [ ] Payment callback handling
- [ ] Transaction history

### Phase 3: Subscription System (2 minggu)
- [ ] Subscription plans
- [ ] Auto-renewal logic
- [ ] Monthly token reset
- [ ] Upgrade/downgrade flow

### Phase 4: Polish & Launch (1-2 minggu)
- [ ] Pricing page
- [ ] Invoice generation
- [ ] Email notifications
- [ ] Analytics dashboard

**Total Timeline: 7-9 minggu**

---

## 9. Marketing Strategy

### 9.1 Launch Offer
- **First 100 users**: FREE 50 tokens (senilai Rp 25,000)
- **Early Bird**: 30% discount untuk 3 bulan pertama

### 9.2 Target Market
1. **Akuntan/Tax Consultant** - Proses faktur pajak massal
2. **Finance Team** - Rekonsiliasi bank statement
3. **SME/UMKM** - Digitalisasi dokumen
4. **Startup** - Automasi invoice processing

### 9.3 Channels
- LinkedIn (professional audience)
- Facebook Groups (komunitas akuntan/tax)
- Google Ads (keyword: OCR, scan dokumen, faktur pajak)
- Referral program

---

## 10. Competitive Advantage

| Feature | Doc Scan AI | Kompetitor |
|---------|-------------|------------|
| Spesifik Indonesia (Faktur Pajak) | ✅ | ❌ |
| Harga dalam Rupiah | ✅ | ❌ |
| Payment lokal (GoPay, OVO, dll) | ✅ | ❌ |
| AI Extraction akurat | ✅ | Varies |
| No minimum purchase | ✅ | ❌ |
| Free trial tokens | ✅ | Varies |

---

## 11. Technical Recommendations

### 11.1 Remove Unused Dependencies

**Untuk hemat server resources, hapus PyTorch/CUDA** (6GB!) karena sudah pakai Google Document AI:

```bash
pip uninstall torch torchvision torchaudio
pip uninstall nvidia-cublas-cu12 nvidia-cuda-* nvidia-cudnn-*
```

Ini akan free ~6GB disk dan memory.

### 11.2 Caching Strategy

Implement Redis caching untuk:
- Token balance (5 menit TTL)
- Package list (1 jam TTL)
- User subscription status (10 menit TTL)

### 11.3 Rate Limiting

Untuk prevent abuse:
- Free tier: 10 requests/minute
- Paid tier: 60 requests/minute
- Enterprise: Unlimited

---

## 12. Legal & Compliance

### 12.1 Required Documents
- Terms of Service
- Privacy Policy (GDPR-compliant)
- Refund Policy

### 12.2 Data Retention
- Uploaded documents: 30 hari
- Processed results: 90 hari
- Payment records: 5 tahun (tax compliance)

---

## Appendix A: Competitor Pricing Reference

| Service | Pricing | Notes |
|---------|---------|-------|
| [Google Document AI](https://cloud.google.com/document-ai/pricing) | $1.50/1000 pages | Base OCR |
| [AWS Textract](https://aws.amazon.com/textract/pricing/) | $1.50/1000 pages | Similar to Google |
| [Mistral OCR](https://pyimagesearch.com/2025/12/23/mistral-ocr-3-technical-review-sota-document-parsing-at-commodity-pricing/) | $1/1000 pages | Batch API |
| [Nanonets](https://nanonets.com/buyers-guide/ocr-software) | $0.01-0.05/page | SaaS platform |
| Manual Scanning Service | $0.07-0.12/page | Physical scanning |

---

**Document Version:** 1.0
**Last Updated:** December 2024
**Author:** AI Assistant
