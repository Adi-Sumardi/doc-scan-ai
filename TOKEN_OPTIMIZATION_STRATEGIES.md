# Token Optimization Strategies Comparison
## Hemat Token untuk Rekening Koran 70+ Halaman

**Date**: 2025-10-17
**Purpose**: Compare different strategies to minimize GPT token usage

---

## 🎯 Problem Analysis

### Current Token Usage (Design Awal)

**Scenario**: 70 halaman, 2000 transaksi

```
OCR Output: ~140,000 tokens (70 pages × 2000 chars/page)
After Chunking: 40 chunks × 1000 tokens = 40,000 tokens
GPT Processing: 40 API calls × 1000 tokens input = 40,000 tokens

Total Input Tokens: ~40,000
Total Output Tokens: ~20,000 (assuming 500 tokens/chunk response)
Total Tokens: ~60,000 tokens

Cost Estimate:
Input: 40,000 × $0.0025/1K = $0.10
Output: 20,000 × $0.010/1K = $0.20
Total GPT Cost: $0.30 per document
```

**Ini sudah cukup hemat, tapi bisa lebih hemat lagi!**

---

## 💡 Alternative Strategies - Token Optimization

### Strategy 1: **CURRENT DESIGN (Hybrid RAG + Hierarchical)**
✅ Already implemented in design doc

**Pros**:
- ✅ Comprehensive extraction
- ✅ RAG capability for queries
- ✅ Good accuracy (95-98%)
- ✅ Scalable

**Cons**:
- ⚠️ Masih pakai GPT untuk semua chunks
- ⚠️ Medium cost (~$0.30/doc)

**Token Usage**: ~60,000 tokens
**Cost**: ~$0.30/doc

---

### Strategy 2: **STRUCTURED EXTRACTION FIRST (Minimal GPT)** ⭐ RECOMMENDED

**Core Idea**:
> Gunakan Document AI untuk extract 90% data tanpa GPT, hanya gunakan GPT untuk edge cases!

**Pipeline**:
```
1. Document AI → Extract structured tables (FREE extraction)
2. Rule-based Parser → Parse 90% transaksi (NO GPT!)
3. Smart Classifier → Detect problematic rows
4. GPT-4o Mini → Only process edge cases (~10% data)
5. Merge Results → Combine structured + GPT results
```

**Implementation**:

```python
class OptimizedBankProcessor:
    def __init__(self):
        self.doc_ai = DocumentAIProcessor()
        self.rule_parser = RuleBasedParser()
        self.gpt_mini = GPTMiniProcessor()  # Cheaper model

    async def process_document(self, pdf_path):
        """
        Hybrid approach: Structure first, GPT only for edge cases
        """
        # Step 1: Document AI - Extract structured tables
        ocr_result = await self.doc_ai.process(pdf_path)

        # Step 2: Rule-based parsing (NO GPT!)
        structured_txns = []
        edge_cases = []

        for table in ocr_result.tables:
            for row in table.rows:
                # Try rule-based extraction first
                txn = self.rule_parser.parse_row(row)

                if txn.confidence > 0.90:
                    # High confidence → No GPT needed!
                    structured_txns.append(txn)
                else:
                    # Low confidence → Flag for GPT
                    edge_cases.append(row)

        # Step 3: Use GPT only for edge cases (~10% of data)
        gpt_txns = []
        if len(edge_cases) > 0:
            # Batch edge cases to minimize API calls
            gpt_txns = await self.gpt_mini.process_batch(edge_cases)

        # Step 4: Merge results
        all_txns = structured_txns + gpt_txns

        return {
            "transactions": all_txns,
            "stats": {
                "structured_parsed": len(structured_txns),  # 90%
                "gpt_processed": len(gpt_txns),             # 10%
                "total": len(all_txns)
            }
        }


class RuleBasedParser:
    """
    Parse transaksi using regex & rules (NO GPT!)
    """
    def parse_row(self, row):
        """
        Extract transaction from table row using patterns
        """
        # Pattern 1: Date column
        date = self.extract_date(row.cells[0].text)

        # Pattern 2: Description
        keterangan = self.clean_text(row.cells[1].text)

        # Pattern 3: Debet/Kredit
        debet = self.extract_amount(row.cells[2].text)
        kredit = self.extract_amount(row.cells[3].text)

        # Pattern 4: Saldo
        saldo = self.extract_amount(row.cells[4].text)

        # Validate extraction
        confidence = self.calculate_confidence({
            "date": date,
            "keterangan": keterangan,
            "debet": debet,
            "kredit": kredit,
            "saldo": saldo
        })

        return Transaction(
            tanggal=date,
            keterangan=keterangan,
            debet=debet,
            kredit=kredit,
            saldo=saldo,
            confidence=confidence
        )

    def extract_date(self, text):
        """Extract date using regex patterns"""
        patterns = [
            r'\d{2}[/-]\d{2}[/-]\d{4}',  # DD/MM/YYYY
            r'\d{2}\s+[A-Za-z]{3}\s+\d{4}',  # 01 Jan 2024
            r'\d{1,2}\s+[A-Za-z]+\s+\d{4}'   # 1 Januari 2024
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self.normalize_date(match.group())

        return None

    def extract_amount(self, text):
        """Extract monetary amount using regex"""
        # Remove currency symbols and normalize
        cleaned = re.sub(r'[Rp\s]', '', text)
        cleaned = cleaned.replace('.', '').replace(',', '.')

        # Handle debit notation: (1.000) = -1000
        if '(' in cleaned:
            cleaned = '-' + cleaned.replace('(', '').replace(')', '')

        try:
            return float(cleaned)
        except:
            return None

    def calculate_confidence(self, data):
        """
        Calculate confidence score based on data completeness
        """
        score = 0.0

        # Check each field
        if data['date']: score += 0.25
        if data['keterangan']: score += 0.15
        if data['debet'] is not None or data['kredit'] is not None: score += 0.30
        if data['saldo']: score += 0.30

        return score
```

**Token Usage Calculation**:
```
Document AI OCR: 0 GPT tokens (uses Document AI API)
Rule-based parsing: 0 GPT tokens (pure Python)

Edge cases only (~10% of data):
  200 problematic rows × 100 tokens/row = 20,000 tokens

GPT-4o Mini processing:
  Input: 20,000 tokens × $0.00015/1K = $0.003
  Output: 10,000 tokens × $0.0006/1K = $0.006

Total GPT Cost: $0.009 per document ⚡

SAVINGS: 96% cheaper! ($0.30 → $0.009)
```

**Pros**:
- ✅ **96% cheaper** than Strategy 1
- ✅ **Faster** processing (no API calls for 90% data)
- ✅ **Deterministic** results for structured data
- ✅ Still maintains accuracy with GPT for edge cases

**Cons**:
- ⚠️ Requires good rule patterns (bank-specific)
- ⚠️ May need updates for new bank formats

**Best For**: Production systems with high volume

---

### Strategy 3: **TABLE-ONLY EXTRACTION (Zero GPT)** 💰 CHEAPEST

**Core Idea**:
> Document AI sudah punya Bank Statement Processor yang bisa extract tables! Zero GPT needed!

**Pipeline**:
```
1. Document AI Bank Statement Processor → Extract tables directly
2. Post-processing → Clean & normalize
3. Validation → Check saldo continuity
4. Export → Excel/JSON
```

**Implementation**:

```python
class TableOnlyProcessor:
    """
    Use Document AI's table extraction (NO GPT!)
    """
    async def process_document(self, pdf_path):
        # Use Document AI Bank Statement Processor
        processor_id = "bank-statement-processor"

        result = await self.doc_ai.process_document(
            pdf_path,
            processor_id=processor_id,
            processor_config={
                "extract_tables": True,
                "table_format": "structured"
            }
        )

        # Document AI returns structured tables!
        transactions = []

        for page in result.pages:
            for table in page.tables:
                # Table already has structured rows & columns
                for row in table.body_rows:
                    txn = {
                        "tanggal": row.cells[0].text,
                        "keterangan": row.cells[1].text,
                        "debet": self.parse_amount(row.cells[2].text),
                        "kredit": self.parse_amount(row.cells[3].text),
                        "saldo": self.parse_amount(row.cells[4].text)
                    }
                    transactions.append(txn)

        # Post-process (normalize dates, amounts)
        transactions = self.normalize_transactions(transactions)

        # Validate saldo continuity
        validation = self.validate_saldo_chain(transactions)

        return {
            "transactions": transactions,
            "validation": validation,
            "confidence": 0.85  # Slightly lower without GPT validation
        }
```

**Token Usage**:
```
GPT Tokens: 0
Document AI Cost: 70 pages × $0.015/page = $1.05

Total Cost: $1.05 per document
```

**Pros**:
- ✅ **ZERO GPT tokens**
- ✅ Fast processing
- ✅ Predictable costs
- ✅ Good for well-formatted statements

**Cons**:
- ⚠️ Lower accuracy (~85%) for complex formats
- ⚠️ No semantic understanding
- ⚠️ Struggles with multi-format banks

**Best For**: Well-formatted, consistent bank statements

---

### Strategy 4: **SMART SAMPLING (Intelligent Selection)** 🎯 BALANCED

**Core Idea**:
> Process first/last pages + sample middle pages with GPT. Interpolate the rest!

**Pipeline**:
```
1. Process Page 1 with GPT → Get metadata + first transactions
2. Process Last Page with GPT → Get final saldo
3. Smart Sampling → Select representative pages (every 10th page)
4. Process Samples with GPT → Extract pattern
5. Interpolate → Fill gaps with rule-based extraction
6. Validate → Check saldo matches
```

**Implementation**:

```python
class SmartSamplingProcessor:
    async def process_document(self, pdf_path, total_pages=70):
        """
        Process strategically selected pages only
        """
        # Step 1: Always process first page (metadata)
        page_1_result = await self.process_page_with_gpt(pdf_path, page=1)

        metadata = page_1_result['metadata']  # Bank, account, period
        saldo_awal = page_1_result['saldo_awal']

        # Step 2: Always process last page (final saldo)
        last_page_result = await self.process_page_with_gpt(pdf_path, page=total_pages)
        saldo_akhir = last_page_result['saldo_akhir']

        # Step 3: Smart sampling (every 10th page)
        sample_pages = [1, 10, 20, 30, 40, 50, 60, 70]
        sample_results = []

        for page_num in sample_pages:
            result = await self.process_page_with_gpt(pdf_path, page=page_num)
            sample_results.append(result)

        # Step 4: Learn pattern from samples
        pattern = self.learn_transaction_pattern(sample_results)

        # Step 5: Apply pattern to remaining pages (rule-based)
        all_transactions = []

        for page_num in range(1, total_pages + 1):
            if page_num in sample_pages:
                # Use GPT result
                all_transactions.extend(sample_results[sample_pages.index(page_num)]['transactions'])
            else:
                # Use learned pattern (no GPT!)
                ocr_text = await self.doc_ai.extract_page(pdf_path, page_num)
                txns = pattern.apply(ocr_text)
                all_transactions.extend(txns)

        # Step 6: Validate saldo continuity
        validation = self.validate_against_checkpoints(
            all_transactions,
            saldo_awal=saldo_awal,
            saldo_akhir=saldo_akhir,
            checkpoints=sample_results
        )

        return {
            "transactions": all_transactions,
            "validation": validation,
            "metadata": metadata
        }
```

