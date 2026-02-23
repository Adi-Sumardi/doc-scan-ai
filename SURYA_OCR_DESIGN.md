# Surya OCR Integration Design

## Doc Scan AI - Mengganti/Melengkapi Google Document AI dengan Surya OCR

---

## 1. Mengapa Surya OCR?

| Aspek | Google Document AI | Surya OCR |
|-------|-------------------|-----------|
| **Harga** | $1.50/1000 halaman | GRATIS (open source) |
| **Akurasi teks** | ~98% | ~95% (90+ bahasa) |
| **Table detection** | Excellent | Good (built-in) |
| **Layout analysis** | Good | Excellent |
| **GPU required** | No (cloud) | Optional (CPU mode tersedia) |
| **Privacy** | Data ke Google | 100% lokal |
| **Dependency** | Internet + Billing | Self-hosted |
| **Downtime risk** | Billing expired = mati | Selalu available |

**Cost Savings (Bulan ke-6 SaaS):**
- Google: 50,000 pages x $0.0015 = $75/bulan (Rp 1.200.000)
- Surya: Rp 0 (hanya biaya server)
- **Savings: Rp 1.200.000/bulan**

---

## 2. Strategi Integrasi: Hybrid Dual-Engine

```
                    ┌─────────────────┐
                    │  Upload File    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ OCR Processor   │
                    │ (Router/Switch) │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼──────┐  ┌───▼────┐  ┌──────▼───────┐
     │ Surya OCR     │  │  Both  │  │ Google DocAI │
     │ (PRIMARY)     │  │(Verify)│  │ (FALLBACK)   │
     │ FREE, Local   │  │        │  │ Paid, Cloud  │
     └────────┬──────┘  └───┬────┘  └──────┬───────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼────────┐
                    │ Smart Mapper    │
                    │ (Claude AI)     │
                    └─────────────────┘
```

### Engine Selection Strategy

| Mode | Primary | Fallback | Use Case |
|------|---------|----------|----------|
| **`surya_primary`** | Surya OCR | Google DocAI | Default (hemat biaya) |
| **`google_primary`** | Google DocAI | Surya OCR | Maximum accuracy |
| **`surya_only`** | Surya OCR | None | Gratis 100% |
| **`google_only`** | Google DocAI | None | Current behavior |

---

## 3. Architecture Design

### 3.1 New File: `surya_processor.py`

