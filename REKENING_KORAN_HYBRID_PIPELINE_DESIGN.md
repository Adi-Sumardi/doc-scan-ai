# Rekening Koran Hybrid Pipeline Design
## RAG + Hierarchical Summarization for Large Bank Statements (70+ pages)

**Author**: AI Design Team
**Date**: 2025-10-17
**Version**: 1.0
**Status**: Design Phase

---

## 🎯 Problem Statement

### Current Challenges
1. **Volume Problem**: Rekening koran 70+ halaman berisi ribuan transaksi
2. **Token Limit**: GPT-4o limit 16K tokens → tidak bisa proses semua halaman sekaligus
3. **Context Loss**: Kehilangan konteks saldo antar halaman
4. **Cost & Time**: Biaya dan waktu tinggi jika semua halaman di-process ke GPT
5. **OCR Output**: Hasil OCR besar dan tidak efisien jika langsung ke GPT

### Success Criteria
✅ Process rekening koran 70+ halaman tanpa token limit error
✅ Maintain saldo consistency antar halaman
✅ Extract semua transaksi dengan akurat (95%+ accuracy)
✅ Cost-efficient (hemat token GPT)
✅ Processing time maksimal 2-3 menit per dokumen
✅ Scalable untuk batch processing

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    REKENING KORAN HYBRID PIPELINE                   │
└─────────────────────────────────────────────────────────────────────┘

                            📄 PDF Upload
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │  🧾 OCR & Layout Parsing                   │
        │  ► Google Document AI (Bank Statement)     │
        │  ► Extract: Pages, Tables, Text Blocks     │
        └────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │  🧹 Preprocessing & Cleaning               │
        │  ► Normalize dates, amounts, formats       │
        │  ► Detect bank, account, period            │
        │  ► Extract saldo awal/akhir per page       │
        └────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │  🔀 Logical Chunking                       │
        │  ► Group by saldo context (not by page)    │
        │  ► Each chunk ~500-1000 tokens             │
        │  ► Preserve saldo chain                    │
        └────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌──────────────────┐      ┌──────────────────┐
        │  🧬 Vector DB     │      │  🤖 Smart Mapper │
        │  ► Embeddings     │      │  ► GPT-4o        │
        │  ► RAG Ready      │      │  ► Per Chunk     │
        └──────────────────┘      └──────────────────┘
                    │                         │
                    └────────────┬────────────┘
                                 ▼
        ┌────────────────────────────────────────────┐
        │  🪜 Hierarchical Summarization             │
        │  ► Merge chunk results                     │
        │  ► Validate saldo continuity               │
        │  ► Generate global summary                 │
        └────────────────────────────────────────────┘
                                 │
                                 ▼
        ┌────────────────────────────────────────────┐
        │  📊 Output & Export                        │
        │  ► Excel (formatted)                       │
        │  ► JSON (API response)                     │
        │  ► Summary Report                          │
        └────────────────────────────────────────────┘
```

---

## 📋 Detailed Pipeline Stages

### Stage 1: OCR & Layout Parsing

**Objective**: Extract structured data from PDF rekening koran

**Tools**:
- **Primary**: Google Document AI (Bank Statement Processor)
- **Fallback**: Azure Form Recognizer / Textract

**Process**:
```python
# Input: PDF file (70+ pages)
# Output: Structured JSON with pages, tables, text blocks

{
  "pages": [
    {
      "page_number": 1,
      "tables": [
        {
          "headers": ["Tanggal", "Keterangan", "Debet", "Kredit", "Saldo"],
          "rows": [...]
        }
      ],
      "text_blocks": {
        "header": "Bank BCA - Rekening Koran",
        "account_info": "No. Rek: 1234567890",
        "period": "01 Jan 2024 - 31 Jan 2024",
        "saldo_awal": "100000000",
        "saldo_akhir": "120000000"
      }
    }
  ]
}
```

**Output**:
- Structured JSON per page
- Table data extracted
- Metadata (bank name, account number, period)
- Saldo awal/akhir per page

---

### Stage 2: Preprocessing & Cleaning

**Objective**: Normalize and clean extracted data

**Tools**:
- Python (Pandas, Regex)
- Custom normalization functions

**Process**:
```python
# 1. Normalize dates
"01-Jan-2024" → "2024-01-01"
"1/1/24" → "2024-01-01"

# 2. Normalize amounts
"1.000.000,00" → "1000000.00"
"Rp 1.000.000" → "1000000.00"
"(100.000)" → "-100000.00"  # debit notation

# 3. Detect patterns
- Saldo awal/akhir per page
- Saldo lalu/baru
- Transfer antar halaman

