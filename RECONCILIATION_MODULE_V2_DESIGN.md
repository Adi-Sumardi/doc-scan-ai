# 🔄 Tax Reconciliation Module V2.0 - Updated Design

**Last Updated**: October 18, 2025
**Status**: Ready for Implementation
**Compatibility**: Doc Scan AI v2.0 (Dual AI + Lazy Loading Architecture)

---

## 📋 Executive Summary

Tax Reconciliation module yang **fully integrated** dengan arsitektur terbaru Doc Scan AI:
- ✅ Dual AI Model Support (GPT-4o + Claude Sonnet 4)
- ✅ Lazy Loading Architecture
- ✅ Enhanced Bank Statement Processing (Hybrid Processor)
- ✅ Modular Exporter System
- ✅ React Context API State Management

---

## 🎯 What's New in V2.0

### Major Changes from V1.0:

1. **Dual AI Integration**
   - Auto-detect vendor names menggunakan GPT-4o untuk Faktur Pajak
   - Auto-extract transaction descriptions menggunakan Claude Sonnet 4 untuk Rekening Koran
   - Intelligent matching dengan confidence scoring dari kedua model

2. **Lazy Loading Support**
   - Load only recent reconciliation projects (10 most recent)
   - Background loading untuk historical data
   - Non-blocking UI untuk large datasets

3. **Enhanced Matching Algorithm**
   - Leverage existing SmartMapper untuk vendor name normalization
   - Use Claude AI untuk fuzzy matching description
   - GPT-4o untuk invoice number extraction dari transaction notes

4. **Modular Architecture**
   - Reuse existing `enhanced_bank_processor.py` logic
   - Integrate dengan `hybrid_bank_processor.py` untuk better transaction parsing
   - Use existing `exporters/` system untuk Excel generation

---

## 🏗️ System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   User Upload Documents                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┴────────────┐
         │                          │
         ▼                          ▼
┌─────────────────┐        ┌────────────────┐
│ Rekening Koran  │        │ Faktur Pajak   │
│ (Claude AI)     │        │ (GPT-4o)       │
└────────┬────────┘        └────────┬───────┘
         │                          │
         │    Existing OCR          │
         │    Pipeline              │
         │                          │
         ▼                          ▼
┌─────────────────┐        ┌────────────────┐
│ Bank Trans DB   │        │ Invoice DB     │
│ (extracted)     │        │ (extracted)    │
└────────┬────────┘        └────────┬───────┘
         │                          │
         └─────────┬─────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ Reconciliation       │
         │ Matching Engine      │
         │ (Multi-Criteria)     │
         └──────────┬───────────┘
                    │
      ┌─────────────┼─────────────┐
      │             │             │
      ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Matched  │  │Unmatched │  │Discrep.  │
│ Pairs    │  │ Items    │  │ Report   │
└──────────┘  └──────────┘  └──────────┘
      │             │             │
      └─────────────┼─────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ Excel Export         │
         │ (Multi-Sheet)        │
         └─────────────────────┘
```

---

## 🗄️ Database Schema (Updated)

### Key Changes:
- Add `ai_model_used` field (track which AI processed the data)
- Add `lazy_loaded` flag for pagination support
- Add indexes for performance optimization

```sql
-- Reconciliation Projects Table
CREATE TABLE reconciliation_projects (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    period_start DATETIME,
    period_end DATETIME,
    status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'active',

    -- Statistics (auto-calculated)
    total_invoices INT DEFAULT 0,
    total_transactions INT DEFAULT 0,
    matched_count INT DEFAULT 0,
    unmatched_invoices INT DEFAULT 0,
    unmatched_transactions INT DEFAULT 0,
    match_rate DECIMAL(5,2) DEFAULT 0.00,  -- Percentage

    -- Financial Summary
    total_invoice_amount DECIMAL(15,2) DEFAULT 0.00,
    total_transaction_amount DECIMAL(15,2) DEFAULT 0.00,
    variance_amount DECIMAL(15,2) DEFAULT 0.00,
    variance_percentage DECIMAL(5,2) DEFAULT 0.00,

    -- AI Integration
    ai_vendor_matching_enabled BOOLEAN DEFAULT TRUE,
    ai_reference_extraction_enabled BOOLEAN DEFAULT TRUE,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_status (user_id, status),
    INDEX idx_created_at (created_at DESC)
);