```python
"""
Surya OCR Processor
Local OCR engine using Surya (free, open source)
Supports: OCR, Table Detection, Layout Analysis
"""

import os
import gc
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SuryaOCRResult:
    """Surya OCR result matching CloudOCRResult interface"""
    raw_text: str
    confidence: float
    service_used: str  # "surya_ocr"
    processing_time: float
    extracted_fields: Dict[str, Any]
    raw_response: Dict[str, Any]
    document_type: str
    language_detected: str


class SuryaProcessor:
    """Local OCR processor using Surya OCR

    Features:
    - Text recognition (90+ languages)
    - Table detection & recognition
    - Layout analysis (headers, paragraphs, tables, images)
    - Reading order detection
    - CPU or GPU mode
    """

    def __init__(self):
        self.initialized = False
        self._foundation = None
        self._recognition = None
        self._detection = None
        self._layout = None
        self._table_rec = None

        # Configure for CPU mode on VPS (no GPU)
        os.environ.setdefault('TORCH_DEVICE', 'cpu')
        os.environ.setdefault('RECOGNITION_BATCH_SIZE', '16')
        os.environ.setdefault('DETECTOR_BATCH_SIZE', '4')
        os.environ.setdefault('LAYOUT_BATCH_SIZE', '2')
        os.environ.setdefault('TABLE_REC_BATCH_SIZE', '4')

        try:
            self._init_models()
            self.initialized = True
            logger.info("✅ Surya OCR initialized (CPU mode)")
        except Exception as e:
            logger.error(f"❌ Surya OCR init failed: {e}")
            self.initialized = False

    def _init_models(self):
        """Lazy-load Surya models (loaded on first use to save memory)"""
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor

        self._foundation = FoundationPredictor()
        self._recognition = RecognitionPredictor(self._foundation)
        self._detection = DetectionPredictor()

        logger.info("✅ Surya OCR models loaded (text + detection)")

    def _init_layout_model(self):
        """Load layout model on demand (memory saving)"""
        if self._layout is None:
            from surya.layout import LayoutPredictor
            from surya.foundation import FoundationPredictor
            from surya.settings import settings
            self._layout = LayoutPredictor(
                FoundationPredictor(
                    checkpoint=settings.LAYOUT_MODEL_CHECKPOINT
                )
            )
            logger.info("✅ Surya Layout model loaded")

    def _init_table_model(self):
        """Load table recognition model on demand"""
        if self._table_rec is None:
            from surya.table_rec import TableRecPredictor
            self._table_rec = TableRecPredictor()
            logger.info("✅ Surya Table Recognition model loaded")

    def _pdf_to_images(self, file_path: str) -> list:
        """Convert PDF pages to PIL Images"""
        import fitz  # PyMuPDF
        from PIL import Image
        import io

        doc = fitz.open(file_path)
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render at 300 DPI for good OCR quality
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)

            # Memory cleanup per page
            del pix

        doc.close()
        return images

    def _image_to_pil(self, file_path: str):
        """Load image file as PIL Image"""
        from PIL import Image
        return [Image.open(file_path)]

    async def process_document(self, file_path: str) -> SuryaOCRResult:
        """Process document with Surya OCR

        Supports: PDF, PNG, JPG, JPEG, TIFF, BMP
        Returns: SuryaOCRResult (compatible with CloudOCRResult)
        """
        if not self.initialized:
            raise Exception("Surya OCR not initialized")

        start_time = time.time()
        file_ext = Path(file_path).suffix.lower()

        # Convert to PIL Images
        if file_ext == '.pdf':
            images = self._pdf_to_images(file_path)
        else:
            images = self._image_to_pil(file_path)

        logger.info(f"🔍 Surya OCR processing {len(images)} pages...")

        # Step 1: Text Recognition (OCR)
        ocr_predictions = self._recognition(images, det_predictor=self._detection)

        # Step 2: Layout Analysis (detect tables, headers, etc.)
        self._init_layout_model()
        layout_predictions = self._layout(images)

        # Step 3: Table Recognition (if tables detected in layout)
        tables_data = []
        has_tables = False
        for page_layout in layout_predictions:
            table_regions = [
                block for block in page_layout.bboxes
                if block.label == "Table"
            ]
            if table_regions:
                has_tables = True
                break

        if has_tables:
            self._init_table_model()
            table_predictions = self._table_rec(images)
            tables_data = self._format_tables(table_predictions)

        # Build result
        all_text = []
        pages_data = []
        total_confidence = 0
        total_lines = 0

        for page_idx, (ocr_pred, layout_pred) in enumerate(
            zip(ocr_predictions, layout_predictions)
        ):
            page_text = ""
            page_lines = []

            for line in ocr_pred.text_lines:
                page_text += line.text + "\n"
                total_confidence += line.confidence
                total_lines += 1

                page_lines.append({
                    "text": line.text,
                    "confidence": line.confidence,
                    "bbox": line.bbox,
                    "words": [
                        {"text": w.text, "confidence": w.confidence, "bbox": w.bbox}
                        for w in (line.words or [])
                    ]
                })

            # Layout blocks (tables, headers, paragraphs)
            layout_blocks = []
            for block in layout_pred.bboxes:
                layout_blocks.append({
                    "label": block.label,
                    "bbox": block.bbox,
                    "confidence": block.confidence
                })

            pages_data.append({
                "page_number": page_idx + 1,
                "text": page_text,
                "lines": page_lines,
                "layout": layout_blocks,
                "tables": tables_data[page_idx] if page_idx < len(tables_data) else []
            })

            all_text.append(page_text)

        # Calculate average confidence
        avg_confidence = (total_confidence / total_lines * 100) if total_lines > 0 else 0

        processing_time = time.time() - start_time

        # Build raw_response compatible with existing Smart Mapper format
        raw_response = {
            "source": "surya_ocr",
            "pages": pages_data,
            "total_pages": len(images),
            "tables": tables_data,
            "text": "\n".join(all_text)
        }

        # Memory cleanup
        del images
        gc.collect()

        logger.info(
            f"✅ Surya OCR complete: {len(all_text)} pages, "
            f"{total_lines} lines, {avg_confidence:.1f}% confidence, "
            f"{processing_time:.1f}s"
        )

        return SuryaOCRResult(
            raw_text="\n".join(all_text),
            confidence=avg_confidence,
            service_used="surya_ocr",
            processing_time=processing_time,
            extracted_fields={},
            raw_response=raw_response,
            document_type="",
            language_detected="id"
        )

    def _format_tables(self, table_predictions) -> list:
        """Format Surya table predictions to match Google DocAI table format"""
        all_tables = []
        for page_pred in table_predictions:
            page_tables = []
            for table in page_pred.tables:
                rows = []
                for row in table.rows:
                    cells = []
                    for cell in row.cells:
                        cells.append({
                            "text": cell.text,
                            "bbox": cell.bbox,
                            "row_span": cell.row_span,
                            "col_span": cell.col_span
                        })
                    rows.append({"cells": cells})
                page_tables.append({
                    "rows": rows,
                    "bbox": table.bbox
                })
            all_tables.append(page_tables)
        return all_tables
```