# 4. Clean keterangan
Remove extra spaces, normalize abbreviations
"TRF KE  REK  123" → "TRF KE REK 123"
```

**Output**:
- Clean, normalized transaction data
- Detected metadata (bank, account, period)
- Saldo chain mapping

---

### Stage 3: Logical Chunking

**Objective**: Split dokumen berdasarkan konteks logis, bukan halaman

**Strategy**:

**❌ WRONG: Split by Page**
```
Page 1 (30 transactions) → Chunk 1
Page 2 (30 transactions) → Chunk 2
Page 3 (30 transactions) → Chunk 3
❌ Lost context between pages!
```

**✅ CORRECT: Split by Saldo Context**
```
Chunk 1: Saldo Awal → 50 transactions → Saldo Checkpoint 1
Chunk 2: Saldo Checkpoint 1 → 50 transactions → Saldo Checkpoint 2
Chunk 3: Saldo Checkpoint 2 → 50 transactions → Saldo Akhir
✅ Context preserved!
```

**Implementation**:
```python
class LogicalChunker:
    def __init__(self, max_tokens=1000):
        self.max_tokens = max_tokens

    def chunk_by_saldo_context(self, transactions, saldo_awal):
        """
        Group transactions logically:
        - Start with saldo_awal
        - Add transactions until ~1000 tokens
        - Save saldo checkpoint
        - Next chunk starts with checkpoint
        """
        chunks = []
        current_chunk = []
        current_saldo = saldo_awal
        current_tokens = 0

        for txn in transactions:
            txn_tokens = estimate_tokens(txn)

            if current_tokens + txn_tokens > self.max_tokens:
                # Save chunk with saldo checkpoint
                chunks.append({
                    "saldo_start": current_saldo,
                    "transactions": current_chunk,
                    "saldo_end": calculate_saldo(current_chunk, current_saldo)
                })

                # Start new chunk
                current_saldo = chunks[-1]["saldo_end"]
                current_chunk = []
                current_tokens = 0

            current_chunk.append(txn)
            current_tokens += txn_tokens

        return chunks
```

**Output**:
- Logical chunks with saldo context
- Each chunk ~500-1000 tokens
- Preserved saldo chain

---

### Stage 4: Vector Embedding + RAG

**Objective**: Enable retrieval of relevant transactions without processing all data

**Tools**:
- **Embedding Model**: OpenAI `text-embedding-3-large`
- **Vector DB**: Pinecone / Weaviate / Supabase Vector / Chroma

**When to Use RAG**:
- ✅ User queries: "Cari transaksi transfer ke BCA bulan Januari"
- ✅ Anomaly detection: "Cari transaksi di atas 10 juta"
- ✅ Filtering: "Tampilkan transaksi kategori tertentu"

**Process**:
```python
# 1. Generate embeddings for each transaction
for txn in all_transactions:
    embedding = openai.embeddings.create(
        model="text-embedding-3-large",
        input=f"{txn['tanggal']} {txn['keterangan']} {txn['amount']}"
    )

    # 2. Store in vector DB
    vector_db.upsert(
        id=txn['id'],
        vector=embedding,
        metadata={
            "tanggal": txn['tanggal'],
            "keterangan": txn['keterangan'],
            "amount": txn['amount'],
            "saldo": txn['saldo'],
            "page": txn['page']
        }
    )

# 3. Query vector DB
query = "Transfer ke rekening BCA bulan Januari 2024"
results = vector_db.query(
    query_vector=openai.embeddings.create(input=query),
    top_k=10
)
```

**Output**:
- Vector database dengan semua transaksi
- Fast retrieval untuk queries
- Metadata preserved

---

### Stage 5: Smart Mapping & Reasoning (GPT-4o)

**Objective**: Extract transaksi per chunk dengan GPT-4o

**Strategy**: Process each chunk sequentially with saldo context

**Process**:
```python
class ChunkProcessor:
    def __init__(self, model="gpt-4o"):
        self.model = model

    async def process_chunk(self, chunk, previous_saldo):
        """
        Process chunk with context from previous chunk
        """
        prompt = f"""
You are processing a bank statement chunk.

**Previous Saldo**: Rp {previous_saldo:,.2f}

**Transactions in this chunk**:
{chunk['raw_text']}

**Task**:
1. Extract all transactions in JSON format
2. Validate saldo continuity from previous chunk
3. Calculate running saldo for each transaction
4. Flag any anomalies or errors

**Output Format**:
{{
  "saldo_start": {previous_saldo},
  "transactions": [
    {{
      "tanggal": "2024-01-01",
      "keterangan": "Transfer masuk",
      "debet": 0,
      "kredit": 1000000,
      "saldo": 101000000
    }}
  ],
  "saldo_end": <calculated>,
  "validation": {{
    "saldo_match": true/false,
    "errors": []
  }}
}}
"""

        response = await openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a bank statement processor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        return json.loads(response.choices[0].message.content)