**Token Usage**:
```
Pages processed with GPT: 8 out of 70 (11%)

GPT Processing:
  8 pages × 2000 chars × 1.3 (tokens) = ~20,800 tokens

Cost:
  Input: 20,800 × $0.0025/1K = $0.052
  Output: 10,000 × $0.010/1K = $0.10
  Total: $0.152

Total Cost: ~$0.15 per document

SAVINGS: 50% cheaper than Strategy 1
```

**Pros**:
- ✅ 50% token savings
- ✅ Still gets metadata from GPT
- ✅ Pattern learning improves over time
- ✅ Good balance of cost vs accuracy

**Cons**:
- ⚠️ May miss anomalies in unsampled pages
- ⚠️ Accuracy depends on pattern consistency

**Best For**: Consistent bank formats with predictable patterns

---

### Strategy 5: **PROGRESSIVE VALIDATION** 🔄 ADAPTIVE

**Core Idea**:
> Start rule-based, only call GPT when validation fails!

**Pipeline**:
```
1. Extract all with Document AI
2. Parse all with rules
3. Validate each chunk's saldo
4. IF validation fails → Call GPT for that chunk only
5. Merge results
```

**Implementation**:

```python
class ProgressiveValidator:
    async def process_document(self, pdf_path):
        """
        Adaptive approach: Use GPT only when needed
        """
        # Step 1: Extract all pages with Document AI
        ocr_result = await self.doc_ai.process(pdf_path)

        # Step 2: Parse all with rules
        chunks = self.chunk_by_saldo_context(ocr_result)

        validated_chunks = []
        gpt_processed_count = 0

        for i, chunk in enumerate(chunks):
            # Step 3: Try rule-based extraction
            result = self.rule_parser.parse_chunk(chunk)

            # Step 4: Validate saldo
            is_valid = self.validate_saldo(
                result,
                expected_saldo_start=chunks[i-1]['saldo_end'] if i > 0 else None
            )

            if is_valid and result['confidence'] > 0.90:
                # ✅ Validation passed → No GPT needed!
                validated_chunks.append(result)
            else:
                # ❌ Validation failed → Use GPT
                gpt_result = await self.gpt_processor.process_chunk(chunk)
                validated_chunks.append(gpt_result)
                gpt_processed_count += 1

        return {
            "transactions": self.merge_chunks(validated_chunks),
            "stats": {
                "total_chunks": len(chunks),
                "gpt_processed": gpt_processed_count,
                "rule_based": len(chunks) - gpt_processed_count,
                "gpt_percentage": (gpt_processed_count / len(chunks)) * 100
            }
        }
```

**Token Usage** (Adaptive):
```
Best Case (90% pass validation):
  GPT chunks: 4 out of 40
  Tokens: ~4,000
  Cost: ~$0.03

Average Case (70% pass validation):
  GPT chunks: 12 out of 40
  Tokens: ~12,000
  Cost: ~$0.09

Worst Case (50% pass validation):
  GPT chunks: 20 out of 40
  Tokens: ~20,000
  Cost: ~$0.15

Expected Average Cost: ~$0.09 per document

SAVINGS: 70% cheaper than Strategy 1
```

**Pros**:
- ✅ Adaptive cost (only pay for what you need)
- ✅ Self-improving (better rules = less GPT)
- ✅ High accuracy (GPT validates failures)
- ✅ Transparent (know which chunks used GPT)

**Cons**:
- ⚠️ Variable cost (unpredictable)
- ⚠️ Need good validation logic

**Best For**: Mixed-quality documents, improving systems

---

## 📊 Strategy Comparison Matrix

| Strategy | GPT Tokens | Cost/Doc | Accuracy | Speed | Best Use Case |
|----------|-----------|----------|----------|-------|---------------|
| **1. Hybrid RAG** | 60,000 | $0.30 | 95-98% | Medium | Complex queries, high accuracy needs |
| **2. Structured First** ⭐ | 6,000 | $0.01 | 92-95% | Fast | Production, high volume |
| **3. Table-Only** 💰 | 0 | $1.05* | 85-90% | Fastest | Well-formatted statements |
| **4. Smart Sampling** 🎯 | 20,000 | $0.15 | 90-93% | Medium | Consistent formats |
| **5. Progressive** 🔄 | 4,000-20,000 | $0.03-$0.15 | 93-96% | Fast | Mixed quality docs |