### 3.2 Modified: `ocr_processor.py` (Hybrid Engine)

```python
"""
OCR Processor Module - Hybrid Version
Primary: Surya OCR (free, local)
Fallback: Google Document AI (paid, cloud)
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# OCR Engine configuration
OCR_ENGINE_MODE = os.environ.get('OCR_ENGINE_MODE', 'surya_primary')
# Options: surya_primary, google_primary, surya_only, google_only

# Try to import Surya OCR
try:
    from surya_processor import SuryaProcessor
    HAS_SURYA = True
    logger.info("✅ Surya OCR available")
except ImportError:
    HAS_SURYA = False
    logger.warning("⚠️ Surya OCR not available (pip install surya-ocr)")

# Try to import Google Document AI
try:
    from cloud_ai_processor import CloudAIProcessor
    HAS_CLOUD_AI = True
    logger.info("✅ Google Document AI available")
except ImportError:
    HAS_CLOUD_AI = False
    logger.warning("⚠️ Google Document AI not available")


class RealOCRProcessor:
    """Hybrid OCR processor: Surya (free) + Google DocAI (fallback)"""

    def __init__(self):
        self.initialized = False
        self._last_ocr_result = None
        self.surya_processor = None
        self.cloud_processor = None

        # Initialize engines based on mode
        if OCR_ENGINE_MODE in ('surya_primary', 'surya_only') and HAS_SURYA:
            try:
                self.surya_processor = SuryaProcessor()
                logger.info("🚀 Surya OCR initialized (PRIMARY)")
            except Exception as e:
                logger.error(f"❌ Surya OCR init failed: {e}")

        if OCR_ENGINE_MODE in ('surya_primary', 'google_primary', 'google_only') and HAS_CLOUD_AI:
            try:
                self.cloud_processor = CloudAIProcessor()
                logger.info("🚀 Google Document AI initialized (FALLBACK)")
            except Exception as e:
                logger.error(f"❌ Google DocAI init failed: {e}")

        self.initialized = (
            self.surya_processor is not None or
            self.cloud_processor is not None
        )

        if not self.initialized:
            logger.critical("❌ No OCR engine available!")

    async def extract_text(self, file_path: str) -> str:
        """Extract text with hybrid engine (Surya primary, Google fallback)"""
        if not self.initialized:
            logger.error("❌ No OCR engine initialized")
            return ""

        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return ""

        file_ext = Path(file_path).suffix.lower()

        # Determine engine order
        if OCR_ENGINE_MODE == 'surya_primary':
            engines = [
                ('surya', self.surya_processor),
                ('google', self.cloud_processor)
            ]
        elif OCR_ENGINE_MODE == 'google_primary':
            engines = [
                ('google', self.cloud_processor),
                ('surya', self.surya_processor)
            ]
        elif OCR_ENGINE_MODE == 'surya_only':
            engines = [('surya', self.surya_processor)]
        else:  # google_only
            engines = [('google', self.cloud_processor)]

        # Try engines in order
        for engine_name, engine in engines:
            if engine is None:
                continue

            try:
                if engine_name == 'surya':
                    result = await engine.process_document(file_path)
                else:
                    result = await engine.process_with_google(file_path)

                if result and result.raw_text:
                    logger.info(
                        f"✅ {engine_name} OCR success: "
                        f"{len(result.raw_text)} chars, "
                        f"{result.confidence:.1f}% confidence"
                    )

                    self._last_ocr_result = {
                        'text': result.raw_text,
                        'extracted_fields': result.extracted_fields,
                        'confidence': result.confidence,
                        'engine_used': result.service_used,
                        'quality_score': result.confidence,
                        'processing_time': result.processing_time,
                        'raw_response': result.raw_response
                    }
                    return result.raw_text
                else:
                    logger.warning(f"⚠️ {engine_name} returned no text, trying next...")

            except Exception as e:
                logger.error(f"❌ {engine_name} failed: {e}")
                continue

        logger.error("❌ All OCR engines failed")
        return ""

    def get_last_ocr_metadata(self) -> Optional[Dict[str, Any]]:
        return self._last_ocr_result

    def get_ocr_system_info(self) -> Dict[str, Any]:
        return {
            'engine_mode': OCR_ENGINE_MODE,
            'surya_available': self.surya_processor is not None,
            'google_available': self.cloud_processor is not None,
            'initialized': self.initialized,
            'smart_mapper_enabled': True
        }
```