```

**Key Features**:
- ✅ Sequential processing dengan saldo context
- ✅ Validation per chunk
- ✅ Error detection
- ✅ Running saldo calculation

**Output**:
- Extracted transactions per chunk
- Validated saldo chain
- Error/anomaly flags

---

### Stage 6: Hierarchical Summarization

**Objective**: Merge semua chunk results menjadi final output

**Process**:
```python
class HierarchicalSummarizer:
    def merge_chunks(self, chunk_results):
        """
        Merge all chunk results with validation
        """
        all_transactions = []
        saldo_chain = []
        errors = []

        for i, chunk_result in enumerate(chunk_results):
            # 1. Validate saldo continuity
            if i > 0:
                expected_saldo = chunk_results[i-1]['saldo_end']
                actual_saldo = chunk_result['saldo_start']

                if expected_saldo != actual_saldo:
                    errors.append({
                        "chunk": i,
                        "error": "Saldo mismatch",
                        "expected": expected_saldo,
                        "actual": actual_saldo
                    })

            # 2. Merge transactions
            all_transactions.extend(chunk_result['transactions'])

            # 3. Track saldo chain
            saldo_chain.append({
                "chunk": i,
                "saldo_start": chunk_result['saldo_start'],
                "saldo_end": chunk_result['saldo_end']
            })

        # 4. Generate summary
        summary = self.generate_summary(all_transactions)

        return {
            "total_transactions": len(all_transactions),
            "transactions": all_transactions,
            "saldo_chain": saldo_chain,
            "summary": summary,
            "errors": errors,
            "validation": {
                "saldo_match": len(errors) == 0,
                "completeness": self.check_completeness(all_transactions)
            }
        }

    def generate_summary(self, transactions):
        """
        Generate high-level summary
        """
        df = pd.DataFrame(transactions)

        return {
            "total_debet": df['debet'].sum(),
            "total_kredit": df['kredit'].sum(),
            "net_change": df['kredit'].sum() - df['debet'].sum(),
            "transaction_count": len(df),
            "date_range": {
                "start": df['tanggal'].min(),
                "end": df['tanggal'].max()
            },
            "top_categories": df.groupby('category')['amount'].sum().nlargest(5).to_dict()
        }
```

**Output**:
- Complete transaction list
- Validated saldo chain
- High-level summary
- Error report (if any)

---

### Stage 7: Output & Export

**Objective**: Export hasil ke berbagai format

**Formats**:

#### 1. Excel Export
```python
def export_to_excel(data, output_path):
    """
    Export to formatted Excel
    """
    wb = Workbook()

    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Summary"
    ws_summary.append(["Bank", data['bank_info']['nama_bank']])
    ws_summary.append(["Account", data['bank_info']['nomor_rekening']])
    ws_summary.append(["Period", data['bank_info']['periode']])
    ws_summary.append(["Total Transactions", data['total_transactions']])
    ws_summary.append(["Total Debet", data['summary']['total_debet']])
    ws_summary.append(["Total Kredit", data['summary']['total_kredit']])

    # Sheet 2: Transactions
    ws_txn = wb.create_sheet("Transactions")
    ws_txn.append(["Tanggal", "Keterangan", "Debet", "Kredit", "Saldo"])

    for txn in data['transactions']:
        ws_txn.append([
            txn['tanggal'],
            txn['keterangan'],
            txn['debet'],
            txn['kredit'],
            txn['saldo']
        ])

    # Sheet 3: Saldo Chain (for validation)
    ws_saldo = wb.create_sheet("Saldo Chain")
    ws_saldo.append(["Chunk", "Saldo Start", "Saldo End"])

    for chain in data['saldo_chain']:
        ws_saldo.append([chain['chunk'], chain['saldo_start'], chain['saldo_end']])

    wb.save(output_path)