*Document AI cost only

---

## 🎯 RECOMMENDATIONS

### Recommended Approach: **HYBRID - Structured First + Progressive Validation** ⭐

**Why?**
- ✅ Best cost/accuracy balance
- ✅ 90%+ documents processed without GPT
- ✅ GPT validates only edge cases
- ✅ Production-ready

**Implementation Strategy**:

```python
class OptimalBankProcessor:
    """
    Combines Strategy 2 + Strategy 5
    """
    async def process_document(self, pdf_path):
        # Phase 1: Structure First (Strategy 2)
        structured_result = await self.structured_extractor.process(pdf_path)

        # Phase 2: Progressive Validation (Strategy 5)
        validated_result = await self.progressive_validator.validate(
            structured_result
        )

        return validated_result
```

**Expected Metrics**:
- **Cost**: $0.01 - $0.05 per document (95% savings!)
- **Accuracy**: 93-96%
- **Speed**: 30-60 seconds per document
- **Token Usage**: 4,000 - 10,000 tokens (instead of 60,000)

---

## 🔧 Implementation Priority

### Phase 1: Quick Win (Week 1)
✅ Implement **Strategy 2 (Structured First)**
- Build rule-based parser for common banks
- Test with BCA, Mandiri, BNI statements
- Measure accuracy vs current system

### Phase 2: Refinement (Week 2)
✅ Add **Strategy 5 (Progressive Validation)**
- Implement saldo validation
- Add GPT fallback for failures
- Track GPT usage percentage

### Phase 3: Optimization (Week 3)
✅ Fine-tune rules based on real data
- Learn from GPT corrections
- Update rule patterns
- Reduce GPT usage to <5%

---

## 💡 Additional Token-Saving Tricks

### 1. Use GPT-4o-mini for Simple Cases
```python
# For edge cases that don't need reasoning
if complexity_score < 0.5:
    model = "gpt-4o-mini"  # 60% cheaper
else:
    model = "gpt-4o"
```

### 2. Batch Processing
```python
# Instead of 40 separate API calls
# Batch similar chunks together
batched_chunks = self.batch_similar_chunks(chunks, batch_size=5)

for batch in batched_chunks:
    # 1 API call for 5 chunks
    result = await gpt.process_batch(batch)
```

### 3. Prompt Compression
```python
# Instead of sending full OCR text
original_prompt = f"Extract transactions from: {full_ocr_text}"  # 5000 tokens

# Use compressed format
compressed_prompt = f"Extract from table: {table_only}"  # 800 tokens

# 84% token reduction!
```

### 4. Response Format Optimization
```python
# Instead of verbose JSON
{
  "transaction_date": "2024-01-01",
  "transaction_description": "Transfer to BCA",
  "debit_amount": 1000000,
  "credit_amount": 0,
  "balance_amount": 5000000
}

# Use compact format
["2024-01-01", "Transfer to BCA", 1000000, 0, 5000000]

# 60% token reduction in responses!
```

---

## 🎬 Next Steps

1. **Choose Strategy** - Recommend **Structured First + Progressive**
2. **Build POC** - Test with 1-2 real bank statements
3. **Measure Metrics**:
   - Token usage
   - Cost per document
   - Accuracy vs current system
   - Processing time
4. **Iterate** - Refine rules based on results
5. **Scale** - Roll out to production

---

## 📈 Expected ROI

**Current System** (using full GPT):
- 100 documents/day × $0.30 = $30/day = $900/month

**Optimized System** (Structured First):
- 100 documents/day × $0.02 = $2/day = $60/month

**Savings**: $840/month (93% reduction) 💰

---

**End of Analysis**