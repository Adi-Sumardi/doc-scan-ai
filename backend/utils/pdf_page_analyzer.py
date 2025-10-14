"""
PDF Page Analyzer
Utility for analyzing PDF page counts and splitting large PDFs into manageable chunks
Optimized for handling massive bank statements with 50+ pages
"""

import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import fitz  # PyMuPDF - memory efficient PDF library

logger = logging.getLogger(__name__)


class PDFPageAnalyzer:
    """
    Analyze and chunk PDF files for efficient processing

    Features:
    - Count total pages in PDF
    - Split large PDFs into page chunks
    - Memory-efficient processing (only load pages when needed)
    - Support for massive PDFs (100+ pages)
    """

    def __init__(self, max_pages_per_chunk: int = 10):
        """
        Initialize PDF Page Analyzer

        Args:
            max_pages_per_chunk: Maximum pages to process in one chunk (default: 10)
        """
        self.max_pages_per_chunk = max_pages_per_chunk

    def get_page_count(self, pdf_path: str) -> int:
        """
        Get total page count of a PDF file (fast operation)

        Args:
            pdf_path: Path to PDF file

        Returns:
            int: Total number of pages
        """
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception as e:
            logger.error(f"Failed to get page count for {pdf_path}: {e}")
            return 0

    def analyze_pdf(self, pdf_path: str) -> Dict:
        """
        Analyze PDF file and return detailed information

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with PDF metadata
        """
        try:
            doc = fitz.open(pdf_path)

            page_count = len(doc)
            file_size = Path(pdf_path).stat().st_size

            # Get metadata
            metadata = doc.metadata or {}

            # Calculate chunks
            num_chunks = (page_count + self.max_pages_per_chunk - 1) // self.max_pages_per_chunk

            analysis = {
                "file_path": str(pdf_path),
                "filename": Path(pdf_path).name,
                "total_pages": page_count,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "needs_chunking": page_count > self.max_pages_per_chunk,
                "num_chunks": num_chunks,
                "pages_per_chunk": self.max_pages_per_chunk,
                "metadata": {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "creator": metadata.get("creator", ""),
                    "producer": metadata.get("producer", "")
                }
            }

            doc.close()

            logger.info(f"📄 PDF Analysis: {Path(pdf_path).name} - {page_count} pages, {num_chunks} chunks")

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze PDF {pdf_path}: {e}")
            return {
                "file_path": str(pdf_path),
                "filename": Path(pdf_path).name,
                "total_pages": 0,
                "error": str(e)
            }

    def get_page_chunks(self, pdf_path: str) -> List[Dict]:
        """
        Get list of page chunks for processing

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of chunk definitions with page ranges
        """
        try:
            page_count = self.get_page_count(pdf_path)

            if page_count == 0:
                return []

            chunks = []

            for chunk_idx in range(0, page_count, self.max_pages_per_chunk):
                start_page = chunk_idx
                end_page = min(chunk_idx + self.max_pages_per_chunk, page_count)

                chunk = {
                    "chunk_index": len(chunks),
                    "start_page": start_page,
                    "end_page": end_page,
                    "page_count": end_page - start_page,
                    "page_range": f"{start_page + 1}-{end_page}",  # Human-readable (1-indexed)
                    "file_path": str(pdf_path)
                }

                chunks.append(chunk)

            logger.info(f"📊 Created {len(chunks)} chunks for {Path(pdf_path).name}")

            return chunks

        except Exception as e:
            logger.error(f"Failed to create chunks for {pdf_path}: {e}")
            return []

    def extract_page_range(
        self,
        pdf_path: str,
        start_page: int,
        end_page: int,
        output_path: str
    ) -> bool:
        """
        Extract a range of pages from PDF to a new PDF file

        Args:
            pdf_path: Source PDF path
            start_page: Start page (0-indexed)
            end_page: End page (exclusive, 0-indexed)
            output_path: Output PDF path

        Returns:
            bool: Success status
        """
        try:
            doc = fitz.open(pdf_path)

            # Create new document with selected pages
            output_doc = fitz.open()

            for page_num in range(start_page, end_page):
                if page_num < len(doc):
                    output_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

            # Save output
            output_doc.save(output_path)
            output_doc.close()
            doc.close()

            logger.info(f"✅ Extracted pages {start_page}-{end_page} to {output_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to extract pages from {pdf_path}: {e}")
            return False

    def get_page_image(
        self,
        pdf_path: str,
        page_number: int,
        dpi: int = 150
    ) -> Optional[bytes]:
        """
        Extract a single page as PNG image (for preview or OCR)

        Args:
            pdf_path: Path to PDF file
            page_number: Page number (0-indexed)
            dpi: Resolution for image (default: 150)

        Returns:
            bytes: PNG image data, or None if failed
        """
        try:
            doc = fitz.open(pdf_path)

            if page_number >= len(doc):
                logger.error(f"Page {page_number} out of range for {pdf_path}")
                doc.close()
                return None

            page = doc[page_number]

            # Render page to image
            zoom = dpi / 72  # 72 is default DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")

            doc.close()

            return img_bytes

        except Exception as e:
            logger.error(f"Failed to extract page {page_number} from {pdf_path}: {e}")
            return None


def analyze_batch_pdfs(file_paths: List[str], max_pages_per_chunk: int = 10) -> Dict:
    """
    Analyze multiple PDFs and return batch statistics

    Args:
        file_paths: List of PDF file paths
        max_pages_per_chunk: Chunk size for processing

    Returns:
        Dict with batch statistics
    """
    analyzer = PDFPageAnalyzer(max_pages_per_chunk=max_pages_per_chunk)

    total_pages = 0
    total_chunks = 0
    pdf_analyses = []

    for pdf_path in file_paths:
        if not str(pdf_path).lower().endswith('.pdf'):
            continue

        analysis = analyzer.analyze_pdf(pdf_path)
        pdf_analyses.append(analysis)

        total_pages += analysis.get("total_pages", 0)
        total_chunks += analysis.get("num_chunks", 0)

    return {
        "total_files": len(file_paths),
        "total_pdf_files": len(pdf_analyses),
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "average_pages_per_file": round(total_pages / len(pdf_analyses), 1) if pdf_analyses else 0,
        "files": pdf_analyses
    }


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Quick utility function to get PDF page count

    Args:
        pdf_path: Path to PDF file

    Returns:
        int: Number of pages (0 if error)
    """
    analyzer = PDFPageAnalyzer()
    return analyzer.get_page_count(pdf_path)


def should_chunk_pdf(pdf_path: str, max_pages: int = 10) -> Tuple[bool, int]:
    """
    Check if a PDF should be chunked and return page count

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum pages before chunking (default: 10)

    Returns:
        Tuple[bool, int]: (should_chunk, page_count)
    """
    analyzer = PDFPageAnalyzer(max_pages_per_chunk=max_pages)
    page_count = analyzer.get_page_count(pdf_path)

    return (page_count > max_pages, page_count)