-- Tax Invoices Table (from Faktur Pajak scans)
CREATE TABLE recon_tax_invoices (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    scan_result_id VARCHAR(36),  -- Link to processing_results table

    -- Invoice Data (from GPT-4o extraction)
    invoice_number VARCHAR(100) NOT NULL,
    invoice_date DATE NOT NULL,
    vendor_name VARCHAR(255),
    vendor_npwp VARCHAR(20),

    -- Amounts
    dpp DECIMAL(15,2) NOT NULL,            -- Dasar Pengenaan Pajak
    ppn DECIMAL(15,2) NOT NULL,            -- PPN 11%
    total_amount DECIMAL(15,2) NOT NULL,   -- DPP + PPN

    -- Matching Status
    match_status ENUM('unmatched', 'matched', 'partial', 'disputed') DEFAULT 'unmatched',
    matched_transaction_id VARCHAR(36),
    match_confidence DECIMAL(5,2),  -- 0.00 to 100.00
    match_method ENUM('auto', 'manual', 'ai_suggested'),
    matched_at DATETIME,

    -- AI Processing Metadata
    ai_model_used VARCHAR(50) DEFAULT 'gpt-4o',
    extraction_confidence DECIMAL(5,2),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (scan_result_id) REFERENCES processing_results(id) ON DELETE SET NULL,
    INDEX idx_project_match (project_id, match_status),
    INDEX idx_invoice_number (invoice_number),
    INDEX idx_invoice_date (invoice_date)
);

-- Bank Transactions Table (from Rekening Koran scans)
CREATE TABLE recon_bank_transactions (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    scan_result_id VARCHAR(36),  -- Link to processing_results table

    -- Transaction Data (from Claude AI extraction)
    bank_name VARCHAR(100),
    account_number VARCHAR(50),
    transaction_date DATE NOT NULL,
    posting_date DATE,
    description TEXT,
    reference_number VARCHAR(100),

    -- Amounts
    debit DECIMAL(15,2) DEFAULT 0.00,
    credit DECIMAL(15,2) DEFAULT 0.00,
    balance DECIMAL(15,2),

    -- Matching Status
    match_status ENUM('unmatched', 'matched', 'partial', 'disputed') DEFAULT 'unmatched',
    matched_invoice_id VARCHAR(36),
    match_confidence DECIMAL(5,2),
    match_method ENUM('auto', 'manual', 'ai_suggested'),
    matched_at DATETIME,

    -- AI Extracted Fields (from Claude)
    extracted_vendor_name VARCHAR(255),      -- AI-extracted from description
    extracted_invoice_number VARCHAR(100),   -- AI-extracted from reference/description

    -- AI Processing Metadata
    ai_model_used VARCHAR(50) DEFAULT 'claude-sonnet-4',
    extraction_confidence DECIMAL(5,2),

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (scan_result_id) REFERENCES processing_results(id) ON DELETE SET NULL,
    INDEX idx_project_match (project_id, match_status),
    INDEX idx_transaction_date (transaction_date),
    INDEX idx_extracted_vendor (extracted_vendor_name)
);

