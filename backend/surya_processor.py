"""
Surya OCR Processor
Local OCR engine using Surya (free, open source)
Supports: OCR, Table Detection, Layout Analysis
Output format: Google Document AI compatible (for Smart Mapper)
"""

import os
import gc
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class SuryaOCRResult:
    """Surya OCR result matching CloudOCRResult interface"""
    raw_text: str
    confidence: float
    service_used: str
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
    - CPU or GPU mode
    - Output compatible with Google Document AI format (for Smart Mapper)
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
        os.environ.setdefault('RECOGNITION_BATCH_SIZE',
                              os.environ.get('RECOGNITION_BATCH_SIZE', '8'))
        os.environ.setdefault('DETECTOR_BATCH_SIZE',
                              os.environ.get('DETECTOR_BATCH_SIZE', '2'))
        os.environ.setdefault('LAYOUT_BATCH_SIZE',
                              os.environ.get('LAYOUT_BATCH_SIZE', '1'))
        os.environ.setdefault('TABLE_REC_BATCH_SIZE',
                              os.environ.get('TABLE_REC_BATCH_SIZE', '2'))

        try:
            self._init_models()
            self.initialized = True
            logger.info("Surya OCR initialized (CPU mode)")
        except Exception as e:
            logger.error(f"Surya OCR init failed: {e}", exc_info=True)
            self.initialized = False

    def _init_models(self):
        """Load core Surya models (foundation + recognition + detection)"""
        from surya.foundation import FoundationPredictor
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor

        self._foundation = FoundationPredictor()
        self._detection = DetectionPredictor()
        self._recognition = RecognitionPredictor(self._foundation)

        logger.info("Surya OCR core models loaded (foundation + recognition + detection)")

    def _init_layout_model(self):
        """Load layout model on demand (memory saving)"""
        if self._layout is None:
            from surya.layout import LayoutPredictor
            self._layout = LayoutPredictor(self._foundation)
            logger.info("Surya Layout model loaded")

    def _init_table_model(self):
        """Load table recognition model on demand"""
        if self._table_rec is None:
            from surya.table_rec import TableRecPredictor
            self._table_rec = TableRecPredictor()
            logger.info("Surya Table Recognition model loaded")

    def _pdf_to_images(self, file_path: str) -> list:
        """Convert PDF pages to PIL Images using PyMuPDF"""
        import fitz  # PyMuPDF
        from PIL import Image
        import io

        doc = fitz.open(file_path)
        images = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render at 300 DPI for good OCR quality
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data)).convert("RGB")
            images.append(img)
            del pix

        doc.close()
        return images

    def _image_to_pil(self, file_path: str) -> list:
        """Load image file as PIL Image"""
        from PIL import Image
        img = Image.open(file_path).convert("RGB")
        return [img]

    async def process_document(self, file_path: str) -> SuryaOCRResult:
        """Process document with Surya OCR

        Supports: PDF, PNG, JPG, JPEG, TIFF, BMP
        Returns: SuryaOCRResult with Google DocAI-compatible raw_response
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

        logger.info(f"Surya OCR processing {len(images)} pages from {file_ext} file...")

        # Step 1: Text Recognition (OCR)
        ocr_predictions = self._recognition(images, det_predictor=self._detection)

        # Step 2: Layout Analysis (detect tables, headers, etc.)
        self._init_layout_model()
        layout_predictions = self._layout(images)

        # Step 3: Table Recognition (if tables detected in layout)
        has_tables = False
        for page_layout in layout_predictions:
            for block in page_layout.bboxes:
                if block.label == "Table":
                    has_tables = True
                    break
            if has_tables:
                break

        table_predictions = None
        if has_tables:
            self._init_table_model()
            table_predictions = self._table_rec(images)

        # Build page text and metadata
        all_page_texts = []
        page_ocr_data = []
        total_confidence = 0
        total_lines = 0

        for page_idx, ocr_pred in enumerate(ocr_predictions):
            page_text = ""
            page_lines_data = []

            for line in ocr_pred.text_lines:
                page_text += line.text + "\n"
                total_confidence += line.confidence
                total_lines += 1
                page_lines_data.append({
                    "text": line.text,
                    "confidence": line.confidence,
                    "bbox": list(line.bbox) if hasattr(line.bbox, '__iter__') else line.bbox,
                })

            all_page_texts.append(page_text.rstrip("\n"))
            page_ocr_data.append(page_lines_data)

        avg_confidence = (total_confidence / total_lines * 100) if total_lines > 0 else 0

        # Build Google DocAI-compatible raw_response
        raw_response = self._build_google_compatible_response(
            all_page_texts, page_ocr_data, table_predictions
        )

        # Memory cleanup
        del images
        gc.collect()

        processing_time = time.time() - start_time
        full_text = raw_response["text"]

        logger.info(
            f"Surya OCR complete: {len(all_page_texts)} pages, "
            f"{total_lines} lines, {avg_confidence:.1f}% confidence, "
            f"{processing_time:.1f}s"
        )

        return SuryaOCRResult(
            raw_text=full_text,
            confidence=avg_confidence,
            service_used="surya_ocr",
            processing_time=processing_time,
            extracted_fields={},
            raw_response=raw_response,
            document_type="",
            language_detected="id",
        )

    def _build_google_compatible_response(
        self,
        all_page_texts: List[str],
        page_ocr_data: List[list],
        table_predictions: Optional[list],
    ) -> Dict[str, Any]:
        """Build raw_response in Google Document AI format for Smart Mapper compatibility.

        Smart Mapper extracts table cell text via text_anchor.text_segments
        which reference character positions in the root 'text' field.
        We append table cell texts to full_text and record their positions.
        """
        # Start with OCR text (pages joined by newline)
        full_text = "\n".join(all_page_texts)

        pages = []
        for page_idx in range(len(all_page_texts)):
            # Get table data for this page
            page_tables_formatted = []

            if table_predictions and page_idx < len(table_predictions):
                page_pred = table_predictions[page_idx]

                # Process each table detected on this page
                for table in (page_pred.tables if hasattr(page_pred, 'tables') else []):
                    # Group cells by row_id
                    rows_map = defaultdict(list)
                    header_row_ids = set()

                    cells = table.cells if hasattr(table, 'cells') else []
                    for cell in cells:
                        row_id = cell.row_id if hasattr(cell, 'row_id') else 0
                        rows_map[row_id].append(cell)
                        if hasattr(cell, 'is_header') and cell.is_header:
                            header_row_ids.add(row_id)

                    # Sort cells within each row by col_id
                    for row_id in rows_map:
                        rows_map[row_id].sort(
                            key=lambda c: c.col_id if hasattr(c, 'col_id') else 0
                        )

                    # Build header_rows and body_rows with text_anchor
                    header_rows = []
                    body_rows = []

                    for row_id in sorted(rows_map.keys()):
                        row_cells = []
                        for cell in rows_map[row_id]:
                            cell_text = (cell.text if hasattr(cell, 'text') else "").strip()

                            if cell_text:
                                # Append cell text to full_text and record position
                                start_index = len(full_text) + 1  # +1 for the \n
                                full_text += "\n" + cell_text
                                end_index = len(full_text)
                            else:
                                start_index = 0
                                end_index = 0

                            row_cells.append({
                                "layout": {
                                    "text_anchor": {
                                        "text_segments": [{
                                            "start_index": start_index,
                                            "end_index": end_index,
                                        }]
                                    }
                                }
                            })

                        row_data = {"cells": row_cells}
                        if row_id in header_row_ids:
                            header_rows.append(row_data)
                        else:
                            body_rows.append(row_data)

                    # If no headers detected, treat first row as header
                    if not header_rows and body_rows:
                        header_rows = [body_rows.pop(0)]

                    page_tables_formatted.append({
                        "header_rows": header_rows,
                        "body_rows": body_rows,
                    })

            pages.append({
                "tables": page_tables_formatted,
            })

        return {
            "text": full_text,
            "pages": pages,
            "entities": [],
            "source": "surya_ocr",
        }
