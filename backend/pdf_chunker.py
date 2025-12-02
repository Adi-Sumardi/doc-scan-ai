"""
PDF Chunker for Multi-Page Bank Statements
Handles large PDF files (20+ pages) by splitting into manageable chunks
Optimized for rekening koran / bank statements with 150+ transactions per page

✅ MEMORY OPTIMIZATION:
- Default chunk size: 8 pages (~1200 transactions)
- Prevents OOM KILL for large files (50+ pages)
- Processes chunks sequentially to manage memory
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
import gc  # ✅ NEW: Garbage collection for memory management

logger = logging.getLogger(__name__)

class PDFChunker:
    """Split large PDF files into chunks for processing"""

    def __init__(self, max_pages_per_chunk: int = 8):  # ✅ REDUCED from 10 to 8
        """
        Initialize PDF chunker

        Args:
            max_pages_per_chunk: Maximum pages to process in one chunk (default: 8)
                                 8 pages × 150 transactions = ~1200 transactions per chunk
                                 Safe for Claude AI processing without OOM
        """
        self.max_pages_per_chunk = max_pages_per_chunk
        logger.info(f"📄 PDF Chunker initialized (max {max_pages_per_chunk} pages/chunk)")
        logger.info(f"   Estimated ~{max_pages_per_chunk * 150} transactions per chunk")

    def get_page_count(self, pdf_path: str) -> int:
        """Get total page count of PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages)
        except Exception as e:
            logger.error(f"❌ Failed to get page count from {pdf_path}: {e}")
            return 0

    def needs_chunking(self, pdf_path: str, threshold: int = 8) -> bool:  # ✅ REDUCED from 10 to 8
        """
        Check if PDF needs to be chunked

        Args:
            pdf_path: Path to PDF file
            threshold: Page count threshold for chunking (default: 8)

        Returns:
            True if PDF has more pages than threshold
        """
        page_count = self.get_page_count(pdf_path)
        needs_split = page_count > threshold

        if needs_split:
            logger.info(f"📚 PDF has {page_count} pages - chunking required (threshold: {threshold})")
            logger.info(f"   Estimated total transactions: ~{page_count * 150}")
        else:
            logger.info(f"📄 PDF has {page_count} pages - no chunking needed")

        return needs_split

    def split_pdf_to_chunks(self, pdf_path: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """
        Split PDF into multiple chunk files

        Args:
            pdf_path: Path to source PDF
            output_dir: Directory for chunk files (default: same as source)

        Returns:
            List of dicts with chunk info: {
                'path': str,
                'start_page': int,
                'end_page': int,
                'total_pages': int
            }
        """
        try:
            page_count = self.get_page_count(pdf_path)
            if page_count == 0:
                logger.error(f"❌ Cannot split PDF with 0 pages: {pdf_path}")
                return []

            # Prepare output directory
            if output_dir is None:
                output_dir = str(Path(pdf_path).parent / "chunks")

            os.makedirs(output_dir, exist_ok=True)

            # Read source PDF
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                chunks = []
                chunk_num = 1

                logger.info(f"📄 Splitting {total_pages} pages into {self.max_pages_per_chunk}-page chunks...")

                # Split into chunks
                for start_page in range(0, total_pages, self.max_pages_per_chunk):
                    end_page = min(start_page + self.max_pages_per_chunk, total_pages)

                    # Create chunk PDF
                    pdf_writer = PyPDF2.PdfWriter()

                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])

                    # Save chunk
                    chunk_filename = f"chunk_{chunk_num:03d}.pdf"
                    chunk_path = os.path.join(output_dir, chunk_filename)

                    with open(chunk_path, 'wb') as chunk_file:
                        pdf_writer.write(chunk_file)

                    chunk_info = {
                        'path': chunk_path,
                        'start_page': start_page + 1,  # 1-indexed
                        'end_page': end_page,
                        'total_pages': end_page - start_page
                    }

                    chunks.append(chunk_info)
                    logger.info(f"   ✅ Chunk {chunk_num}: pages {start_page + 1}-{end_page} (~{(end_page - start_page) * 150} txns)")

                    chunk_num += 1

                logger.info(f"✅ PDF split into {len(chunks)} chunks")
                return chunks

        except Exception as e:
            logger.error(f"❌ Failed to split PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def cleanup_chunks(self, chunk_paths: List[str]):
        """
        ✅ ENHANCED: Clean up temporary chunk files with memory cleanup

        Args:
            chunk_paths: List of chunk file paths to delete
        """
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
                    logger.debug(f"🗑️ Removed chunk: {chunk_path}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove chunk {chunk_path}: {e}")

        # ✅ NEW: Force garbage collection after cleanup
        gc.collect()
        logger.info(f"🗑️ Cleaned up {len(chunk_paths)} chunk files + freed memory")

    def merge_extracted_data(
        self, 
        chunk_results: List[Dict[str, Any]], 
        document_type: str
    ) -> Dict[str, Any]:
        """
        ✅ ENHANCED: Merge results from all chunks with memory-efficient processing

        Args:
            chunk_results: List of extraction results from each chunk
            document_type: Type of document (rekening_koran, etc)

        Returns:
            Merged result with all transactions
        """
        try:
            if not chunk_results:
                logger.warning("⚠️ No chunk results to merge")
                return {}

            logger.info(f"🔗 Merging {len(chunk_results)} chunk results...")

            # Base merged result from first chunk
            merged = {
                'document_type': document_type,
                'extracted_data': {},
                'raw_text': '',
                'extracted_text': ''
            }

            # Merge based on document type
            if document_type == 'rekening_koran':
                merged = self._merge_rekening_koran_chunks(chunk_results)
            else:
                # Generic merge for other document types
                merged = self._merge_generic_chunks(chunk_results)

            # ✅ NEW: Force garbage collection after merge
            gc.collect()

            return merged

        except Exception as e:
            logger.error(f"❌ Failed to merge chunk results: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _merge_rekening_koran_chunks(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        ✅ ENHANCED: Merge rekening koran chunks with duplicate removal and memory optimization

        Handles:
        - Bank info (from first chunk)
        - Saldo info (opening from first, closing from last)
        - Transactions (merged from all chunks, duplicates removed)
        - Summary (recalculated from merged transactions)
        - raw_response (merged pages from all chunks for Claude AI)
        """
        if not chunk_results:
            return {}

        # Get first chunk as base
        first_chunk = chunk_results[0]
        first_extracted = first_chunk.get('extracted_data', {})

        # Initialize merged structure
        merged = {
            'document_type': 'rekening_koran',
            'bank_info': {},
            'saldo_info': {},
            'transactions': [],
            'raw_text': '',
            'extracted_text': '',
            'raw_response': {}  # ✅ NEW: Merge raw_response for Claude AI
        }

        # Merge bank info (use first chunk)
        if 'bank_info' in first_extracted:
            merged['bank_info'] = first_extracted['bank_info'].copy()
            logger.info(f"   Bank: {merged['bank_info'].get('nama_bank', 'N/A')}")

        # Merge saldo info
        if 'saldo_info' in first_extracted:
            # Start with first chunk's saldo_awal
            merged['saldo_info'] = first_extracted['saldo_info'].copy()

            # Use last chunk's saldo_akhir
            last_chunk = chunk_results[-1]
            last_extracted = last_chunk.get('extracted_data', {})
            if 'saldo_info' in last_extracted and 'saldo_akhir' in last_extracted['saldo_info']:
                merged['saldo_info']['saldo_akhir'] = last_extracted['saldo_info']['saldo_akhir']

            logger.info(f"   Saldo Awal: {merged['saldo_info'].get('saldo_awal', 'N/A')}")
            logger.info(f"   Saldo Akhir: {merged['saldo_info'].get('saldo_akhir', 'N/A')}")

        # ✅ CRITICAL: Merge transactions with duplicate detection
        seen_transactions = set()  # Track unique transactions
        all_transactions = []

        for idx, chunk in enumerate(chunk_results, 1):
            chunk_extracted = chunk.get('extracted_data', {})
            chunk_transactions = chunk_extracted.get('transactions', [])

            if not chunk_transactions:
                logger.warning(f"   ⚠️ Chunk {idx} has no transactions")
                continue

            # Add transactions with duplicate check
            duplicates = 0
            for trans in chunk_transactions:
                if not isinstance(trans, dict):
                    continue

                # Create transaction fingerprint
                tanggal = trans.get('tanggal', '')
                debet = str(trans.get('debet', ''))
                kredit = str(trans.get('kredit', ''))
                saldo = str(trans.get('saldo', ''))
                fingerprint = f"{tanggal}_{debet}_{kredit}_{saldo}"

                if fingerprint not in seen_transactions:
                    seen_transactions.add(fingerprint)
                    all_transactions.append(trans)
                else:
                    duplicates += 1

            logger.info(f"   Chunk {idx}: {len(chunk_transactions)} txns, {duplicates} duplicates removed")

            # ✅ NEW: Clear chunk data from memory
            del chunk_transactions

        merged['transactions'] = all_transactions
        logger.info(f"   ✅ Total unique transactions: {len(all_transactions)}")

        # Merge raw text (concatenate all chunks)
        raw_texts = []
        for chunk in chunk_results:
            raw_text = chunk.get('raw_text', '') or chunk.get('extracted_text', '')
            if raw_text:
                raw_texts.append(raw_text)

        merged['raw_text'] = '\n'.join(raw_texts)
        merged['extracted_text'] = merged['raw_text']

        # ✅ NEW: Merge raw_response from all chunks for Claude AI
        # Structure: { 'pages': [...], 'text': ... }
        all_pages = []
        all_tables = []
        for idx, chunk in enumerate(chunk_results, 1):
            chunk_extracted = chunk.get('extracted_data', {})
            chunk_raw = chunk_extracted.get('raw_response', {})

            if isinstance(chunk_raw, dict):
                # Collect pages from each chunk
                chunk_pages = chunk_raw.get('pages', [])
                if chunk_pages:
                    all_pages.extend(chunk_pages)
                    logger.info(f"   📊 Chunk {idx}: Added {len(chunk_pages)} pages to merged raw_response")

                # Also collect tables
                chunk_tables = chunk.get('tables', [])
                if chunk_tables:
                    all_tables.extend(chunk_tables)

        # Build merged raw_response
        if all_pages:
            merged['raw_response'] = {
                'pages': all_pages,
                'text': merged['raw_text']
            }
            logger.info(f"   ✅ Merged raw_response: {len(all_pages)} pages, {len(all_tables)} tables")
        else:
            # Fallback: Use first chunk's raw_response if pages not found
            first_raw = first_chunk.get('extracted_data', {}).get('raw_response', {})
            if first_raw:
                merged['raw_response'] = first_raw
                logger.info(f"   ⚠️ Using first chunk's raw_response as fallback")
            else:
                logger.warning(f"   ⚠️ No raw_response found in any chunk")

        # ✅ NEW: Clear temporary data
        del raw_texts
        del seen_transactions

        # Build extracted_data wrapper
        merged['extracted_data'] = {
            'bank_info': merged['bank_info'],
            'saldo_info': merged['saldo_info'],
            'transactions': merged['transactions'],
            'raw_response': merged.get('raw_response', {})  # ✅ Include raw_response in extracted_data
        }

        return merged

    def _merge_generic_chunks(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generic merge for non-rekening-koran documents
        """
        if not chunk_results:
            return {}

        # Simple concatenation of raw text
        merged = {
            'raw_text': '',
            'extracted_text': '',
            'extracted_data': {}
        }

        raw_texts = []
        for chunk in chunk_results:
            raw_text = chunk.get('raw_text', '') or chunk.get('extracted_text', '')
            if raw_text:
                raw_texts.append(raw_text)

        merged['raw_text'] = '\n'.join(raw_texts)
        merged['extracted_text'] = merged['raw_text']

        return merged


# Global chunker instance
pdf_chunker = PDFChunker()