```

#### 2. JSON API Response
```json
{
  "document_id": "uuid",
  "document_type": "rekening_koran",
  "bank_info": {
    "nama_bank": "Bank BCA",
    "nomor_rekening": "1234567890",
    "nama_pemilik": "PT Example",
    "periode": "01 Jan 2024 - 31 Dec 2024"
  },
  "saldo_info": {
    "saldo_awal": "100000000",
    "saldo_akhir": "120000000",
    "mata_uang": "IDR"
  },
  "transactions": [...],
  "summary": {
    "total_transactions": 2000,
    "total_debet": "500000000",
    "total_kredit": "520000000",
    "net_change": "20000000"
  },
  "metadata": {
    "processing_time": "120s",
    "chunks_processed": 40,
    "confidence": 0.95,
    "errors": []
  }
}
```

---

## 🛠️ Tech Stack

### Required Libraries & Services

| Component | Tool/Service | Purpose |
|-----------|--------------|---------|
| **OCR** | Google Document AI | Extract structured data from PDF |
| **PDF Processing** | PyPDF2, pdf2image | PDF manipulation |
| **Data Processing** | Pandas, NumPy | Data normalization & analysis |
| **Embedding** | OpenAI Embedding API | Generate vector embeddings |
| **Vector DB** | Pinecone / Weaviate / Chroma | Store & retrieve embeddings |
| **LLM** | OpenAI GPT-4o | Smart mapping & reasoning |
| **Orchestration** | LangChain | Chain management |
| **Export** | openpyxl, ReportLab | Excel & PDF generation |
| **Async** | Celery + Redis | Background task processing |
| **API** | FastAPI | REST API endpoints |

### Python Dependencies
```txt
# requirements.txt
google-cloud-documentai>=2.20.0
openai>=1.12.0
pinecone-client>=3.0.0  # or weaviate-client or chromadb
langchain>=0.1.0
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0
PyPDF2>=3.0.0
pdf2image>=1.16.0
celery>=5.3.0
redis>=5.0.0
fastapi>=0.109.0
pydantic>=2.5.0
```

---

## 📊 Performance Estimates

### Processing Metrics

| Metric | Estimate |
|--------|----------|
| **Processing Speed** | ~500-1000 transactions/minute |
| **Cost per Document** | ~$0.50 - $2.00 (70 pages) |
| **Accuracy** | 95-98% transaction extraction |
| **Saldo Accuracy** | 99%+ (with validation) |
| **Max Pages Supported** | Unlimited (with chunking) |

### Cost Breakdown (70-page document)

```
OCR (Google Document AI):
  70 pages × $0.015/page = $1.05

Embeddings (if using RAG):
  ~2000 transactions × $0.0001/1K tokens = $0.20

GPT-4o Processing:
  40 chunks × 1000 tokens/chunk × $0.0025/1K tokens = $0.10

Total Estimated Cost: ~$1.35 per document
```

---

## 🔄 API Endpoints

### Endpoint Design

```python
# POST /api/upload/rekening-koran-large
"""
Upload large rekening koran for hybrid processing
"""
{
  "file": "binary_data",
  "processing_options": {
    "enable_rag": true,
    "chunk_size": 1000,
    "use_hierarchical": true
  }
}

# Response
{
  "batch_id": "uuid",
  "status": "processing",
  "estimated_time": "120s"
}

# GET /api/batches/{batch_id}/status
"""
Check processing status
"""
{
  "batch_id": "uuid",
  "status": "processing",
  "progress": {
    "current_chunk": 15,
    "total_chunks": 40,
    "percentage": 37.5
  }
}

# GET /api/batches/{batch_id}/results
"""
Get final results
"""
{
  "batch_id": "uuid",
  "status": "completed",
  "results": {
    "document_id": "uuid",
    "transactions": [...],
    "summary": {...},
    "saldo_chain": [...]
  }
}

# POST /api/rekening-koran/query
"""
RAG query for specific transactions
"""
{
  "document_id": "uuid",
  "query": "Cari transaksi transfer ke BCA bulan Januari",
  "top_k": 10
}

# Response
{
  "results": [
    {
      "transaction": {...},
      "relevance_score": 0.95
    }
  ]
}
```

---

## 🧪 Testing Strategy

### Test Cases

#### 1. Unit Tests
```python
# test_chunker.py
def test_logical_chunking():
    transactions = generate_test_transactions(100)
    chunker = LogicalChunker(max_tokens=1000)
    chunks = chunker.chunk_by_saldo_context(transactions, saldo_awal=1000000)

    # Verify saldo continuity
    for i in range(len(chunks) - 1):
        assert chunks[i]['saldo_end'] == chunks[i+1]['saldo_start']

# test_normalizer.py
def test_amount_normalization():
    assert normalize_amount("1.000.000,00") == 1000000.00
    assert normalize_amount("Rp 1.000.000") == 1000000.00
    assert normalize_amount("(100.000)") == -100000.00
```

#### 2. Integration Tests
```python
# test_pipeline.py
@pytest.mark.asyncio
async def test_full_pipeline():
    # Test with sample 70-page PDF
    result = await process_large_rekening_koran("test_70pages.pdf")

    assert result['total_transactions'] > 0
    assert result['validation']['saldo_match'] == True
    assert result['metadata']['chunks_processed'] > 0