-- Matches Table (M:N relationship)
CREATE TABLE recon_matches (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    invoice_id VARCHAR(36),
    transaction_id VARCHAR(36),

    -- Match Details
    match_type ENUM('one_to_one', 'one_to_many', 'many_to_one') DEFAULT 'one_to_one',
    confidence_score DECIMAL(5,2) NOT NULL,
    match_method ENUM('auto', 'manual', 'ai_suggested') NOT NULL,

    -- Score Breakdown (for transparency)
    score_amount DECIMAL(5,2),      -- Amount matching score
    score_date DECIMAL(5,2),        -- Date proximity score
    score_vendor DECIMAL(5,2),      -- Vendor name similarity score
    score_reference DECIMAL(5,2),   -- Reference number matching score

    -- Amount Details
    invoice_amount DECIMAL(15,2),
    transaction_amount DECIMAL(15,2),
    amount_variance DECIMAL(15,2),
    date_variance_days INT,

    -- Status
    status ENUM('suggested', 'confirmed', 'disputed', 'rejected') DEFAULT 'suggested',
    notes TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),  -- User who created/confirmed match

    FOREIGN KEY (project_id) REFERENCES reconciliation_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (invoice_id) REFERENCES recon_tax_invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES recon_bank_transactions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_match (invoice_id, transaction_id),
    INDEX idx_project_status (project_id, status),
    INDEX idx_confidence (confidence_score DESC)
);
```

---

## 🧠 Enhanced Matching Algorithm with Dual AI

### Intelligent Vendor Name Matching

**Problem**: Bank transaction descriptions are messy
```
"TRF DR PT SEJAHTERA ABD TBK CAB JKT"
vs
"PT SEJAHTERA ABADI"
```

**Solution**: Use GPT-4o Smart Mapper

```python
async def ai_match_vendor_names(
    transaction_description: str,
    candidate_vendors: List[str],
    model: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Use GPT-4o to intelligently match vendor names
    Leverages existing SmartMapper infrastructure
    """
    prompt = f"""
    Given this bank transaction description:
    "{transaction_description}"

    Match it to the most likely vendor from this list:
    {json.dumps(candidate_vendors, indent=2)}

    Return JSON:
    {{
        "matched_vendor": "PT SEJAHTERA ABADI",
        "confidence": 0.92,
        "reasoning": "Abbreviation 'ABD' matches 'ABADI', same company name structure"
    }}
    """

    # Use existing SmartMapper (already has GPT-4o client)
    result = await smart_mapper.query(prompt)
    return result
```

### Invoice Number Extraction from Transaction Notes

**Problem**: Invoice numbers buried in transaction reference
```
"PAYMENT FOR INVOICE INV-2024-001 AND INV-2024-002"
```

**Solution**: Use Claude AI for extraction

```python
async def extract_invoice_references(
    transaction_description: str,
    model: str = "claude-sonnet-4"
) -> List[str]:
    """
    Use Claude to extract invoice numbers from transaction text
    """
    prompt = f"""
    Extract all invoice numbers from this transaction description:
    "{transaction_description}"

    Return JSON array: ["INV-2024-001", "INV-2024-002"]
    """

    # Use existing Claude client (already initialized in smart_mapper.py)
    result = await smart_mapper._invoke_claude_direct(prompt, "")
    return json.loads(result)
```

---

## 🔄 Integration with Existing Systems

### 1. Reuse OCR Pipeline

**NO need to rewrite OCR!** Use existing endpoints:

```python
# Frontend uploads documents
POST /api/upload  # Existing endpoint
→ Returns batch_id

# Backend processes with existing pipeline
→ Google Document AI OCR (already working)
→ GPT-4o Smart Mapper for Faktur Pajak
→ Claude AI Smart Mapper for Rekening Koran
→ Stored in processing_results table

# Reconciliation imports from processing_results
POST /api/reconciliation/projects/{id}/import/invoices
{
    "scan_result_ids": ["result-1", "result-2", "result-3"]
}

# Backend:
1. SELECT * FROM processing_results WHERE id IN (...)
2. Parse extracted_data JSON
3. INSERT INTO recon_tax_invoices (...)
```

### 2. Leverage Modular Exporter System

**Use existing exporter pattern:**

```python
# backend/exporters/reconciliation_exporter.py
class ReconciliationExporter(BaseExporter):
    """
    Follows same pattern as:
    - FakturPajakExporter
    - RekeningKoranExporter
    - PPh21Exporter
    """

    def export_to_excel(self, project_id: str) -> str:
        """
        Generate multi-sheet Excel report
        Sheet 1: Summary
        Sheet 2: Matched Pairs
        Sheet 3: Unmatched Invoices
        Sheet 4: Unmatched Transactions
        Sheet 5: All Invoices
        Sheet 6: All Transactions
        """
        # Use openpyxl (already installed)
        # Follow same styling as existing exporters
        pass
```

### 3. Frontend Integration with DocumentContext

**Leverage existing React Context API:**

```typescript
// src/context/ReconciliationContext.tsx
export const ReconciliationProvider: React.FC<Props> = ({ children }) => {
    const [projects, setProjects] = useState<ReconciliationProject[]>([]);
    const [loading, setLoading] = useState(false);

    // Lazy loading pattern (same as DocumentContext)
    const loadRecentProjectsOnly = async () => {
        setLoading(true);
        const allProjects = await apiService.getAllReconciliationProjects();
        const recent = allProjects.slice(0, 10);  // Only 10 recent
        setProjects(recent);
        setLoading(false);

        // Background load remaining
        if (allProjects.length > 10) {
            setTimeout(() => {
                setProjects(allProjects);
            }, 1000);
        }
    };

    // ... rest follows DocumentContext pattern
};
```

---

## 🚀 API Endpoints (Updated)

### Enhanced Endpoints with AI Features

```python
# POST /api/reconciliation/auto-match
{
    "project_id": "project-123",
    "min_confidence": 0.70,
    "use_ai_vendor_matching": true,        # NEW: Use GPT-4o for vendor matching
    "use_ai_reference_extraction": true,   # NEW: Use Claude for invoice extraction
    "date_tolerance_days": 7
}

# Response includes AI insights
{
    "matches_found": 42,
    "high_confidence": 35,
    "medium_confidence": 7,
    "low_confidence": 0,
    "ai_vendor_matches": 28,      # NEW: Matched using AI
    "ai_reference_matches": 15,   # NEW: Matched using AI extraction
    "processing_time": 2.8,
    "model_usage": {
        "gpt_4o_calls": 28,
        "claude_calls": 15,
        "total_tokens": 45000
    }
}

# GET /api/reconciliation/invoices/{id}/suggestions
# Returns AI-enhanced suggestions
{
    "invoice": {...},
    "suggestions": [
        {
            "transaction": {...},
            "confidence": 0.94,
            "score_details": {
                "amount": 1.00,
                "date": 0.95,
                "vendor": 0.92,     # AI-matched
                "reference": 0.88   # AI-extracted
            },
            "ai_insights": {
                "vendor_match_method": "gpt_4o_fuzzy",
                "vendor_match_reasoning": "Abbreviation pattern match",
                "extracted_references": ["INV-001"],
                "confidence_ai": 0.92
            }
        }
    ]
}
```

---

## 💻 Frontend Components (Updated)

### New Components Following Existing Patterns

```typescript
// src/pages/Reconciliation/Dashboard.tsx
// Similar to: src/pages/History.tsx
// Shows list of reconciliation projects with lazy loading

// src/pages/Reconciliation/ProjectDetail.tsx
// Similar to: src/pages/ScanResults.tsx
// Shows matched/unmatched items with split view

// src/components/Reconciliation/MatchSuggestion.tsx
// Similar to: src/components/DocumentViewer.tsx
// Shows AI-powered match suggestions with confidence scores

// src/components/Reconciliation/AIInsightBadge.tsx
// NEW: Shows which AI model was used
// GPT-4o badge for vendor matching
// Claude badge for reference extraction
```

### UI Components Structure

```
src/pages/Reconciliation/
├── Dashboard.tsx              # Project list (lazy loaded)
├── ProjectDetail.tsx          # Main reconciliation view
├── MatchingInterface.tsx      # Manual matching modal
└── DiscrepancyView.tsx        # Discrepancy details

src/components/Reconciliation/
├── StatCard.tsx               # Statistics cards
├── TransactionTable.tsx       # Paginated table
├── MatchSuggestion.tsx        # AI suggestions
├── ConfidenceScore.tsx        # Visual confidence indicator
├── AIInsightBadge.tsx         # Show AI model used
└── VendorMatchPreview.tsx     # Preview vendor match reasoning
```

---

## 📊 Enhanced Excel Export Format

### Multi-Sheet Export with AI Insights

```
Sheet 1: Summary
┌───────────────────────────────────────────────────────┐
│ Tax Reconciliation Report                            │
│ Project: Q1 2024 Reconciliation                      │
│ Period: Jan 1 - Mar 31, 2024                         │
│ Generated: Apr 1, 2024 10:30 WIB                     │
├───────────────────────────────────────────────────────┤
│ Statistics                                            │
│ Total Invoices:              45                      │
│ Total Transactions:         150                      │
│ Matched:                     38  (84.4%)             │
│ Unmatched Invoices:           7                      │
│ Unmatched Transactions:     112                      │
│                                                       │
│ AI Performance                                        │
│ AI Vendor Matches:           28  (73.7% of matches)  │
│ AI Reference Matches:        15  (39.5% of matches)  │
│ Average Match Confidence:  89.5%                     │
│                                                       │
│ Financial Summary                                     │
│ Total Invoice Amount:   Rp 247,500,000              │
│ Total Transaction Amount: Rp 1,250,000,000          │
│ Variance:               Rp 1,002,500,000            │
│ Match Coverage:              19.8%                   │
└───────────────────────────────────────────────────────┘

Sheet 2: Matched Pairs
[Invoice# | Date | Amount | Trans# | Trans Amount | Confidence | AI Model | Match Method]

Sheet 3: Unmatched Invoices (with AI suggestions)
[Invoice# | Date | Vendor | Amount | Top Suggestion | Confidence | AI Reason]

Sheet 4: Unmatched Transactions (with AI extraction)
[Date | Description | Amount | Extracted Vendor | Extracted Invoice# | AI Confidence]

Sheet 5: All Invoices (complete data dump)
Sheet 6: All Transactions (complete data dump)
```

---

## 🎯 Implementation Phases (Updated)

### Phase 1: Core Infrastructure (Week 1)
- [x] Database schema & migration
- [x] Basic CRUD endpoints (already exists)
- [x] Import from existing scan_results
- [ ] Basic matching algorithm (amount + date only)
- [ ] Simple Excel export

### Phase 2: AI Integration (Week 2)
- [ ] GPT-4o vendor name matching
- [ ] Claude invoice number extraction
- [ ] Enhanced matching with AI scores
- [ ] AI insights in API responses

### Phase 3: Frontend & UX (Week 3)
- [ ] Reconciliation Dashboard (lazy loading)
- [ ] Project Detail View
- [ ] Matching Interface with AI suggestions
- [ ] AI Insight Badges
- [ ] Confidence Score Visualization

### Phase 4: Advanced Features (Week 4)
- [ ] Split transaction detection
- [ ] Partial payment tracking
- [ ] Duplicate detection
- [ ] Bulk operations
- [ ] Advanced filtering

### Phase 5: Polish & Testing (Week 5)
- [ ] Performance optimization (1000+ items)
- [ ] Integration tests
- [ ] User acceptance testing
- [ ] Documentation
- [ ] Deployment to production

**Total Timeline: 5 weeks**

---

## 💡 Key Innovations in V2.0

### 1. Zero Additional OCR Cost
- Reuse existing processed documents
- No need to re-scan
- Import directly from `processing_results` table

### 2. Intelligent AI Orchestration
- GPT-4o for tax document understanding
- Claude for bank statement parsing
- Best-of-both-worlds matching

### 3. Lazy Loading Architecture
- Fast initial load (10 recent projects)
- Background loading for history
- Non-blocking user experience

### 4. Modular & Maintainable
- Follows existing codebase patterns
- Minimal code duplication
- Easy to test and extend

---

## 🔐 Security & Performance

### Security Enhancements
- Row-level security (users only see their projects)
- Audit trail for all matches/unmatches
- Encrypted sensitive data (NPWP, account numbers)
- Rate limiting on AI endpoints

### Performance Optimizations
- Database indexing for fast queries
- Lazy loading for large datasets
- Batch processing for AI calls
- Caching for repeated vendor matches
- Background jobs for auto-matching (don't block UI)

---

## 📈 Success Metrics

### KPIs to Track
1. **Match Rate**: Target 85%+ auto-match
2. **AI Accuracy**: Target 95%+ correct AI suggestions
3. **Processing Speed**: <3 seconds for 100 transactions
4. **User Time Savings**: 95% reduction vs manual
5. **AI Cost**: <$0.50 per project (token optimization)

---

## 🆚 Comparison: V1.0 vs V2.0

| Feature | V1.0 | V2.0 |
|---------|------|------|
| OCR Integration | Manual import | Direct from scan results |
| AI Models | GPT-4o only | GPT-4o + Claude (dual) |
| Vendor Matching | Exact string match | AI-powered fuzzy match |
| Invoice Extraction | Manual input | AI auto-extraction |
| Frontend Loading | Load all | Lazy loading |
| Performance | 100 items | 1000+ items |
| Code Reuse | New codebase | 70% reuse existing |

---

## ✅ Production Readiness Checklist

Before deploying to production:

- [ ] All database migrations tested
- [ ] API endpoints security reviewed
- [ ] AI prompts optimized for cost
- [ ] Frontend lazy loading working
- [ ] Excel export tested with real data
- [ ] Performance test with 1000+ items
- [ ] Integration tests passing
- [ ] User documentation complete
- [ ] Monitoring & logging in place
- [ ] Backup strategy defined

---

## 🚀 Next Steps

1. **Review this design** with team
2. **Approve AI integration strategy**
3. **Start Phase 1 implementation**
4. **Set up development database**
5. **Create first working prototype**

---

**Ready to implement? Let's build the best tax reconciliation system!** 🎉