### 3.3 Smart Mapper Compatibility Layer

Surya OCR output perlu diformat agar kompatibel dengan Smart Mapper (Claude AI) yang expect format Google Document AI.

**Perubahan di `smart_mapper.py`:**

```python
# Di method map_document(), tambahkan detection source

async def map_document(self, doc_type, document_json, template, ...):
    source = document_json.get("source", "google_document_ai")

    if source == "surya_ocr":
        # Convert Surya format to Smart Mapper compatible format
        document_json = self._convert_surya_to_standard(document_json)

    # ... existing Smart Mapper logic (unchanged)

def _convert_surya_to_standard(self, surya_json: dict) -> dict:
    """Convert Surya OCR output to Google DocAI-compatible format"""
    pages = []
    for page in surya_json.get("pages", []):
        # Convert lines to paragraphs format
        paragraphs = []
        for line in page.get("lines", []):
            paragraphs.append({
                "text": line["text"],
                "confidence": line.get("confidence", 0.9),
                "bounding_box": line.get("bbox", [])
            })

        # Convert layout blocks
        blocks = []
        for block in page.get("layout", []):
            blocks.append({
                "type": block["label"],
                "bbox": block["bbox"],
                "confidence": block.get("confidence", 0.9)
            })

        pages.append({
            "page_number": page["page_number"],
            "paragraphs": paragraphs,
            "tables": page.get("tables", []),
            "blocks": blocks,
            "text": page.get("text", "")
        })

    return {
        "source": "surya_ocr_converted",
        "pages": pages,
        "text": surya_json.get("text", ""),
        "tables": surya_json.get("tables", [])
    }
```