```

#### 3. Load Tests
```python
# Test concurrent processing
async def test_concurrent_processing():
    tasks = [
        process_large_rekening_koran(f"test_{i}.pdf")
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks)
    assert all(r['status'] == 'completed' for r in results)
```

---

## 📈 Monitoring & Logging

### Metrics to Track

```python
# metrics.py
class PipelineMetrics:
    def __init__(self):
        self.metrics = {
            "ocr_time": [],
            "chunking_time": [],
            "gpt_processing_time": [],
            "total_time": [],
            "chunks_processed": [],
            "transactions_extracted": [],
            "errors": [],
            "saldo_mismatches": []
        }

    def log_processing(self, stage, duration, metadata=None):
        logger.info(f"[{stage}] Completed in {duration:.2f}s", extra=metadata)
        self.metrics[f"{stage}_time"].append(duration)
```

### Logging Strategy

```python
# Structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "chunk_processed",
    chunk_id=chunk_id,
    transactions_count=len(transactions),
    saldo_start=saldo_start,
    saldo_end=saldo_end,
    validation_status="passed",
    processing_time=duration
)
```

---

## 🚀 Implementation Roadmap

### Phase 1: Core Pipeline (Week 1-2)
- [ ] Setup Document AI integration
- [ ] Implement preprocessing & normalization
- [ ] Build logical chunker
- [ ] Integrate GPT-4o smart mapper
- [ ] Implement hierarchical summarizer

### Phase 2: RAG Integration (Week 3)
- [ ] Setup vector database (Pinecone/Weaviate)
- [ ] Implement embedding generation
- [ ] Build query interface
- [ ] Test retrieval accuracy

### Phase 3: API & Export (Week 4)
- [ ] Build FastAPI endpoints
- [ ] Implement Excel export
- [ ] Add progress tracking
- [ ] Setup Celery for async processing

### Phase 4: Testing & Optimization (Week 5)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load testing
- [ ] Performance optimization

### Phase 5: Production Deployment (Week 6)
- [ ] Deploy to GCP/AWS
- [ ] Setup monitoring
- [ ] Documentation
- [ ] User training

---

## 💡 Best Practices

### 1. Error Handling
```python
class PipelineError(Exception):
    """Base exception for pipeline errors"""
    pass

class SaldoMismatchError(PipelineError):
    """Raised when saldo doesn't match between chunks"""
    pass

# Graceful degradation
try:
    result = await process_chunk(chunk)
except SaldoMismatchError as e:
    logger.warning(f"Saldo mismatch detected: {e}")
    # Try to reconcile or flag for manual review
    result = await reconcile_saldo(chunk, previous_chunk)
```

### 2. Caching
```python
# Cache OCR results
@cache(ttl=3600)
async def get_ocr_result(document_id):
    return await document_ai.process(document_id)

# Cache embeddings
@cache(ttl=86400)
async def get_embedding(text):
    return await openai.embeddings.create(input=text)
```

### 3. Rate Limiting
```python
# Respect API rate limits
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_gpt_with_retry(prompt):
    return await openai.chat.completions.create(...)
```

---

## 🎯 Success Metrics

### KPIs to Track

| KPI | Target | Measurement |
|-----|--------|-------------|
| **Extraction Accuracy** | 95%+ | Manual validation of sample |
| **Saldo Accuracy** | 99%+ | Automated validation |
| **Processing Time** | <3 min/doc | Pipeline metrics |
| **Cost per Document** | <$2.00 | API usage tracking |
| **Error Rate** | <5% | Error logs |
| **User Satisfaction** | 4.5/5 | User feedback |

---

## 📚 References & Resources

### Documentation
- [Google Document AI - Bank Statement Parser](https://cloud.google.com/document-ai/docs/processors-list#processor_bank-statement-processor)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [Pinecone Vector Database](https://docs.pinecone.io/)

### Related Files
- `backend/ai_processor.py` - Current AI processor
- `backend/cloud_ai_processor.py` - Document AI integration
- `backend/smart_mapper.py` - Smart mapping logic
- `backend/pdf_chunker.py` - Current PDF chunking (page-based)

---

## ✅ Next Steps

1. **Review Design** - Get approval on architecture
2. **Proof of Concept** - Build minimal pipeline with 1 test document
3. **Iterate** - Refine based on POC results
4. **Full Implementation** - Build complete pipeline
5. **Testing** - Comprehensive testing with real documents
6. **Deployment** - Production rollout

---

**End of Design Document**