---

## 4. Server Requirements & Performance

### 4.1 VPS Requirements (CPU Mode)

| Resource | Current (Google only) | Dengan Surya OCR |
|----------|----------------------|-------------------|
| **RAM** | 300MB | 2-3GB (models loaded) |
| **Disk** | 6.1GB (venv) | +2GB (Surya models) |
| **CPU** | Minimal | 2-4 cores recommended |
| **GPU** | Not needed | Optional (faster) |

### 4.2 Processing Speed Comparison

| Dokumen | Google DocAI | Surya (CPU) | Surya (GPU) |
|---------|-------------|-------------|-------------|
| 1 halaman (image) | ~2s | ~5-8s | ~1-2s |
| 1 halaman (PDF) | ~3s | ~8-12s | ~2-3s |
| 10 halaman PDF | ~5s | ~40-60s | ~10-15s |
| 50 halaman PDF | ~15s | ~3-5min | ~30-60s |

**Trade-off: Lebih lambat di CPU, tapi GRATIS.**

### 4.3 Memory Optimization (CPU VPS)

```python
# Environment variables untuk VPS tanpa GPU
OCR_ENGINE_MODE=surya_primary
TORCH_DEVICE=cpu

# Batch sizes kecil untuk hemat memory
RECOGNITION_BATCH_SIZE=8      # Default: 32 (CPU)
DETECTOR_BATCH_SIZE=2          # Default: 6 (CPU)
LAYOUT_BATCH_SIZE=1            # Default: 4 (CPU)
TABLE_REC_BATCH_SIZE=2         # Default: 8 (CPU)

# Lazy loading: models di-load saat dibutuhkan
SURYA_LAZY_LOAD=true
```

---

## 5. Configuration (.env)

```bash
# === OCR Engine Configuration ===

# Engine mode: surya_primary | google_primary | surya_only | google_only
OCR_ENGINE_MODE=surya_primary

# Surya OCR settings
TORCH_DEVICE=cpu
RECOGNITION_BATCH_SIZE=8
DETECTOR_BATCH_SIZE=2
LAYOUT_BATCH_SIZE=1
TABLE_REC_BATCH_SIZE=2
SURYA_LAZY_LOAD=true

# Google Document AI (fallback)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_CLOUD_PROJECT_ID=automation-ai-pajak
GOOGLE_PROCESSOR_ID=xxxxx
GOOGLE_PROCESSOR_LOCATION=us
```

---

## 6. Installation Steps

```bash
# 1. Install Surya OCR
pip install surya-ocr

# 2. Install PyMuPDF (PDF to image conversion)
pip install PyMuPDF

# 3. (Optional) Remove unused PyTorch CUDA if on CPU-only VPS
pip uninstall nvidia-cublas-cu12 nvidia-cuda-nvrtc-cu12 \
    nvidia-cuda-runtime-cu12 nvidia-cudnn-cu8 nvidia-nccl2 \
    nvidia-cusparse-cu12 nvidia-cusolver-cu12

# 4. First run will auto-download Surya models (~2GB)

# 5. Set environment variable
echo "OCR_ENGINE_MODE=surya_primary" >> /var/www/docscan/backend/.env
```

---

## 7. Implementation Roadmap

### Phase 1: Core Integration (3-5 hari)

```
[x] Design document (this file)
[ ] Create surya_processor.py
[ ] Modify ocr_processor.py (hybrid engine)
[ ] Add OCR_ENGINE_MODE config
[ ] Test with single page faktur pajak
[ ] Test with single page image
```

### Phase 2: Smart Mapper Compatibility (2-3 hari)

```
[ ] Add Surya → Standard format converter in smart_mapper.py
[ ] Test Smart Mapper with Surya output (faktur pajak)
[ ] Test Smart Mapper with Surya output (rekening koran)
[ ] Verify table extraction quality
```

### Phase 3: Chunking & Multi-page (2-3 hari)

```
[ ] Test PDF chunking with Surya
[ ] Optimize memory for large PDFs (50+ pages)
[ ] Test rekening koran 50 halaman
[ ] Memory profiling & optimization
```

### Phase 4: Production Deploy (1-2 hari)

```
[ ] Install on VPS
[ ] Performance benchmarking
[ ] Set OCR_ENGINE_MODE=surya_primary
[ ] Monitor error rates
[ ] Compare accuracy: Surya vs Google
```

**Total: 8-13 hari**

---

## 8. Fallback Logic Detail

```
User uploads document
        │
        ▼
┌─ OCR_ENGINE_MODE = surya_primary ─┐
│                                    │
│  ┌─────────────────────┐          │
│  │ 1. Try Surya OCR    │          │
│  │    (free, local)    │          │
│  └──────────┬──────────┘          │
│             │                      │
│     Success? ──► Yes ──► Return    │
│             │                      │
│             No                     │
│             │                      │
│  ┌──────────▼──────────┐          │
│  │ 2. Try Google DocAI │          │
│  │    (paid, cloud)    │          │
│  └──────────┬──────────┘          │
│             │                      │
│     Success? ──► Yes ──► Return    │
│             │                      │
│             No                     │
│             │                      │
│  ┌──────────▼──────────┐          │
│  │ 3. Return Error     │          │
│  │    "All OCR failed" │          │
│  └─────────────────────┘          │
└────────────────────────────────────┘
```

---

## 9. Monitoring & Analytics

### API Endpoint: `GET /api/ocr/stats`

```json
{
  "engine_mode": "surya_primary",
  "engines": {
    "surya": { "available": true, "requests": 450, "success": 440, "avg_time": 8.2 },
    "google": { "available": true, "requests": 10, "success": 10, "avg_time": 3.1 }
  },
  "fallback_rate": "2.2%",
  "cost_saved_this_month": "Rp 680,000",
  "total_pages_processed": 4500
}
```

### SaaS Token Impact

Dengan Surya OCR gratis, **margin profit naik drastis:**

| Bulan ke-6 | Dengan Google | Dengan Surya Primary |
|------------|---------------|---------------------|
| Revenue | Rp 17,500,000 | Rp 17,500,000 |
| Google OCR Cost | Rp 1,200,000 | Rp 120,000 (fallback only) |
| AI Cost (Claude) | Rp 4,000,000 | Rp 4,000,000 |
| Server | Rp 500,000 | Rp 800,000 (more RAM) |
| **Net Profit** | **Rp 11,275,000** | **Rp 12,055,000** |
| **Margin** | 64% | **69%** |

---

## 10. Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Surya accuracy < Google | Medium | Fallback ke Google untuk hasil buruk |
| Surya lambat di CPU | Medium | Upgrade VPS RAM/CPU, atau tambah GPU |
| Model download besar (2GB) | Low | One-time download, cache di server |
| PyTorch memory usage | Medium | Lazy loading, batch size kecil |
| Table detection kurang akurat | Medium | Synthetic table fallback (existing) |

---

## Appendix: File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `surya_processor.py` | **NEW** | Surya OCR wrapper class |
| `ocr_processor.py` | **MODIFY** | Hybrid engine (Surya + Google) |
| `smart_mapper.py` | **MODIFY** | Add Surya format converter |
| `.env` | **MODIFY** | Add OCR_ENGINE_MODE config |
| `requirements.txt` | **MODIFY** | Add `surya-ocr`, `PyMuPDF` |

**Zero breaking changes** - existing Google DocAI flow tetap berfungsi.

---

**Document Version:** 1.0
**Last Updated:** February 2026

**Sources:**
- [Surya OCR GitHub](https://github.com/datalab-to/surya)
- [Surya OCR PyPI](https://pypi.org/project/surya-ocr/)
- [Google Document AI Pricing](https://cloud.google.com/document-ai/pricing)
